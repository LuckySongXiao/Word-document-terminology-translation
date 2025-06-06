#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
带控制台的单文件启动器封装脚本 - 用于调试和异常排查
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
import json

class ConsoleBuilder:
    def __init__(self):
        self.project_root = Path.cwd()
        self.version = "3.1"
        self.build_name = "多格式文档翻译助手_调试版"
        self.release_dir = self.project_root / "release"

    def print_header(self):
        """打印构建头部信息"""
        print("=" * 80)
        print(f"🔧 多格式文档翻译助手 v{self.version} - 调试版封装（带控制台）")
        print("=" * 80)
        print()
        print("📋 调试版特性:")
        print("✅ 显示控制台窗口，便于查看异常报错")
        print("✅ 详细的调试日志输出")
        print("✅ 实时错误信息显示")
        print("✅ 包含所有最新修复")
        print("✅ 单文件部署，无需安装")
        print()

    def check_environment(self):
        """检查构建环境"""
        print("🔍 检查构建环境...")

        # 检查Python版本
        python_version = sys.version_info
        print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

        if python_version < (3, 8):
            print("❌ Python版本过低，需要3.8或更高版本")
            return False

        # 检查必要文件
        required_files = [
            "launcher.py",
            "web_server.py",
            "config.json",
            "logo.ico"
        ]

        for file_name in required_files:
            if not (self.project_root / file_name).exists():
                print(f"❌ 缺少必要文件: {file_name}")
                return False

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
        print("🧹 清理构建目录...")

        dirs_to_clean = ["build", "dist"]
        for dir_name in dirs_to_clean:
            dir_path = Path(dir_name)
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"  删除: {dir_name}")

        # 清理spec文件
        for spec_file in self.project_root.glob("*.spec"):
            spec_file.unlink()
            print(f"  删除: {spec_file.name}")

        print("✅ 清理完成")

    def create_spec_file(self):
        """创建PyInstaller规格文件（带控制台）"""
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

