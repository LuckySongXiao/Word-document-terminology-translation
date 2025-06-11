import uvicorn
import argparse
import logging
import webbrowser
import threading
import time
import os
import sys
from web.api import app
from utils.terminology import load_terminology
from services.translator import TranslationService
from utils.ui_logger import setup_console_logger

# 设置实时日志系统
def setup_logging():
    """设置实时日志配置，支持终端控制台和Web界面同步显示"""
    try:
        # 使用控制台日志系统，支持实时日志文件
        root_logger = setup_console_logger()

        # 禁用uvicorn的默认日志配置，避免冲突
        logging.getLogger("uvicorn").handlers.clear()
        logging.getLogger("uvicorn.access").handlers.clear()
        logging.getLogger("uvicorn.error").handlers.clear()

        return logging.getLogger(__name__)
    except Exception as e:
        # 如果控制台日志系统失败，使用简化的控制台日志
        print(f"控制台日志系统初始化失败，使用简化日志: {e}")

        # 清除所有现有的处理器
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # 创建简单的控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)  # 改为DEBUG级别

        # 配置根日志记录器
        root_logger.setLevel(logging.DEBUG)  # 改为DEBUG级别
        root_logger.addHandler(console_handler)

        return logging.getLogger(__name__)

# 设置日志
logger = setup_logging()

# 同时创建web_server日志记录器，确保与WebSocket处理器配置一致
web_server_logger = logging.getLogger('web_server')
web_server_logger.setLevel(logging.INFO)

# 创建全局翻译服务实例
# 注意：在主程序中初始化，避免在导入时初始化
translator = None

def find_available_port(start_port: int, max_attempts: int = 10) -> int:
    """查找可用端口"""
    import socket

    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue

    raise RuntimeError(f"无法在端口范围 {start_port}-{start_port + max_attempts - 1} 内找到可用端口")

