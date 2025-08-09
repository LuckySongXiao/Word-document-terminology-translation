#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多格式文档翻译助手 - 简化打包脚本
基于现有环境直接打包，不重新安装依赖
"""

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('build.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class SimpleBuilder:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.build_dir = self.project_root / "build_temp"
        self.dist_dir = self.project_root / "dist"
        self.release_dir = self.project_root / "release"
        self.version = "3.0"
        self.build_date = datetime.now().strftime("%Y%m%d")
        
    def clean_build_dirs(self):
        """清理构建目录"""
        logger.info("清理构建目录...")
        
        dirs_to_clean = [self.build_dir, self.dist_dir, "build"]
        for dir_path in dirs_to_clean:
            if isinstance(dir_path, str):
                dir_path = Path(dir_path)
            if dir_path.exists():
                logger.info(f"删除目录: {dir_path}")
                shutil.rmtree(dir_path)
        
        # 清理spec文件
        for spec_file in self.project_root.glob("*.spec"):
            logger.info(f"删除spec文件: {spec_file}")
            spec_file.unlink()
            
        logger.info("✓ 清理完成")
    
    def check_python_environment(self):
        """检查Python环境"""
        logger.info("检查Python环境...")
        
        # 检查Python版本
        if sys.version_info < (3, 8):
            raise Exception("需要Python 3.8或更高版本")
        
        logger.info(f"Python版本: {sys.version}")
        logger.info(f"Python路径: {sys.executable}")
        
        # 检查PyInstaller
        try:
            import PyInstaller
            logger.info(f"PyInstaller版本: {PyInstaller.__version__}")
        except ImportError:
            logger.info("安装PyInstaller...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        
        logger.info("✓ Python环境检查通过")
    
    def create_pyinstaller_spec(self):
        """创建PyInstaller spec文件"""
        logger.info("创建PyInstaller spec文件...")
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
project_root = Path(r"{self.project_root}")

# 数据文件
datas = [
    (str(project_root / "data"), "data"),
    (str(project_root / "web" / "static"), "web/static"),
    (str(project_root / "web" / "templates"), "web/templates"),
    (str(project_root / "API_config"), "API_config"),
    (str(project_root / "config.json"), "."),
    (str(project_root / "logo.ico"), "."),
]

# 隐藏导入
hiddenimports = [
    # 核心模块
    'services.translator',
    'services.ollama_translator', 
    'services.zhipuai_translator',
    'services.siliconflow_translator',
    'services.base_translator',
    'services.excel_processor',
    'services.document_processor',
    'services.pdf_processor',
    'utils.terminology',
    'utils.api_config',
    'web.api',
    'web.realtime_logger',
    
    # Web框架
    'fastapi',
    'uvicorn',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.websockets',
    'websockets',
    'starlette',
    'starlette.applications',
    'starlette.routing',
    'starlette.responses',
    'starlette.staticfiles',
    'starlette.templating',
    'jinja2',
    'aiofiles',
    
    # 文档处理
    'docx',
    'openpyxl',
    'PyMuPDF',
    'fitz',
    'pandas',
    'numpy',
    
    # AI和网络
    'openai',
    'ollama',
    'requests',
    'httpx',
    'aiohttp',
    
    # 系统相关
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'webbrowser',
    'threading',
    'subprocess',
    'socket',
    'pathlib',
    'json',
    'logging',
    'datetime',
    
    # Windows特定
    'win32api',
    'win32con', 
    'win32security',
    'win32com',
    'win32com.client',
    'pythoncom',
    'pywintypes',
]

# 排除模块
excludes = [
    'matplotlib',
    'notebook',
    'jupyter',
    'IPython',
    'scipy',
    'sklearn',
    'tensorflow',
    'torch',
    'torchvision',
]

a = Analysis(
    ['launcher.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='多格式文档翻译助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "logo.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='多格式文档翻译助手',
)
'''
        
        spec_file = self.project_root / "app.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        logger.info(f"✓ spec文件创建完成: {spec_file}")
        return spec_file
    
    def build_executable(self, spec_file):
        """构建可执行文件"""
        logger.info("开始构建可执行文件...")
        
        # 运行PyInstaller
        cmd = [sys.executable, "-m", "PyInstaller", str(spec_file), "--clean", "--noconfirm"]
        logger.info(f"执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"PyInstaller构建失败:")
            logger.error(f"stdout: {result.stdout}")
            logger.error(f"stderr: {result.stderr}")
            raise Exception("PyInstaller构建失败")
        
        logger.info("✓ 可执行文件构建完成")
    
    def copy_additional_files(self):
        """复制额外的文件到发布目录"""
        logger.info("复制额外文件...")
        
        app_dir = self.dist_dir / "多格式文档翻译助手"
        if not app_dir.exists():
            raise Exception("未找到构建的应用目录")
        
        # 复制文档文件
        docs_to_copy = [
            "README.md",
            "使用说明.md", 
            "使用指南.md",
            "BUILD_README.md",
            "COMPLETE_BUILD_GUIDE.md"
        ]
        
        for doc in docs_to_copy:
            src = self.project_root / doc
            if src.exists():
                dst = app_dir / doc
                shutil.copy2(src, dst)
                logger.info(f"复制文档: {doc}")
        
        # 创建快速开始文件
        quick_start = app_dir / "快速开始.txt"
        with open(quick_start, 'w', encoding='utf-8') as f:
            f.write(f"""多格式文档翻译助手 v{self.version}
构建日期: {self.build_date}

快速开始:
1. 双击 "多格式文档翻译助手.exe" 启动程序
2. 程序会自动启动Web服务器并打开浏览器
3. 在Web界面中配置API密钥和术语库
4. 上传文档开始翻译

支持格式:
- Word文档 (.docx)
- PDF文档 (.pdf)
- Excel表格 (.xlsx)
- 文本文件 (.txt)

支持翻译引擎:
- 智谱AI (glm-4-flash-250414)
- Ollama (本地模型)
- 硅基流动 (SiliconFlow)

局域网访问:
其他设备可通过 http://[主机IP]:8000 访问

技术支持:
如遇问题请查看使用说明.md或联系技术支持
""")
        
        logger.info("✓ 额外文件复制完成")
    
    def build(self):
        """执行完整构建流程"""
        logger.info("=" * 60)
        logger.info("开始构建多格式文档翻译助手")
        logger.info("=" * 60)
        
        try:
            # 1. 环境检查
            self.check_python_environment()
            
            # 2. 清理构建目录
            self.clean_build_dirs()
            
            # 3. 创建spec文件
            spec_file = self.create_pyinstaller_spec()
            
            # 4. 构建可执行文件
            self.build_executable(spec_file)
            
            # 5. 复制额外文件
            self.copy_additional_files()
            
            logger.info("=" * 60)
            logger.info("✓ 构建完成!")
            logger.info("=" * 60)
            logger.info(f"构建结果位于: {self.dist_dir}")
            logger.info("可以将dist目录中的文件夹分发给用户使用")
            
        except Exception as e:
            logger.error(f"构建失败: {e}")
            raise

def main():
    """主函数"""
    try:
        builder = SimpleBuilder()
        builder.build()
    except Exception as e:
        logger.error(f"构建过程出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