# 隐藏导入 - 确保所有必要模块都被包含
hiddenimports = [
    # Web框架相关
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

    # 翻译服务相关
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
    console=True,  # 显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    cofile=None,
    icon='logo.ico',
)
'''

        spec_file = f"{self.build_name}_v{self.version}.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)

        print(f"✅ 规格文件已创建: {spec_file}")
        return spec_file

    def build_executable(self, spec_file):
        """构建可执行文件"""
        print("🔨 开始构建调试版可执行文件...")
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

        # 复制内网模式相关文件
        intranet_files = [
            "启用内网模式.bat",
            "恢复外网模式.bat",
            "内网模式启动器.bat",
            "test_intranet_mode.py",
            "test_target_language_fix.py",
            "内网环境解决方案.md",
            "内网环境快速解决方案.txt",
            "内网翻译错误修复说明.md"
        ]

        for file_name in intranet_files:
            src_file = self.project_root / file_name
            if src_file.exists():
                dst_file = final_dir / file_name
                shutil.copy2(src_file, dst_file)
                print(f"复制内网模式文件: {file_name}")
            else:
                print(f"⚠️  内网模式文件不存在: {file_name}")

        return final_dir

    def create_documentation(self, release_dir):
        """创建使用文档"""
        print("📝 创建使用文档...")

        # 使用说明
        usage_guide = f"""多格式文档翻译助手 v{self.version} - 调试版使用说明

=== 调试版特性 ===

本版本专门用于调试和异常排查，具有以下特点：

✅ 显示控制台窗口 - 可以看到详细的运行日志和错误信息
✅ 实时错误输出 - 所有异常都会在控制台中显示
✅ 调试信息完整 - 包含详细的系统状态和处理过程
✅ 便于问题定位 - 出现问题时可以直接查看控制台信息
✅ 修复了变量作用域问题 - 解决了启动器的lambda表达式错误

=== 使用方法 ===

1. 双击运行 "{self.build_name}_v{self.version}.exe"
2. 程序启动后会显示两个窗口：
   - 控制台窗口：显示详细的运行日志和错误信息
   - 启动器窗口：图形界面操作窗口
3. 如果出现问题，请查看控制台窗口中的错误信息
4. 浏览器会自动打开Web界面

=== 最新修复 ===

• 修复了启动器中的变量作用域问题
• 解决了lambda表达式中的NameError和UnboundLocalError
• 改进了端口检测和服务器启动逻辑
• 优化了错误处理和日志显示

=== 注意事项 ===

• 请不要关闭控制台窗口，否则程序会退出
• 控制台窗口中的信息对于问题诊断非常重要
• 如果遇到问题，请截图保存控制台中的错误信息
• 本版本主要用于调试，正式使用建议使用标准版本

=== 常见问题 ===

Q: 为什么有两个窗口？
A: 控制台窗口用于显示调试信息，启动器窗口用于操作界面。

Q: 可以关闭控制台窗口吗？
A: 不建议关闭，关闭后程序会退出。

Q: 控制台显示很多信息正常吗？
A: 正常，这些都是调试信息，有助于问题诊断。

=== 技术支持 ===

如果遇到问题，请提供：
1. 控制台窗口中的完整错误信息
2. 操作步骤描述
3. 使用的文件类型和大小

版本: {self.version}
构建日期: {time.strftime('%Y-%m-%d')}
修复内容: 变量作用域问题、lambda表达式错误
"""

        usage_path = release_dir / "调试版使用说明.txt"
        with open(usage_path, 'w', encoding='utf-8') as f:
            f.write(usage_guide)

        print(f"✅ 使用说明已创建: {usage_path}")

        # 快速启动指南
        quick_start = f"""🚀 多格式文档翻译助手 v{self.version} - 调试版快速启动

=== 快速启动步骤 ===

1. 双击运行 "{self.build_name}_v{self.version}.exe"
2. 等待控制台显示 "Web版启动完成！"
3. 浏览器会自动打开 http://localhost:8000
4. 开始使用翻译功能

=== 内网环境使用 ===

如果在内网环境中使用：
1. 运行 "启用内网模式.bat" 配置内网模式
2. 程序将跳过外部API连接检查
3. 优先使用本地Ollama或内网翻译服务
4. 如需恢复外网模式，运行 "恢复外网模式.bat"

=== 调试信息查看 ===

• 控制台窗口会显示详细的运行信息
• 翻译过程中的所有步骤都会在控制台中显示
• 如果出现错误，控制台会显示具体的错误原因
• 请保持控制台窗口打开状态

=== 问题排查 ===

如果程序无法启动或出现错误：
1. 查看控制台窗口中的错误信息
2. 检查是否有端口占用提示
3. 确认网络连接正常（或启用内网模式）
4. 截图保存错误信息以便技术支持

更多详细信息请查看"调试版使用说明.txt"
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
        required_files = ["调试版使用说明.txt", "快速启动.txt"]
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

        # 显示完成信息
        print()
        print("=" * 80)
        print("🎉 调试版构建完成!")
        print("=" * 80)
        print()
        print(f"📁 发布目录: {release_dir}")
        print(f"🚀 可执行文件: {self.build_name}_v{self.version}.exe")
        print()
        print("📋 调试版特性:")
        print("✅ 显示控制台窗口，便于查看异常报错")
        print("✅ 详细的调试日志输出")
        print("✅ 实时错误信息显示")
        print("✅ 包含所有最新修复")
        print()
        print("⚠️  注意: 本版本主要用于调试，正式使用建议使用标准版本")
        print()

        return True

def main():
    """主函数"""
    builder = ConsoleBuilder()

    try:
        success = builder.build()
        if success:
            print("构建成功完成！")
            return 0
        else:
            print("构建失败，请检查错误信息")
            return 1
    except KeyboardInterrupt:
        print("\n用户取消构建")
        return 1
    except Exception as e:
        print(f"构建过程中出现异常: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    input("按回车键退出...")
    sys.exit(exit_code)
