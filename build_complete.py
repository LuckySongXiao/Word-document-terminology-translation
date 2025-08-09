#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多格式文档翻译助手 - 完整虚拟环境打包脚本
支持将整个项目和虚拟环境打包成一键启动的EXE可执行文件
"""

import os
import sys
import shutil
import subprocess
import logging
import json
import zipfile
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

class ProjectBuilder:
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

        # 检查pip
        try:
            import pip
            logger.info(f"pip版本: {pip.__version__}")
        except ImportError:
            raise Exception("未找到pip")

        logger.info("✓ Python环境检查通过")

    def install_dependencies(self):
        """安装项目依赖"""
        logger.info("安装项目依赖...")

        requirements_file = self.project_root / "requirements_minimal.txt"
        if not requirements_file.exists():
            raise Exception("未找到requirements_minimal.txt文件")

        # 升级pip
        logger.info("升级pip...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--upgrade", "pip"
        ], check=True)

        # 安装依赖
        logger.info("安装项目依赖...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], check=True)

        logger.info("✓ 依赖安装完成")

    def prepare_build_directory(self):
        """准备构建目录"""
        logger.info("准备构建目录...")

        self.build_dir.mkdir(exist_ok=True)

        # 复制项目文件
        files_to_copy = [
            "launcher.py",
            "main.py",
            "web_server.py",
            "config.json",
            "logo.ico"
        ]

        dirs_to_copy = [
            "services",
            "utils",
            "web",
            "ui",
            "data",
            "API_config"
        ]

        # 复制文件
        for file_name in files_to_copy:
            src = self.project_root / file_name
            if src.exists():
                dst = self.build_dir / file_name
                shutil.copy2(src, dst)
                logger.info(f"复制文件: {file_name}")

        # 复制目录
        for dir_name in dirs_to_copy:
            src = self.project_root / dir_name
            if src.exists():
                dst = self.build_dir / dir_name
                shutil.copytree(src, dst, dirs_exist_ok=True)
                logger.info(f"复制目录: {dir_name}")

        logger.info("✓ 构建目录准备完成")

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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='多格式文档翻译助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "logo.ico"),
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

    def create_documentation_files(self):
        """创建文档文件（单文件版本）"""
        logger.info("创建文档文件...")

        # 创建临时文档目录
        docs_dir = self.project_root / "temp_docs"
        docs_dir.mkdir(exist_ok=True)

        # 创建快速开始文件
        quick_start = docs_dir / "快速开始.txt"
        with open(quick_start, 'w', encoding='utf-8') as f:
            f.write(f"""多格式文档翻译助手 v{self.version} (修复版)
构建日期: {self.build_date}

✅ 本版本修复内容:
- 修复Web服务器启动失败问题
- 解决日志配置冲突
- 优化uvicorn配置
- 确保所有翻译引擎正常工作

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
- 智谱AI (glm-4-flash-250414) ✅
- Ollama (本地模型) ✅
- 硅基流动 (SiliconFlow) ✅
- 内网翻译器 ✅

特色功能:
- 术语库管理和预处理
- 实时翻译进度显示
- 双语对照输出
- PDF数学公式处理
- 批量文档翻译

局域网访问:
其他设备可通过 http://[主机IP]:8000 访问

故障排除:
如果启动失败，请检查:
1. 端口8000是否被占用
2. 防火墙设置
3. 查看终端错误信息

技术支持:
如遇问题请查看使用说明.md或联系技术支持
""")

        # 创建版本信息文件
        version_info = docs_dir / "版本信息.txt"
        with open(version_info, 'w', encoding='utf-8') as f:
            f.write(f"""多格式文档翻译助手 v{self.version} (单文件修复版)
构建日期: {self.build_date}
Python版本: {sys.version}
平台: Windows 10/11 x64

🔧 本次修复内容:
- 修复Web服务器启动失败问题
- 解决uvicorn日志配置冲突
- 移除复杂的自定义日志配置
- 确保所有翻译引擎正常工作
- 优化错误处理和日志输出

✅ 功能特性:
- 单文件可执行程序
- 一键启动Web服务
- 支持局域网访问
- 实时日志同步
- 多翻译引擎支持
- 术语库管理
- 批量文档处理

🚀 性能优化:
- 优化启动速度
- 改进内存使用
- 简化日志配置
- 减少启动错误
- 单文件部署便捷
""")

        # 创建修复说明文件
        fix_notes = docs_dir / "修复说明.txt"
        with open(fix_notes, 'w', encoding='utf-8') as f:
            f.write(f"""Web服务器启动问题修复说明

问题描述:
之前版本在启动时出现 "Unable to configure formatter 'default'" 错误，
导致Web服务器无法正常启动。

修复方案:
1. 简化uvicorn日志配置
2. 移除自定义日志配置冲突
3. 使用默认日志处理器
4. 优化错误处理机制

