#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单文件启动器封装脚本 - 包含WebSocket修复和所有最新改进
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
import json

class SingleFileBuilder:
    def __init__(self):
        self.project_root = Path.cwd()
        self.version = "3.1"
        self.build_name = "多格式文档翻译助手_单文件版"
        self.release_dir = self.project_root / "release"

    def print_header(self):
        """打印构建头部信息"""
        print("=" * 80)
        print(f"🚀 多格式文档翻译助手 v{self.version} - 单文件版封装")
        print("=" * 80)
        print()
        print("📋 本次封装包含的最新改进:")
        print("✅ WebSocket连接稳定性修复")
        print("✅ 实时日志同步功能")
        print("✅ 启动器不自动关闭")
        print("✅ 完整的服务器控制功能")
        print("✅ 改进的UI和用户体验")
        print("✅ 单文件部署，无需安装")
        print("✅ 包含完整虚拟环境")
        print()

    def check_environment(self):
        """检查构建环境"""
        print("🔍 检查构建环境...")

        # 检查Python版本
        python_version = sys.version_info
        print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

        if python_version < (3, 8):
            print("❌ 错误: 需要Python 3.8或更高版本")
            return False

        # 检查关键文件
        required_files = [
            "launcher.py",
            "web_server.py",
            "web/api.py",
            "config.json",
            "requirements.txt"
        ]

        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)

        if missing_files:
            print(f"❌ 缺少关键文件: {', '.join(missing_files)}")
            return False

        # 检查虚拟环境
        if 'CONDA_DEFAULT_ENV' in os.environ:
            env_name = os.environ['CONDA_DEFAULT_ENV']
            print(f"当前虚拟环境: {env_name}")
        else:
            print("⚠️  警告: 未检测到conda虚拟环境")

        print("✅ 环境检查通过")
        return True

    def install_pyinstaller(self):
        """安装PyInstaller"""
        print("📦 检查PyInstaller...")

        try:
            import PyInstaller
            print(f"✅ PyInstaller已安装: {PyInstaller.__version__}")
            return True
        except ImportError:
            print("📥 安装PyInstaller...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                             check=True, capture_output=True)
                print("✅ PyInstaller安装成功")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ PyInstaller安装失败: {e}")
                return False

    def clean_build_dirs(self):
        """清理构建目录"""
        print("🧹 清理旧的构建文件...")

        dirs_to_clean = ["build", "dist"]
        for dir_name in dirs_to_clean:
            if Path(dir_name).exists():
                shutil.rmtree(dir_name)
                print(f"删除: {dir_name}")

        # 清理release目录
        if self.release_dir.exists():
            shutil.rmtree(self.release_dir)
            print(f"删除: {self.release_dir}")

        print("✅ 清理完成")

    def create_spec_file(self):
        """创建PyInstaller规格文件"""
        print("📝 创建PyInstaller规格文件...")

        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 数据文件 - 包含所有必要的资源
datas = [
    ('data', 'data'),
    ('web', 'web'),
    ('API_config', 'API_config'),
    ('config.json', '.'),
    ('web_server.py', '.'),
    ('main.py', '.'),
    ('services', 'services'),
    ('utils', 'utils'),
    ('ui', 'ui'),
    ('gui', 'gui'),
    ('tools', 'tools'),
    ('requirements.txt', '.'),
    ('logo.ico', '.'),
]

# 隐藏导入 - 确保所有依赖都被包含
hiddenimports = [
    # Web服务器相关
    'uvicorn',
    'uvicorn.main',
    'uvicorn.server',
    'uvicorn.config',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.websockets',
    'fastapi',
    'fastapi.applications',
    'fastapi.routing',
    'fastapi.middleware',
    'fastapi.middleware.cors',
    'fastapi.responses',
    'fastapi.staticfiles',
    'fastapi.templating',
    'jinja2',
    'starlette',
    'starlette.applications',
    'starlette.routing',
    'starlette.responses',
    'starlette.staticfiles',
    'starlette.templating',
    'starlette.middleware',
    'starlette.middleware.cors',
    'pydantic',
    'pydantic.main',
    'pydantic.fields',
    'websockets',
    'websockets.server',
    'websockets.client',
    'python-multipart',

    # 翻译服务相关
    'requests',
    'zhipuai',
    'ollama',
    'httpx',
    'openai',

    # 文档处理相关
    'openpyxl',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    'python-docx',
    'docx',
    'docx.document',
    'docx.shared',
    'PyPDF2',
    'pdfplumber',
    'Pillow',
    'PIL',
    'PIL.Image',

    # GUI相关
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.scrolledtext',

    # 系统相关
    'threading',
    'asyncio',
    'asyncio.events',
    'asyncio.protocols',
    'json',
    'pathlib',
    'datetime',
    'logging',
    'logging.handlers',
    'subprocess',
    'webbrowser',
    'socket',
    'time',
    'os',
    'sys',
    'shutil',
    'traceback',
    'queue',
    'concurrent.futures',
    'multiprocessing',
    'ssl',
    'urllib',
    'urllib.parse',
    'urllib.request',
    'base64',
    'hashlib',
    'uuid',
    'tempfile',
    'io',
    'csv',
    're',
    'collections',
    'functools',
    'itertools',
    'typing',
]

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
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
    name='{self.build_name}_v{self.version}',
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
    cofile=None,
    icon='logo.ico',
)
'''

        spec_file = f"{self.build_name}.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)

        print(f"✅ 规格文件已创建: {spec_file}")
        return spec_file

    def build_executable(self, spec_file):
        """构建可执行文件"""
        print("🔨 开始构建单文件可执行文件...")
        print("注意: 单文件构建可能需要10-15分钟，请耐心等待...")

        try:
            cmd = [
                sys.executable, "-m", "PyInstaller",
                spec_file,
                "--clean",
                "--noconfirm",
                "--log-level=INFO"
            ]

            print(f"执行命令: {' '.join(cmd)}")

            # 执行构建
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # 实时显示输出
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    line = output.strip()
                    if line:  # 只显示非空行
                        print(f"  {line}")

            return_code = process.poll()

            if return_code == 0:
                print("✅ 构建成功!")
                return True
            else:
                print(f"❌ 构建失败，返回码: {return_code}")
                return False

        except Exception as e:
            print(f"❌ 构建过程中出现错误: {e}")
            return False

    def organize_release(self):
        """整理发布文件"""
        print("📦 整理发布文件...")

        # 创建release目录
        self.release_dir.mkdir(exist_ok=True)

        # 查找生成的exe文件
        dist_dir = Path("dist")
        exe_file = dist_dir / f"{self.build_name}_v{self.version}.exe"

        if not exe_file.exists():
            print(f"❌ 未找到可执行文件: {exe_file}")
            return False

        # 创建最终发布目录
        final_dir = self.release_dir / f"{self.build_name}_v{self.version}_{time.strftime('%Y%m%d')}"
        final_dir.mkdir(exist_ok=True)

        # 复制可执行文件
        final_exe = final_dir / f"{self.build_name}_v{self.version}.exe"
        shutil.copy2(exe_file, final_exe)
        print(f"复制可执行文件: {final_exe}")

        # 复制配置文件
        config_files = [
            "config.json",
            "requirements.txt"
        ]

        for config_file in config_files:
            if Path(config_file).exists():
                shutil.copy2(config_file, final_dir / config_file)
                print(f"复制配置文件: {config_file}")

        # 复制API配置目录
        if Path("API_config").exists():
            shutil.copytree("API_config", final_dir / "API_config", dirs_exist_ok=True)
            print("复制API配置目录")

        # 复制术语库数据
        if Path("data").exists():
            shutil.copytree("data", final_dir / "data", dirs_exist_ok=True)
            print("复制术语库数据")

        return final_dir

    def create_documentation(self, release_dir):
        """创建使用文档"""
        print("📚 创建使用文档...")

        # 创建使用说明
        readme_content = f"""# {self.build_name} v{self.version}

## 🎯 最新版本特性

本版本是单文件版本，包含以下重要特性：

### ✅ 单文件部署
- **一键启动**: 双击exe文件即可运行，无需安装
- **完整集成**: 包含所有依赖和虚拟环境
- **绿色软件**: 不写注册表，不留系统垃圾

### ✅ WebSocket连接优化
- **稳定连接**: 修复了连接频繁断开的问题
- **实时同步**: 终端和Web界面日志完全同步
- **智能重连**: 优化的重连策略和心跳机制

### ✅ 启动器改进
- **持续监控**: 启动器保持运行，实时显示服务器状态
- **完整控制**: 重启、停止、打开浏览器等功能
- **详细日志**: 彩色分级日志显示，便于问题排查

### ✅ 翻译功能
- **多格式支持**: Word、PDF、Excel、TXT等
- **多引擎支持**: 智谱AI、Ollama、硅基流动、内网翻译器
- **术语管理**: 完整的术语库管理功能
- **批量处理**: 支持批量文档翻译

## 🚀 使用方法

### 1. 启动程序
双击 `{self.build_name}_v{self.version}.exe` 启动程序

### 2. 首次配置
1. 程序启动后会自动打开Web界面
2. 在翻译器设置中配置API密钥
3. 可选择智谱AI、Ollama等翻译引擎

### 3. 开始翻译
1. 上传要翻译的文档
2. 选择源语言和目标语言
3. 配置翻译选项（术语库、输出格式等）
4. 点击开始翻译

### 4. 术语库管理
1. 在术语库管理区域导入/导出术语
2. 支持Excel格式的术语库文件
3. 可按语言分类管理术语

## 📝 系统要求

- **操作系统**: Windows 10及以上版本
- **内存**: 建议4GB以上
- **磁盘空间**: 至少1GB可用空间
- **网络**: 在线翻译需要网络连接

## 🔧 API配置

### 智谱AI (推荐)
1. 访问 https://open.bigmodel.cn/ 注册账号
2. 获取API Key
3. 在程序中配置API Key

### Ollama (本地)
1. 安装Ollama软件
2. 下载翻译模型
3. 确保Ollama服务运行在11434端口

### 硅基流动
1. 访问 https://siliconflow.cn/ 注册账号
2. 获取API Key
3. 在程序中配置API Key

## 🌐 网络访问

程序启动后支持以下访问方式：
- **本机访问**: http://localhost:8000
- **局域网访问**: http://[本机IP]:8000

## 🔧 故障排除

### 常见问题
1. **程序无法启动**
   - 检查是否有杀毒软件拦截
   - 确保有足够的磁盘空间
   - 尝试以管理员身份运行

2. **翻译失败**
   - 检查网络连接
   - 确认API密钥配置正确
   - 查看启动器日志信息

3. **Web页面无法访问**
   - 检查防火墙设置
   - 确认端口8000未被占用
   - 尝试重启程序

### 日志查看
启动器窗口会显示详细的运行日志，包括：
- 服务器启动状态
- 翻译过程信息
- 错误和警告信息

## 📞 技术支持

如需技术支持，请提供：
- 启动器显示的完整错误信息
- 操作系统版本信息
- 具体的操作步骤和问题描述

## 📋 更新日志

### v{self.version} ({time.strftime('%Y-%m-%d')})
- ✅ 修复WebSocket连接稳定性问题
- ✅ 优化实时日志同步功能
- ✅ 改进启动器用户界面
- ✅ 增强错误处理和提示
- ✅ 单文件打包，简化部署

---
**版本**: v{self.version}
**构建时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
**构建环境**: {os.environ.get('CONDA_DEFAULT_ENV', 'Unknown')}
"""

        readme_path = release_dir / "使用说明.txt"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        print(f"✅ 使用说明已创建: {readme_path}")

        # 创建快速启动说明
        quick_start = f"""# 快速启动指南

## 🚀 一分钟上手

1. **启动程序**
   双击 `{self.build_name}_v{self.version}.exe`

2. **等待启动**
   程序会自动启动Web服务器并打开浏览器

3. **配置API**
   在翻译器设置中选择翻译引擎并配置API密钥

4. **开始翻译**
   上传文档，选择语言，点击开始翻译

## 📞 遇到问题？

- 查看启动器窗口的日志信息
- 确保网络连接正常
- 检查API密钥配置
- 尝试重启程序

更多详细信息请查看"使用说明.txt"
"""

        quick_path = release_dir / "快速启动.txt"
        with open(quick_path, 'w', encoding='utf-8') as f:
            f.write(quick_start)

        print(f"✅ 快速启动指南已创建: {quick_path}")

    def verify_build(self, release_dir):
        """验证构建结果"""
        print("🔍 验证构建结果...")

        exe_file = release_dir / f"{self.build_name}_v{self.version}.exe"

        if not exe_file.exists():
            print("❌ 可执行文件未找到")
            return False

        # 检查文件大小
        file_size = exe_file.stat().st_size / (1024 * 1024)  # MB
        print(f"可执行文件大小: {file_size:.1f} MB")

        if file_size < 50:  # 单文件版本应该比较大
            print("⚠️  警告: 文件大小异常，可能缺少依赖")

        # 检查配置文件
        required_files = ["使用说明.txt", "快速启动.txt"]
        for file_name in required_files:
            if not (release_dir / file_name).exists():
                print(f"❌ 缺少文件: {file_name}")
                return False

        print("✅ 构建验证通过")
        return True

    def build(self):
        """执行完整构建流程"""
        self.print_header()

        # 检查环境
        if not self.check_environment():
            return False

        # 安装PyInstaller
        if not self.install_pyinstaller():
            return False

        # 清理旧文件
        self.clean_build_dirs()

        # 创建规格文件
        spec_file = self.create_spec_file()

        # 构建可执行文件
        if not self.build_executable(spec_file):
            return False

        # 整理发布文件
        release_dir = self.organize_release()
        if not release_dir:
            return False

        # 创建文档
        self.create_documentation(release_dir)

        # 验证构建
        if not self.verify_build(release_dir):
            return False

        # 构建完成
        print()
        print("=" * 80)
        print("🎉 单文件版本构建完成!")
        print("=" * 80)
        print(f"📁 发布目录: {release_dir}")
        print(f"🚀 可执行文件: {self.build_name}_v{self.version}.exe")
        print()
        print("📋 特性说明:")
        print("✅ 单文件部署，无需安装")
        print("✅ 包含完整虚拟环境")
        print("✅ WebSocket连接稳定")
        print("✅ 实时日志同步")
        print("✅ 完整功能支持")
        print()
        print("📋 下一步:")
        print("1. 测试可执行文件")
        print("2. 验证所有功能正常")
        print("3. 准备分发给用户")
        print()

        return release_dir

def main():
    """主函数"""
    builder = SingleFileBuilder()

    try:
        release_dir = builder.build()
        if release_dir:
            # 询问是否打开发布目录
            try:
                choice = input("是否打开发布目录? (y/n): ").lower().strip()
                if choice in ['y', 'yes', '是']:
                    import subprocess
                    subprocess.run(['explorer', str(release_dir)], shell=True)
            except KeyboardInterrupt:
                print("\n构建完成")
        else:
            print("构建失败，请检查错误信息")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n构建被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"构建过程中出现未预期的错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