def open_browser(host, port):
    """在新线程中打开浏览器"""
    # 等待服务器启动
    time.sleep(1.5)
    # 构建URL
    url = f"http://{'localhost' if host == '0.0.0.0' else host}:{port}"
    # 打开浏览器
    logger.info(f"正在打开浏览器: {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.error(f"打开浏览器失败: {str(e)}")

def main():
    """Web服务器入口函数"""
    global translator

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='文档翻译助手Web服务器')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='服务器主机地址')
    parser.add_argument('--port', type=int, default=8000, help='服务器端口')
    parser.add_argument('--reload', action='store_true', help='是否启用热重载')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    args = parser.parse_args()

    # 查找可用端口
    try:
        actual_port = find_available_port(args.port)
        if actual_port != args.port:
            logger.info(f"端口 {args.port} 被占用，自动切换到端口 {actual_port}")
            web_server_logger.info(f"端口 {args.port} 被占用，自动切换到端口 {actual_port}")
    except RuntimeError as e:
        logger.error(str(e))
        web_server_logger.error(str(e))
        sys.exit(1)

    # 记录系统信息（同时使用两个日志记录器确保同步）
    logger.info("=" * 50)
    web_server_logger.info("=" * 50)
    logger.info("多格式文档翻译助手 - Web服务器启动")
    web_server_logger.info("多格式文档翻译助手 - Web服务器启动")
    logger.info("=" * 50)
    web_server_logger.info("=" * 50)
    logger.info(f"系统信息: Python {sys.version}")
    web_server_logger.info(f"系统信息: Python {sys.version}")
    logger.info(f"操作系统: {sys.platform}")
    web_server_logger.info(f"操作系统: {sys.platform}")
    logger.info(f"工作目录: {os.getcwd()}")
    web_server_logger.info(f"工作目录: {os.getcwd()}")
    logger.info("-" * 50)
    web_server_logger.info("-" * 50)

    # 初始化翻译服务
    try:
        logger.info("正在初始化翻译服务...")
        web_server_logger.info("正在初始化翻译服务...")

        # 在打包环境中，需要确保工作目录正确
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller打包环境
            logger.info(f"检测到PyInstaller环境，_MEIPASS: {sys._MEIPASS}")
            logger.info(f"当前工作目录: {os.getcwd()}")
            os.chdir(sys._MEIPASS)
            logger.info(f"切换工作目录到: {os.getcwd()}")

        # 设置翻译服务的日志级别为DEBUG
        import logging
        logging.getLogger('services.translator').setLevel(logging.DEBUG)
        logging.getLogger('services').setLevel(logging.DEBUG)

        logger.info("开始创建TranslationService实例...")
        translator = TranslationService()
        logger.info("TranslationService实例创建完成")

        # 将翻译服务实例传递给API模块
        from web.api import set_translator_instance
        set_translator_instance(translator)
        logger.info("翻译服务初始化成功")
        web_server_logger.info("翻译服务初始化成功")
    except Exception as e:
        import traceback
        logger.error(f"翻译服务初始化失败: {str(e)}")
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        web_server_logger.error(f"翻译服务初始化失败: {str(e)}")
        logger.error("将继续启动服务器，但翻译功能可能不可用")
        web_server_logger.error("将继续启动服务器，但翻译功能可能不可用")
        translator = None

    # 翻译服务状态检查（延迟到用户选择时进行）
    if translator:
        try:
            # 获取当前使用的模型
            current_model = translator.get_current_model()
            logger.info(f"当前配置的模型: {current_model}")
            logger.info("翻译服务已初始化，连接测试将在用户选择平台时进行")
            logger.info("-" * 50)

        except Exception as e:
            logger.error(f"获取翻译服务信息时发生错误: {str(e)}")
            logger.error("将继续启动服务器，但部分翻译功能可能不可用")

    # 预加载术语库
    try:
        terminology = load_terminology()
        if terminology:
            languages = list(terminology.keys())
            logger.info(f"成功加载术语库，包含 {len(languages)} 种语言: {', '.join(languages)}")
            for lang, terms in terminology.items():
                logger.info(f"  - {lang}: {len(terms)} 个术语")
        else:
            logger.warning("术语库为空，请在Web界面中导入术语")
    except Exception as e:
        logger.error(f"加载术语库失败: {str(e)}")
        logger.info("将使用空术语库启动服务器")

    logger.info("-" * 50)

    # 启动浏览器线程
    if not args.no_browser:
        threading.Thread(target=open_browser, args=(args.host, actual_port), daemon=True).start()

    # 启动服务器
    logger.info(f"启动Web服务器，地址: http://{args.host}:{actual_port}")
    logger.info("=" * 50)

    # 添加日志记录，确保这些信息能够被前端捕获
    logger.info("Web服务器已启动，等待客户端连接...")
    web_server_logger.info("Web服务器已启动，等待客户端连接...")
    logger.info("系统日志将在此处实时显示")
    web_server_logger.info("系统日志将在此处实时显示")

    # 记录一些重要的系统信息，这些信息会被发送到前端
    logger.info(f"术语库状态: {'已加载' if terminology else '未加载或为空'}")
    web_server_logger.info(f"术语库状态: {'已加载' if terminology else '未加载或为空'}")
    logger.info(f"翻译服务状态: {'已初始化' if translator else '未初始化'}")
    web_server_logger.info(f"翻译服务状态: {'已初始化' if translator else '未初始化'}")

    # 确保日志同步到终端和Web界面
    logger.info("日志系统已配置完成，终端控制台和Web界面将实时同步显示系统日志")
    web_server_logger.info("日志系统已配置完成，终端控制台和Web界面将实时同步显示系统日志")

    # 启动服务器
    try:
        # 简化uvicorn配置，避免日志配置冲突
        config = uvicorn.Config(
            app,
            host=args.host,
            port=actual_port,
            reload=args.reload,
            log_level="error",  # 降低uvicorn日志级别
            access_log=False,   # 禁用访问日志
            log_config=None     # 不使用自定义日志配置，避免冲突
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.error(f"Web服务器启动失败: {str(e)}")
        logger.error("请检查端口是否被占用或重新启动程序")

if __name__ == "__main__":
    main()