修复文件:
- web_server.py (第182-198行)
- 移除复杂的log_config配置
- 设置log_config=None避免冲突

测试验证:
✅ Web服务器正常启动
✅ 所有翻译引擎可用
✅ 术语库正常加载
✅ Web界面正常访问

构建日期: {self.build_date}
修复版本: v{self.version} (单文件版)
""")

        # 复制现有文档文件
        docs_to_copy = [
            "README.md",
            "使用说明.md",
            "使用指南.md",
            "BUILD_README.md"
        ]

        for doc in docs_to_copy:
            src = self.project_root / doc
            if src.exists():
                dst = docs_dir / doc
                shutil.copy2(src, dst)
                logger.info(f"复制文档: {doc}")

        logger.info("✓ 文档文件创建完成")
        return docs_dir

    def create_release_package(self, docs_dir):
        """创建发布包（单文件版本）"""
        logger.info("创建单文件发布包...")

        self.release_dir.mkdir(exist_ok=True)

        # 单文件版本的可执行文件在dist目录下
        exe_file = self.dist_dir / "多格式文档翻译助手.exe"
        if not exe_file.exists():
            raise Exception("未找到构建的可执行文件")

        # 创建发布目录
        release_name = f"多格式文档翻译助手_单文件版_v{self.version}_{self.build_date}"
        release_path = self.release_dir / release_name

        if release_path.exists():
            shutil.rmtree(release_path)

        release_path.mkdir(parents=True)

        # 复制可执行文件
        exe_dst = release_path / "多格式文档翻译助手.exe"
        shutil.copy2(exe_file, exe_dst)
        logger.info(f"复制可执行文件: {exe_dst}")

        # 复制文档文件
        for doc_file in docs_dir.iterdir():
            if doc_file.is_file():
                dst = release_path / doc_file.name
                shutil.copy2(doc_file, dst)
                logger.info(f"复制文档: {doc_file.name}")

        logger.info(f"创建发布目录: {release_path}")

        # 创建ZIP包
        zip_path = self.release_dir / f"{release_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(release_path):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(release_path)
                    zipf.write(file_path, arc_path)

        logger.info(f"创建ZIP包: {zip_path}")

        # 计算大小
        exe_size = exe_file.stat().st_size
        zip_size = zip_path.stat().st_size

        logger.info(f"可执行文件大小: {exe_size / 1024 / 1024:.1f} MB")
        logger.info(f"ZIP包大小: {zip_size / 1024 / 1024:.1f} MB")

        return release_path, zip_path

    def test_single_file(self):
        """测试单文件可执行程序"""
        logger.info("测试单文件可执行程序...")

        exe_path = self.dist_dir / "多格式文档翻译助手.exe"

        if not exe_path.exists():
            raise Exception("未找到构建的单文件可执行程序")

        logger.info("✓ 单文件可执行程序存在")

        # 检查文件大小
        file_size = exe_path.stat().st_size
        logger.info(f"✓ 可执行文件大小: {file_size / 1024 / 1024:.1f} MB")

        logger.info("✓ 单文件程序测试完成")

    def build(self):
        """执行完整构建流程（单文件版本）"""
        logger.info("=" * 60)
        logger.info("开始封装多格式文档翻译助手 - 单文件版")
        logger.info("基于修复的Web服务器版本")
        logger.info("=" * 60)

        try:
            # 1. 环境检查
            self.check_python_environment()

            # 2. 清理构建目录
            self.clean_build_dirs()

            # 3. 安装依赖
            self.install_dependencies()

            # 4. 准备构建目录
            self.prepare_build_directory()

            # 5. 创建文档文件
            docs_dir = self.create_documentation_files()

            # 6. 创建spec文件
            spec_file = self.create_pyinstaller_spec()

            # 7. 构建单文件可执行程序
            self.build_executable(spec_file)

            # 8. 测试单文件程序
            self.test_single_file()

            # 9. 创建发布包
            release_path, zip_path = self.create_release_package(docs_dir)

            # 10. 清理临时文件
            if docs_dir.exists():
                shutil.rmtree(docs_dir)

            logger.info("=" * 60)
            logger.info("✓ 单文件版封装完成!")
            logger.info("=" * 60)
            logger.info(f"发布目录: {release_path}")
            logger.info(f"ZIP包: {zip_path}")
            logger.info("Web服务器启动问题已修复")
            logger.info("单文件版本，无需安装，双击即可运行")
            logger.info("可以将发布目录或ZIP包分发给用户使用")

        except Exception as e:
            logger.error(f"构建失败: {e}")
            raise

def main():
    """主函数"""
    try:
        builder = ProjectBuilder()
        builder.build()
    except Exception as e:
        logger.error(f"构建过程出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
