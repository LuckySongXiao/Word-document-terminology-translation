from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
import os
import uuid
import logging
import shutil
import threading
from typing import List, Optional, Dict
from pydantic import BaseModel
import json
import asyncio
from datetime import datetime

from services.translator import TranslationService
from services.document_factory import DocumentProcessorFactory
from utils.terminology import load_terminology, save_terminology, TERMINOLOGY_PATH
from web.realtime_logger import realtime_monitor, start_realtime_monitoring, stop_realtime_monitoring

# 简化日志配置，避免与web_server.py冲突
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="文档翻译助手", description="多格式文档翻译Web服务")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置静态文件和模板
# 动态确定静态文件和模板目录路径
import sys
from pathlib import Path

def find_web_resources():
    """查找web资源目录"""
    possible_paths = []

    if getattr(sys, 'frozen', False):
        # 打包环境 - 尝试多个可能的路径
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller单文件模式
            meipass_dir = Path(sys._MEIPASS)
            possible_paths.extend([
                meipass_dir,
                meipass_dir / "web",
            ])

        # 可执行文件目录
        exe_dir = Path(sys.executable).parent
        possible_paths.extend([
            exe_dir / "_internal" / "web",
            exe_dir / "web",
            exe_dir / "_internal",
            exe_dir,
        ])
    else:
        # 源码环境
        current_dir = Path(__file__).parent.parent
        possible_paths.append(current_dir)

    # 查找包含web目录的路径
    for base_path in possible_paths:
        web_dir = base_path / "web"
        static_dir = web_dir / "static"
        templates_dir = web_dir / "templates"

        print(f"检查路径: {base_path}")
        print(f"  web目录: {web_dir} (存在: {web_dir.exists()})")
        print(f"  static目录: {static_dir} (存在: {static_dir.exists()})")
        print(f"  templates目录: {templates_dir} (存在: {templates_dir.exists()})")

        # 检查是否有必要的文件
        if templates_dir.exists() and (templates_dir / "index.html").exists():
            print(f"找到有效的web资源目录: {base_path}")
            return base_path

    # 如果都没找到，尝试使用PyInstaller的临时目录
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass_fallback = Path(sys._MEIPASS)
        print(f"未找到有效的web资源目录，使用PyInstaller临时目录: {meipass_fallback}")
        return meipass_fallback

    # 最后的后备选项
    fallback_dir = Path(__file__).parent.parent
    print(f"未找到有效的web资源目录，使用源码目录作为后备: {fallback_dir}")
    return fallback_dir

base_dir = find_web_resources()
static_dir = base_dir / "web" / "static"
templates_dir = base_dir / "web" / "templates"

# 确保目录存在
if not static_dir.exists():
    print(f"警告: 静态文件目录不存在: {static_dir}")
    # 尝试创建空目录
    static_dir.mkdir(parents=True, exist_ok=True)

if not templates_dir.exists():
    print(f"警告: 模板目录不存在: {templates_dir}")
    templates_dir.mkdir(parents=True, exist_ok=True)

print(f"最终使用的静态文件目录: {static_dir}")
print(f"最终使用的模板目录: {templates_dir}")

# 检查关键文件是否存在
index_html = templates_dir / "index.html"
if not index_html.exists():
    print(f"错误: 找不到index.html模板文件: {index_html}")
    print("这将导致Web服务器无法正常工作")

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# 创建上传和输出目录
UPLOAD_DIR = base_dir / "uploads"
OUTPUT_DIR = base_dir / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

print(f"上传目录: {UPLOAD_DIR}")
print(f"输出目录: {OUTPUT_DIR}")

# 创建翻译服务实例（将在web_server.py中初始化）
translator = None

def set_translator_instance(translator_instance):
    """设置翻译服务实例"""
    global translator
    translator = translator_instance

# 数据模型
class TranslationTask(BaseModel):
    task_id: str
    filename: str
    status: str
    progress: float = 0.0
    output_file: Optional[str] = None

# 存储任务状态
translation_tasks = {}

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = threading.Lock()  # 添加线程锁保护连接字典

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        with self._lock:
            self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]

    async def send_message(self, client_id: str, message: str):
        websocket = None
        with self._lock:
            if client_id in self.active_connections:
                websocket = self.active_connections[client_id]

        # 在锁外发送消息，避免阻塞
        if websocket:
            try:
                await websocket.send_text(message)
            except Exception:
                # 如果发送失败，移除连接
                self.disconnect(client_id)

    async def broadcast(self, message: str):
        # 在锁内创建连接列表的副本，避免在遍历时字典被修改
        with self._lock:
            connections_items = list(self.active_connections.items())

        # 在锁外发送消息，避免阻塞
        failed_clients = []
        for client_id, connection in connections_items:
            try:
                await connection.send_text(message)
            except Exception:
                # 记录失败的客户端，稍后移除
                failed_clients.append(client_id)

        # 移除失败的连接
        for client_id in failed_clients:
            self.disconnect(client_id)

# 创建连接管理器实例
manager = ConnectionManager()

# 自定义日志处理器，将日志发送到WebSocket
class WebSocketLogHandler(logging.Handler):
    def __init__(self, task_id: str):
        super().__init__()
        self.task_id = task_id
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        log_entry = self.format(record)

        # 检查是否在异步环境中
        try:
            asyncio.get_running_loop()
            # 如果能获取到事件循环，说明在异步环境中
            asyncio.create_task(self.send_log(log_entry))
        except RuntimeError:
            # 如果不在异步环境中，只记录日志，不尝试发送
            pass

    async def send_log(self, log_entry):
        await manager.send_message(self.task_id, json.dumps({
            "type": "log",
            "data": log_entry
        }))

# 全局WebSocket日志处理器，将日志发送到所有连接的客户端
class GlobalWebSocketLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        # 使用与终端控制台相同的日志格式，确保一致性
        self.setFormatter(logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        self.setLevel(logging.INFO)  # 只处理INFO级别及以上的日志
        self.pending_logs = []  # 存储待发送的日志
        self._lock = threading.Lock()  # 使用线程锁而不是asyncio锁
        self.max_pending_logs = 1000  # 最大待发送日志数量，防止内存溢出

        # 记录初始化信息，同时输出到终端和Web界面
        init_msg = "全局WebSocket日志处理器已初始化，终端控制台和Web界面日志将实时同步"
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO - {init_msg}")

        # 将初始化消息添加到待发送队列
        with self._lock:
            self.pending_logs.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - web.api - {init_msg}")

    def emit(self, record):
        # 过滤掉一些不需要发送到前端的日志
        if record.name.startswith('uvicorn') or record.name.startswith('fastapi'):
            return

        try:
            log_entry = self.format(record)

            # 确保日志同时输出到终端控制台（实时同步）
            import sys
            sys.stdout.write(f"{log_entry}\n")
            sys.stdout.flush()  # 立即刷新输出缓冲区

            # 检查是否在异步环境中，发送到Web界面
            try:
                asyncio.get_running_loop()
                asyncio.create_task(self.broadcast_log(log_entry))
            except RuntimeError:
                # 存储到待发送队列
                with self._lock:
                    if len(self.pending_logs) >= self.max_pending_logs:
                        self.pending_logs.pop(0)
                    self.pending_logs.append(log_entry)
        except Exception as e:
            import sys
            sys.stderr.write(f"日志处理失败: {str(e)}\n")
            sys.stderr.flush()

    async def broadcast_log(self, log_entry):
        # 向所有连接的客户端广播日志
        try:
            # 安全地检查是否有活跃连接
            with manager._lock:
                active_connections_count = len(manager.active_connections)

            if active_connections_count > 0:
                await manager.broadcast(json.dumps({
                    "type": "system_log",
                    "data": log_entry
                }))
            else:
                # 如果没有活跃连接，将日志存储起来
                with self._lock:
                    # 限制待发送日志数量
                    if len(self.pending_logs) >= self.max_pending_logs:
                        self.pending_logs.pop(0)
                    self.pending_logs.append(log_entry)
        except Exception as e:
            # 使用sys.stderr确保错误信息能输出到终端
            import sys
            sys.stderr.write(f"广播日志失败: {str(e)}\n")
            sys.stderr.flush()

    async def flush_pending_logs(self):
        """发送所有待发送的日志"""
        if not self.pending_logs:
            return

        # 使用线程锁
        with self._lock:
            pending = self.pending_logs.copy()
            self.pending_logs.clear()

        # 记录发送日志数量，同时输出到终端
        import sys
        flush_msg = f"正在发送 {len(pending)} 条待处理日志到Web界面..."
        sys.stdout.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - web.api - {flush_msg}\n")
        sys.stdout.flush()

        for log_entry in pending:
            await self.broadcast_log(log_entry)

        # 记录完成信息
        complete_msg = f"已发送 {len(pending)} 条待处理日志到Web界面"
        sys.stdout.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - web.api - {complete_msg}\n")
        sys.stdout.flush()

# 创建全局WebSocket日志处理器
global_ws_handler = GlobalWebSocketLogHandler()

# 添加到根日志记录器
root_logger = logging.getLogger()
root_logger.addHandler(global_ws_handler)

# 特别为所有翻译相关的日志记录器添加处理器，确保翻译过程日志能够被捕获
web_logger = logging.getLogger('web_logger')
web_logger.addHandler(global_ws_handler)

# 翻译服务相关的日志记录器
translator_logger = logging.getLogger('services.translator')
translator_logger.addHandler(global_ws_handler)

document_processor_logger = logging.getLogger('services.document_processor')
document_processor_logger.addHandler(global_ws_handler)

pdf_processor_logger = logging.getLogger('services.pdf_processor')
pdf_processor_logger.addHandler(global_ws_handler)

excel_processor_logger = logging.getLogger('services.excel_processor')
excel_processor_logger.addHandler(global_ws_handler)

ppt_processor_logger = logging.getLogger('services.ppt_processor')
ppt_processor_logger.addHandler(global_ws_handler)

# 基础翻译器日志记录器
base_translator_logger = logging.getLogger('services.base_translator')
base_translator_logger.addHandler(global_ws_handler)

zhipuai_translator_logger = logging.getLogger('services.zhipuai_translator')
zhipuai_translator_logger.addHandler(global_ws_handler)

ollama_translator_logger = logging.getLogger('services.ollama_translator')
ollama_translator_logger.addHandler(global_ws_handler)

siliconflow_translator_logger = logging.getLogger('services.siliconflow_translator')
siliconflow_translator_logger.addHandler(global_ws_handler)

intranet_translator_logger = logging.getLogger('services.intranet_translator')
intranet_translator_logger.addHandler(global_ws_handler)

# Web服务器日志记录器
web_server_logger = logging.getLogger('web_server')
web_server_logger.addHandler(global_ws_handler)

# 确保所有日志记录器的级别都设置为INFO或更低，以便捕获翻译过程日志
for logger_name in [
    'web_logger', 'services.translator', 'services.document_processor',
    'services.pdf_processor', 'services.excel_processor', 'services.ppt_processor',
    'services.base_translator', 'services.zhipuai_translator', 'services.ollama_translator',
    'services.siliconflow_translator', 'services.intranet_translator', 'web_server'
]:
    logger_instance = logging.getLogger(logger_name)
    if logger_instance.level > logging.INFO:
        logger_instance.setLevel(logging.INFO)
web_logger.addHandler(global_ws_handler)
web_logger.setLevel(logging.INFO)
# 确保web_logger的日志会传播到父级记录器
web_logger.propagate = True

# 记录web_logger配置完成
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO - web_logger配置完成，日志将同步到终端和Web界面")

# 路由定义
@app.get("/")
async def read_root(request: Request):
    """返回主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/translators")
async def get_translators():
    """获取可用的翻译器列表"""
    if not translator:
        raise HTTPException(status_code=503, detail="翻译服务尚未初始化")

    # 获取当前翻译器类型
    current_type = translator.get_current_translator_type()

    # 基础可用性检查（不包括内网翻译器）
    available = {
        "zhipuai": translator._check_zhipuai_available(),
        "ollama": translator.check_ollama_service(),
        "siliconflow": translator.check_siliconflow_service(),
        "intranet": None  # 内网翻译器状态将在用户选择时检测
    }

    # 如果当前使用的是内网翻译器，则检查其状态
    if current_type == "intranet":
        available["intranet"] = translator.check_intranet_service()

    translators = {
        "current": current_type,
        "available": available
    }
    return translators

@app.get("/api/translator/current")
async def get_current_translator():
    """获取当前翻译器设置（不检测连接状态）"""
    if not translator:
        return {"success": False, "message": "翻译服务尚未初始化"}

    try:
        current_type = translator.get_current_translator_type()
        return {
            "success": True,
            "current": current_type
        }
    except Exception as e:
        logger.error(f"获取当前翻译器设置失败: {e}")
        return {"success": False, "message": str(e)}

@app.post("/api/translator/set")
async def set_translator(translator_type: str = Form(...)):
    """设置当前翻译器"""
    if not translator:
        raise HTTPException(status_code=503, detail="翻译服务尚未初始化")

    try:
        logger.info(f"用户选择翻译器: {translator_type}，正在进行连接测试...")

        # 测试选择的翻译器连接
        connection_success = translator.test_translator_connection(translator_type)

        if connection_success:
            logger.info(f"{translator_type}连接测试成功，设置为当前翻译器")
            translator.set_translator_type(translator_type)

            result = {
                "success": True,
                "message": f"已设置翻译器为: {translator_type}",
                "connection_status": "connected"
            }
        else:
            logger.warning(f"{translator_type}连接测试失败")

            # 对于在线API，如果连接失败，询问用户是否要切换到Ollama
            if translator_type in ['zhipuai', 'siliconflow', 'intranet']:
                # 检查Ollama是否可用
                ollama_available = translator.test_translator_connection('ollama')
                if ollama_available:
                    logger.info(f"{translator_type}连接失败，建议切换到Ollama")
                    result = {
                        "success": False,
                        "message": f"{translator_type}连接失败，建议切换到本地Ollama模型",
                        "connection_status": "failed",
                        "fallback_available": True,
                        "fallback_type": "ollama"
                    }
                else:
                    result = {
                        "success": False,
                        "message": f"{translator_type}连接失败，且Ollama也不可用",
                        "connection_status": "failed",
                        "fallback_available": False
                    }
            else:
                # 对于Ollama，如果失败就直接报错
                result = {
                    "success": False,
                    "message": f"{translator_type}连接失败，请检查服务状态",
                    "connection_status": "failed",
                    "fallback_available": False
                }

        return result
    except Exception as e:
        logger.error(f"设置翻译器失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"设置翻译器失败: {str(e)}")

@app.post("/api/translator/fallback")
async def switch_to_fallback():
    """切换到备用翻译器（Ollama）"""
    if not translator:
        raise HTTPException(status_code=503, detail="翻译服务尚未初始化")

    try:
        logger.info("用户确认切换到Ollama翻译器")

        # 测试Ollama连接
        if translator.test_translator_connection('ollama'):
            translator.set_translator_type('ollama')
            logger.info("已成功切换到Ollama翻译器")
            return {
                "success": True,
                "message": "已切换到Ollama翻译器",
                "translator_type": "ollama"
            }
        else:
            logger.error("Ollama翻译器连接失败")
            return {
                "success": False,
                "message": "Ollama翻译器连接失败，请检查Ollama服务状态"
            }
    except Exception as e:
        logger.error(f"切换到备用翻译器失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"切换失败: {str(e)}")

@app.get("/api/intranet/status")
async def check_intranet_status():
    """检查内网翻译器状态"""
    if not translator:
        raise HTTPException(status_code=503, detail="翻译服务尚未初始化")

    try:
        is_available = translator.check_intranet_service()
        return {
            "available": is_available,
            "message": "内网服务可用" if is_available else "内网服务不可用",
            "api_url": translator.config.get("intranet_translator", {}).get("api_url", ""),
            "model": translator.config.get("intranet_translator", {}).get("model", "")
        }
    except Exception as e:
        logger.error(f"检查内网翻译器状态失败: {str(e)}")
        return {
            "available": False,
            "message": f"检查失败: {str(e)}",
            "api_url": "",
            "model": ""
        }

@app.get("/api/models")
async def get_models():
    """获取当前翻译器可用的模型列表"""
    if not translator:
        raise HTTPException(status_code=503, detail="翻译服务尚未初始化")

    try:
        models = translator.get_available_models()
        return {"models": models, "current": translator.get_current_model()}
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"获取模型列表失败: {str(e)}")

@app.post("/api/model/set")
async def set_model(model: str = Form(...)):
    """设置当前模型"""
    if not translator:
        raise HTTPException(status_code=503, detail="翻译服务尚未初始化")

    try:
        translator.set_model(model)
        return {"success": True, "message": f"已设置模型为: {model}"}
    except Exception as e:
        logger.error(f"设置模型失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"设置模型失败: {str(e)}")

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket连接端点"""
    try:
        await manager.connect(websocket, client_id)

        # 记录连接建立信息，同时输出到终端和Web界面
        connect_msg = f"WebSocket客户端 {client_id} 连接已建立"
        logger.info(connect_msg)

        # 发送欢迎消息
        await manager.send_message(client_id, json.dumps({
            "type": "system_log",
            "data": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - web.api - {connect_msg}"
        }))

        # 发送所有待处理的日志
        await global_ws_handler.flush_pending_logs()

        # 设置连接超时和心跳检测
        last_ping_time = asyncio.get_event_loop().time()
        ping_timeout = 180  # 3分钟超时，给客户端足够的时间

        while True:
            try:
                # 使用更长的超时接收消息，与前端心跳间隔匹配
                data = await asyncio.wait_for(websocket.receive_text(), timeout=70.0)

                # 处理从客户端接收的消息
                if data == "ping":
                    # 心跳检测
                    last_ping_time = asyncio.get_event_loop().time()
                    await manager.send_message(client_id, json.dumps({"type": "pong", "data": "pong"}))
                else:
                    # 普通消息回显
                    await manager.send_message(client_id, json.dumps({"type": "echo", "data": f"收到消息: {data}"}))

            except asyncio.TimeoutError:
                # 检查是否超过心跳超时时间
                current_time = asyncio.get_event_loop().time()
                if current_time - last_ping_time > ping_timeout:
                    logger.warning(f"WebSocket客户端 {client_id} 心跳超时，主动断开连接")
                    break
                # 如果没有超时，继续等待
                continue

    except WebSocketDisconnect:
        disconnect_msg = f"WebSocket客户端 {client_id} 正常断开连接"
        logger.info(disconnect_msg)
    except Exception as e:
        error_msg = f"WebSocket客户端 {client_id} 连接异常: {str(e)}"
        logger.error(error_msg)
    finally:
        # 确保清理连接
        manager.disconnect(client_id)
        final_msg = f"WebSocket客户端 {client_id} 连接已清理"
        logger.info(final_msg)

@app.post("/api/translate")
async def translate_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_lang: str = Form("auto"),
    target_lang: str = Form("zh"),
    use_terminology: bool = Form(True),
    preprocess_terms: bool = Form(False),
    export_pdf: bool = Form(False),
    output_format: str = Form("bilingual"),
    skip_translated_content: bool = Form(True),
    client_id: str = Form(None),
    translation_direction: str = Form(None)
):
    """上传文件并开始翻译任务"""
    logger.info(f"收到翻译请求: 文件={file.filename}, 源语言={source_lang}, 目标语言={target_lang}")

    if not translator:
        logger.error("翻译服务未初始化")
        raise HTTPException(status_code=503, detail="翻译服务尚未初始化")

    try:
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())
        logger.info(f"生成任务ID: {task_id}")

        # 保存上传的文件
        file_path = UPLOAD_DIR / file.filename
        logger.info(f"保存文件到: {file_path}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"文件保存成功，大小: {file_path.stat().st_size} 字节")

        # 创建输出文件路径
        filename, ext = os.path.splitext(file.filename)
        output_filename = f"{filename}_translated{ext}"
        output_path = OUTPUT_DIR / output_filename

        # 创建任务状态
        translation_tasks[task_id] = TranslationTask(
            task_id=task_id,
            filename=file.filename,
            status="pending",
            progress=0.0
        )

        # 如果提供了客户端ID，发送任务创建通知
        if client_id:
            try:
                # 检查是否在异步环境中
                asyncio.get_running_loop()
                # 如果能获取到事件循环，说明在异步环境中
                asyncio.create_task(manager.send_message(
                    client_id,
                    json.dumps({
                        "type": "task_created",
                        "data": {
                            "task_id": task_id,
                            "filename": file.filename,
                            "status": "pending"
                        }
                    })
                ))
            except RuntimeError:
                # 如果不在异步环境中，记录日志但不发送消息
                logger.warning("无法发送任务创建通知：不在异步环境中")

        # 记录翻译方向
        if translation_direction:
            logger.info(f"翻译方向: {translation_direction}")

        # 记录后台任务参数
        logger.info(f"准备提交后台翻译任务:")
        logger.info(f"  - 任务ID: {task_id}")
        logger.info(f"  - 输入文件: {str(file_path)}")
        logger.info(f"  - 输出文件: {str(output_path)}")
        logger.info(f"  - 客户端ID: {client_id}")
        logger.info(f"  - 使用术语库: {use_terminology}")
        logger.info(f"  - 术语预处理: {preprocess_terms}")
        logger.info(f"  - 跳过已翻译内容: {skip_translated_content}")

        # 在后台执行翻译任务
        try:
            background_tasks.add_task(
                process_translation,
                task_id,
                str(file_path),
                str(output_path),
                source_lang,
                target_lang,
                use_terminology,
                preprocess_terms,
                export_pdf,
                output_format,
                skip_translated_content,
                client_id,
                translation_direction
            )
            logger.info(f"后台翻译任务已成功提交: {task_id}")
        except Exception as e:
            logger.error(f"提交后台翻译任务失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"提交翻译任务失败: {str(e)}")

        return {"task_id": task_id, "message": "翻译任务已提交"}

    except Exception as e:
        logger.error(f"提交翻译任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提交翻译任务失败: {str(e)}")

async def process_translation(
    task_id: str,
    input_path: str,
    output_path: str,
    source_lang: str,
    target_lang: str,
    use_terminology: bool,
    preprocess_terms: bool = False,
    export_pdf: bool = False,
    output_format: str = "bilingual",
    skip_translated_content: bool = True,
    client_id: str = None,
    translation_direction: str = None
):
    """处理翻译任务"""
    # 立即记录函数被调用
    print(f"[DEBUG] process_translation 函数被调用，任务ID: {task_id}")
    logger.info(f"[DEBUG] process_translation 函数开始执行，任务ID: {task_id}")

    # 检查翻译服务是否可用
    if not translator:
        error_msg = "翻译服务未初始化，无法处理翻译任务"
        logger.error(error_msg)
        print(f"[ERROR] {error_msg}")
        return

    logger.info(f"翻译服务状态: 已初始化")

    # 设置WebSocket日志处理器
    ws_handler = None
    if client_id:
        ws_handler = WebSocketLogHandler(client_id)

        # 添加到根日志记录器，确保所有模块的日志都能被捕获
        root_logger = logging.getLogger()
        root_logger.addHandler(ws_handler)

        # 也添加到当前模块的日志记录器
        logger.addHandler(ws_handler)

        # 特别为翻译相关的日志记录器添加处理器
        translator_logger = logging.getLogger('services.translator')
        translator_logger.addHandler(ws_handler)

        document_processor_logger = logging.getLogger('services.document_processor')
        document_processor_logger.addHandler(ws_handler)

        pdf_processor_logger = logging.getLogger('services.pdf_processor')
        pdf_processor_logger.addHandler(ws_handler)

        excel_processor_logger = logging.getLogger('services.excel_processor')
        excel_processor_logger.addHandler(ws_handler)

        # 设置日志级别为INFO，确保重要信息都能传输
        ws_handler.setLevel(logging.INFO)

        logger.info(f"=== 开始处理翻译任务 {task_id} ===")
        logger.info(f"客户端ID: {client_id}")
        logger.info(f"输入文件: {input_path}")
        logger.info(f"输出文件: {output_path}")
        logger.info(f"源语言: {source_lang}, 目标语言: {target_lang}")
        logger.info(f"使用术语库: {use_terminology}")
        logger.info(f"术语预处理: {preprocess_terms}")
        logger.info(f"导出PDF: {export_pdf}")
        logger.info(f"输出格式: {output_format}")
        logger.info(f"跳过已翻译内容: {skip_translated_content}")
        logger.info(f"翻译方向: {translation_direction}")

        # 发送任务开始通知
        await manager.send_message(
            client_id,
            json.dumps({
                "type": "task_status",
                "data": {
                    "task_id": task_id,
                    "status": "processing",
                    "progress": 0.0,
                    "message": "开始处理翻译任务..."
                }
            })
        )

    try:
        # 更新任务状态
        translation_tasks[task_id].status = "processing"

        # 定义进度更新函数
        async def update_progress(progress: float, message: str = ""):
            translation_tasks[task_id].progress = progress
            if client_id:
                await manager.send_message(
                    client_id,
                    json.dumps({
                        "type": "task_status",
                        "data": {
                            "task_id": task_id,
                            "status": "processing",
                            "progress": progress,
                            "message": message
                        }
                    })
                )

        # 初始进度
        await update_progress(0.05, "加载术语库...")

        # 语言代码映射函数
        def map_language_code(lang_code):
            """将语言代码映射为中文名称"""
            mapping = {
                'en': '英语',
                'ja': '日语',
                'ko': '韩语',
                'fr': '法语',
                'de': '德语',
                'es': '西班牙语',
                'ru': '俄语'
            }
            return mapping.get(lang_code, lang_code)

        # 初始化target_language变量（确保在所有情况下都有定义）
        target_language = map_language_code(target_lang)

        # 加载术语库
        terminology = {}
        if use_terminology:
            try:
                terminology = load_terminology()
                logger.info(f"已加载术语库，包含 {len(terminology)} 种语言")
                for lang, terms in terminology.items():
                    logger.info(f"  - {lang}: {len(terms)} 个术语")

                # 根据翻译方向确定需要使用的术语库
                if translation_direction == "外语→中文":
                    # 外语→中文翻译：需要获取源语言的术语库
                    target_language = map_language_code(source_lang)  # 对于外语→中文，使用源语言的术语库

                    if target_language not in terminology:
                        logger.warning(f"术语库中不存在源语言 '{target_language}'，将使用空术语库")
                        # 创建空术语库
                        terminology[target_language] = {}

                    # 记录术语库大小
                    logger.info(f"源语言 '{target_language}' 术语库大小: {len(terminology.get(target_language, {}))} 个术语")

                    # 如果术语库为空，记录警告
                    if len(terminology.get(target_language, {})) == 0:
                        logger.warning(f"源语言 '{target_language}' 术语库为空，术语预处理可能无法正常工作")
                else:
                    # 中文→外语翻译：需要获取目标语言的术语库
                    target_language = map_language_code(target_lang)

                    if target_language not in terminology:
                        logger.warning(f"术语库中不存在目标语言 '{target_language}'，将使用空术语库")
                        # 创建空术语库
                        terminology[target_language] = {}

                    # 记录术语库大小
                    logger.info(f"目标语言 '{target_language}' 术语库大小: {len(terminology.get(target_language, {}))} 个术语")

                    # 如果术语库为空，记录警告
                    if len(terminology.get(target_language, {})) == 0:
                        logger.warning(f"目标语言 '{target_language}' 术语库为空，术语预处理可能无法正常工作")
            except Exception as e:
                logger.error(f"加载术语库失败: {str(e)}")
                logger.warning("将使用空术语库继续翻译")
                terminology = {}
                # 确保target_language在异常情况下也有定义
                target_language = map_language_code(target_lang)
        else:
            logger.info("根据用户设置，不使用术语库")
            # 确保在不使用术语库时target_language也有定义
            target_language = map_language_code(target_lang)

        await update_progress(0.1, "创建文档处理器...")

        # 检查翻译服务是否已初始化
        if not translator:
            await update_progress(0.0, "翻译服务尚未初始化")
            raise Exception("翻译服务尚未初始化")

        # 创建文档处理器
        factory = DocumentProcessorFactory()
        doc_processor = factory.create_processor(input_path, translator)

        # 设置文档处理器选项
        doc_processor.use_terminology = use_terminology
        doc_processor.preprocess_terms = preprocess_terms
        doc_processor.export_pdf = export_pdf
        doc_processor.output_format = output_format
        doc_processor.skip_translated_content = skip_translated_content

        # 确定翻译方向
        is_cn_to_foreign = False
        if translation_direction:
            is_cn_to_foreign = translation_direction == '中文→外语'
            logger.info(f"使用前端指定的翻译方向: {translation_direction}")
        else:
            is_cn_to_foreign = source_lang == 'zh' or (source_lang == 'auto' and target_lang != 'zh')
            logger.info(f"根据语言设置推断翻译方向: {'中文→外语' if is_cn_to_foreign else '外语→中文'}")

        # 设置源语言和目标语言
        if is_cn_to_foreign:
            if source_lang == 'auto':
                source_lang = 'zh'  # 如果是自动检测，但方向是中文→外语，则设置源语言为中文
            if target_lang == 'zh':
                logger.warning("翻译方向为中文→外语，但目标语言设置为中文，将调整目标语言为英语")
                target_lang = 'en'  # 如果方向是中文→外语，但目标语言是中文，则调整为英语
        else:
            if source_lang == 'auto' or source_lang == 'zh':
                logger.warning("翻译方向为外语→中文，但源语言设置为中文或自动，将调整源语言为英语")
                source_lang = 'en'  # 如果方向是外语→中文，但源语言是中文或自动，则调整为英语
            if target_lang != 'zh':
                logger.warning("翻译方向为外语→中文，但目标语言不是中文，将调整目标语言为中文")
                target_lang = 'zh'  # 如果方向是外语→中文，但目标语言不是中文，则调整为中文

        # 设置翻译方向
        doc_processor.is_cn_to_foreign = is_cn_to_foreign

        # 记录翻译选项
        logger.info(f"翻译选项设置:")
        logger.info(f"  - 使用术语库: {use_terminology}")
        logger.info(f"  - 术语预处理: {preprocess_terms}")
        logger.info(f"  - 导出PDF: {export_pdf}")
        logger.info(f"  - 输出格式: {output_format}")
        logger.info(f"  - 跳过已翻译内容: {skip_translated_content}")
        logger.info(f"  - 源语言: {source_lang}")
        logger.info(f"  - 目标语言: {target_lang}")
        logger.info(f"  - 翻译方向: {'中文→外语' if is_cn_to_foreign else '外语→中文'}")

        # 设置进度回调函数
        doc_processor.set_progress_callback(update_progress)

        await update_progress(0.15, "开始翻译文档...")

        # 记录术语预处理状态
        logger.info(f"术语预处理状态: {'启用' if preprocess_terms else '禁用'}")

        # 执行翻译
        output_path = doc_processor.process_document(
            input_path,
            target_language,  # 使用映射后的语言名称
            terminology,
            source_lang=source_lang,
            target_lang=target_lang
        )

        # 确保输出路径是绝对路径
        if not os.path.isabs(output_path):
            output_path = os.path.abspath(output_path)

        # 检查文件是否存在
        if not os.path.exists(output_path):
            logger.warning(f"翻译输出文件不存在: {output_path}")
            # 尝试在其他位置查找文件
            filename = os.path.basename(output_path)
            alt_paths = [
                os.path.join(OUTPUT_DIR, filename),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "输出", filename),
                os.path.join(os.getcwd(), "输出", filename)
            ]

            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    output_path = alt_path
                    logger.info(f"找到替代输出文件路径: {output_path}")
                    break

        # 更新任务状态
        translation_tasks[task_id].status = "completed"
        translation_tasks[task_id].progress = 1.0
        translation_tasks[task_id].output_file = output_path  # 保存完整路径

        # 发送任务完成通知
        if client_id:
            await manager.send_message(
                client_id,
                json.dumps({
                    "type": "task_status",
                    "data": {
                        "task_id": task_id,
                        "status": "completed",
                        "progress": 1.0,
                        "message": "翻译任务已完成",
                        "output_file": os.path.basename(output_path)
                    }
                })
            )

            # 清理WebSocket日志处理器
            if ws_handler:
                root_logger = logging.getLogger()
                root_logger.removeHandler(ws_handler)
                logger.removeHandler(ws_handler)

                # 清理翻译相关的日志记录器
                translator_logger = logging.getLogger('services.translator')
                translator_logger.removeHandler(ws_handler)

                document_processor_logger = logging.getLogger('services.document_processor')
                document_processor_logger.removeHandler(ws_handler)

                pdf_processor_logger = logging.getLogger('services.pdf_processor')
                pdf_processor_logger.removeHandler(ws_handler)

                excel_processor_logger = logging.getLogger('services.excel_processor')
                excel_processor_logger.removeHandler(ws_handler)

    except Exception as e:
        logger.error(f"翻译任务失败: {str(e)}")
        translation_tasks[task_id].status = "failed"

        # 发送任务失败通知
        if client_id:
            await manager.send_message(
                client_id,
                json.dumps({
                    "type": "task_status",
                    "data": {
                        "task_id": task_id,
                        "status": "failed",
                        "message": f"翻译任务失败: {str(e)}"
                    }
                })
            )

            # 清理WebSocket日志处理器
            if ws_handler:
                root_logger = logging.getLogger()
                root_logger.removeHandler(ws_handler)
                logger.removeHandler(ws_handler)

                # 清理翻译相关的日志记录器
                translator_logger = logging.getLogger('services.translator')
                translator_logger.removeHandler(ws_handler)

                document_processor_logger = logging.getLogger('services.document_processor')
                document_processor_logger.removeHandler(ws_handler)

                pdf_processor_logger = logging.getLogger('services.pdf_processor')
                pdf_processor_logger.removeHandler(ws_handler)

                excel_processor_logger = logging.getLogger('services.excel_processor')
                excel_processor_logger.removeHandler(ws_handler)

    finally:
        # 移除WebSocket日志处理器
        if ws_handler:
            logger.removeHandler(ws_handler)
            # 也从根日志记录器中移除
            root_logger = logging.getLogger()
            root_logger.removeHandler(ws_handler)
            logger.info(f"已清理任务 {task_id} 的WebSocket日志处理器")

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in translation_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    return translation_tasks[task_id]

@app.get("/api/download/{task_id}")
async def download_translated_file(task_id: str):
    """下载翻译后的文件"""
    if task_id not in translation_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = translation_tasks[task_id]
    if task.status != "completed" or not task.output_file:
        raise HTTPException(status_code=400, detail="文件尚未准备好")

    # 尝试在多个可能的位置查找文件
    possible_paths = []

    # 1. 首先在 OUTPUT_DIR 目录中查找文件
    possible_paths.append(str(OUTPUT_DIR / task.output_file))

    # 2. 在 "输出" 目录中查找
    alt_output_dir = Path(__file__).parent.parent / "输出"
    possible_paths.append(str(alt_output_dir / task.output_file))

    # 3. 在项目根目录的 "输出" 文件夹中查找
    root_output_dir = Path.cwd() / "输出"
    possible_paths.append(str(root_output_dir / task.output_file))

    # 4. 检查文件名是否包含完整路径
    if os.path.isabs(task.output_file):
        possible_paths.append(task.output_file)

    # 5. 尝试在当前工作目录中查找
    possible_paths.append(str(Path.cwd() / task.output_file))

    # 6. 尝试在当前工作目录的输出子目录中查找
    possible_paths.append(str(Path.cwd() / "输出" / os.path.basename(task.output_file)))

    # 查找文件
    file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            file_path = path
            break

    if not file_path:
        # 记录所有尝试的路径
        logger.error(f"文件不存在，尝试了以下路径:")
        for path in possible_paths:
            logger.error(f" - {path}")
        raise HTTPException(status_code=404, detail="文件不存在，请检查服务器日志")

    logger.info(f"下载文件: {file_path}")
    return FileResponse(
        path=file_path,
        filename=os.path.basename(task.output_file),
        media_type="application/octet-stream"
    )

# 术语库API
@app.get("/api/terminology")
async def get_terminology():
    """获取术语库"""
    terminology = load_terminology()
    return {"terminology": terminology}

@app.get("/api/terminology/languages")
async def get_terminology_languages():
    """获取术语库支持的语言列表"""
    terminology = load_terminology()
    languages = list(terminology.keys())
    return {"languages": languages}

@app.get("/api/terminology/{language}")
async def get_terminology_by_language(language: str):
    """获取指定语言的术语库"""
    terminology = load_terminology()
    if language not in terminology:
        raise HTTPException(status_code=404, detail=f"语言 '{language}' 不存在")
    return {"language": language, "terms": terminology[language]}

@app.post("/api/terminology")
async def update_terminology(terminology: dict):
    """更新整个术语库"""
    try:
        save_terminology(terminology)
        return {"success": True, "message": "术语库已更新"}
    except Exception as e:
        logger.error(f"更新术语库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新术语库失败: {str(e)}")

@app.post("/api/terminology/{language}")
async def update_terminology_by_language(language: str, terms: dict):
    """更新指定语言的术语库"""
    try:
        terminology = load_terminology()
        terminology[language] = terms
        save_terminology(terminology)
        return {"success": True, "message": f"{language}术语库已更新"}
    except Exception as e:
        logger.error(f"更新{language}术语库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新术语库失败: {str(e)}")

@app.get("/api/terminology/export/{language}")
async def export_terminology_by_language(language: str):
    """导出指定语言的术语库为CSV文件"""
    try:
        terminology = load_terminology()
        if language not in terminology:
            raise HTTPException(status_code=404, detail=f"语言 '{language}' 不存在")

        terms = terminology[language]
        if not terms:
            raise HTTPException(status_code=400, detail=f"{language}术语库为空")

        # 创建CSV内容
        import io
        import csv
        from datetime import datetime
        import urllib.parse

        # 使用utf-8编码创建StringIO
        output = io.StringIO(newline='')
        writer = csv.writer(output)

        # 根据语言设置CSV标题
        if language == "英语":
            writer.writerow(["中文术语", "英语术语"])
        elif language == "日语":
            writer.writerow(["中文术语", "日语术语"])
        elif language == "韩语":
            writer.writerow(["中文术语", "韩语术语"])
        elif language == "德语":
            writer.writerow(["中文术语", "德语术语"])
        elif language == "法语":
            writer.writerow(["中文术语", "法语术语"])
        elif language == "西班牙语":
            writer.writerow(["中文术语", "西班牙语术语"])
        else:
            writer.writerow(["中文术语", f"{language}术语"])

        # 写入术语数据
        for source, target in terms.items():
            # 清理术语中的回车符
            clean_source = source.replace('\r', '').replace('\n', '')
            clean_target = target.replace('\r', '').replace('\n', '')
            writer.writerow([clean_source, clean_target])

        # 生成文件名并进行URL编码
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{language}术语库_{timestamp}.csv"
        encoded_filename = urllib.parse.quote(filename)

        # 返回CSV文件，使用UTF-8编码
        content = output.getvalue().encode('utf-8')
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出{language}术语库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出术语库失败: {str(e)}")

@app.post("/api/terminology/import/{language}")
async def import_terminology_by_language(language: str, file: UploadFile = File(...)):
    """从CSV文件导入术语库"""
    try:
        # 读取文件内容
        content = await file.read()
        content = content.decode("utf-8")

        # 解析CSV内容
        import csv
        import io

        reader = csv.reader(io.StringIO(content))
        terms = {}

        # 跳过标题行
        next(reader, None)

        for row in reader:
            if len(row) >= 2:
                source = row[0].strip()
                target = row[1].strip()
                if source and target:
                    # 清理术语中的回车符和换行符
                    clean_source = source.replace('\r', '').replace('\n', '')
                    clean_target = target.replace('\r', '').replace('\n', '')
                    terms[clean_source] = clean_target

        if not terms:
            raise HTTPException(status_code=400, detail="未能从文件中解析出有效的术语")

        # 更新术语库，保持现有结构
        terminology = load_terminology()

        # 确保不覆盖其他语言的术语，只更新指定语言
        if language not in terminology:
            terminology[language] = {}

        # 合并新术语到现有术语库中，而不是完全替换
        existing_terms = terminology[language]
        for source, target in terms.items():
            existing_terms[source] = target

        terminology[language] = existing_terms
        save_terminology(terminology)

        return {
            "success": True,
            "message": f"成功导入 {len(terms)} 个术语到 {language} 术语库",
            "count": len(terms)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导入{language}术语库失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导入术语库失败: {str(e)}")

@app.get("/api/tasks")
async def get_all_tasks():
    """获取所有任务"""
    return list(translation_tasks.values())

@app.get("/api/logs/realtime")
async def get_realtime_logs(count: int = 100):
    """获取实时日志"""
    try:
        logs = realtime_monitor.get_recent_logs(count)
        return {
            "success": True,
            "logs": logs,
            "total": len(logs)
        }
    except Exception as e:
        logger.error(f"获取实时日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取实时日志失败: {str(e)}")

@app.get("/api/logs/since")
async def get_logs_since(since: str):
    """获取指定时间后的日志"""
    try:
        if not since:
            raise HTTPException(status_code=400, detail="缺少since参数")

        logs = realtime_monitor.get_logs_since(since)
        return {
            "success": True,
            "logs": logs,
            "total": len(logs)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取指定时间后的日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")

@app.get("/api/logs/stats")
async def get_exception_stats():
    """获取异常统计"""
    try:
        stats = realtime_monitor.get_exception_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"获取异常统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取异常统计失败: {str(e)}")

@app.post("/api/logs/clear")
async def clear_logs():
    """清空日志缓冲区"""
    try:
        realtime_monitor.clear_logs()
        return {
            "success": True,
            "message": "日志已清空"
        }
    except Exception as e:
        logger.error(f"清空日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空日志失败: {str(e)}")

# 启动实时日志监控
@app.on_event("startup")
async def startup_event():
    """应用启动时的事件"""
    logger.info("启动实时日志监控...")
    start_realtime_monitoring()
    logger.info("实时日志监控已启动")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的事件"""
    logger.info("停止实时日志监控...")
    stop_realtime_monitoring()
    logger.info("实时日志监控已停止")