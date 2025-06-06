#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多格式文档翻译助手 - 简易打包脚本
避免批处理文件的编码问题
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header():
    print("=" * 60)
    print("多格式文档翻译助手 - 简易打包")
    print("=" * 60)
    print()

def check_environment():
    print("检查环境...")
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")

    # 检查conda环境
    if 'CONDA_DEFAULT_ENV' in os.environ:
        print(f"Conda环境: {os.environ['CONDA_DEFAULT_ENV']}")
    else:
        print("未检测到conda环境")

    print()

def install_pyinstaller():
    print("检查PyInstaller...")
    try:
        import PyInstaller
        print(f"PyInstaller已安装: {PyInstaller.__version__}")
    except ImportError:
        print("安装PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("PyInstaller安装完成")
    print()

def clean_old_files():
    print("清理旧文件...")

    # 清理目录
    for dir_name in ["dist", "build"]:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"删除目录: {dir_name}")

    # 清理spec文件
    for spec_file in Path(".").glob("*.spec"):
        spec_file.unlink()
        print(f"删除文件: {spec_file}")

    print("清理完成")
    print()

def build_package():
    print("开始打包...")

    # PyInstaller命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=多格式文档翻译助手",
        "--icon=logo.ico",
        "--windowed",
        "--onedir",
        "--add-data=data;data",
        "--add-data=web;web",
        "--add-data=API_config;API_config",
        "--add-data=config.json;.",
        "--hidden-import=services.translator",
        "--hidden-import=services.ollama_translator",
        "--hidden-import=services.zhipuai_translator",
        "--hidden-import=services.siliconflow_translator",
        "--hidden-import=services.base_translator",
        "--hidden-import=services.excel_processor",
        "--hidden-import=services.document_processor",
        "--hidden-import=services.pdf_processor",
        "--hidden-import=utils.terminology",
        "--hidden-import=utils.api_config",
        "--hidden-import=web.api",
        "--hidden-import=web.realtime_logger",
        "--hidden-import=fastapi",
        "--hidden-import=uvicorn",
        "--hidden-import=websockets",
        "--hidden-import=starlette",
        "--hidden-import=jinja2",
        "--hidden-import=aiofiles",
        "--hidden-import=docx",
        "--hidden-import=openpyxl",
        "--hidden-import=PyMuPDF",
        "--hidden-import=fitz",
        "--hidden-import=pandas",
        "--hidden-import=numpy",
        "--hidden-import=openai",
        "--hidden-import=ollama",
        "--hidden-import=requests",
        "--hidden-import=httpx",
        "--hidden-import=aiohttp",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        "--clean",
        "--noconfirm",
        "launcher.py"
    ]

    print("执行PyInstaller...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("打包失败！")
        print("错误信息:")
        print(result.stderr)
        return False

    print("打包成功！")
    return True

def copy_additional_files():
    print("复制额外文件...")

    app_dir = Path("dist") / "多格式文档翻译助手"
    if not app_dir.exists():
        print("错误: 未找到打包结果目录")
        return

    # 复制文档文件
    docs = ["README.md", "使用说明.md", "BUILD_README.md", "打包使用说明.md"]
    for doc in docs:
        if Path(doc).exists():
            shutil.copy2(doc, app_dir)
            print(f"复制: {doc}")

    # 创建快速开始文件
    quick_start = app_dir / "快速开始.txt"
    with open(quick_start, 'w', encoding='utf-8') as f:
        f.write("""多格式文档翻译助手 v3.0

使用方法:
1. 双击 "多格式文档翻译助手.exe" 启动程序
2. 程序会自动启动Web服务器并打开浏览器
3. 在Web界面中配置API密钥和术语库
4. 上传文档开始翻译

支持格式: Word、PDF、Excel、TXT
支持翻译引擎: 智谱AI、Ollama、硅基流动

局域网访问: 其他设备可通过 http://[主机IP]:8000 访问
""")

    print("额外文件复制完成")

def check_required_files():
    """检查必需的文件是否存在"""
    print("检查必需文件...")

    required_files = [
        "launcher.py",
        "config.json",
        "logo.ico"
    ]

    required_dirs = [
        "data",
        "web",
        "API_config",
        "services",
        "utils"
    ]

    missing_files = []

    # 检查文件
    for file_name in required_files:
        if not Path(file_name).exists():
            missing_files.append(f"文件: {file_name}")

    # 检查目录
    for dir_name in required_dirs:
        if not Path(dir_name).exists():
            missing_files.append(f"目录: {dir_name}")

    if missing_files:
        print("错误: 缺少必需的文件或目录:")
        for item in missing_files:
            print(f"  - {item}")
        return False

    print("所有必需文件检查通过")
    return True

def main():
    try:
        print_header()

        # 切换到项目目录
        project_dir = Path(__file__).parent
        os.chdir(project_dir)
        print(f"工作目录: {project_dir.absolute()}")
        print()

        # 检查必需文件
        if not check_required_files():
            print("请确保在正确的项目目录中运行此脚本")
            input("按回车键退出...")
            return 1
        print()

        # 检查环境
        check_environment()

        # 安装PyInstaller
        install_pyinstaller()

        # 清理旧文件
        clean_old_files()

        # 执行打包
        if build_package():
            # 复制额外文件
            copy_additional_files()

            print()
            print("=" * 60)
            print("打包完成！")
            print("=" * 60)
            result_dir = Path('dist') / '多格式文档翻译助手'
            print(f"结果位于: {result_dir.absolute()}")
            print()

            # 询问是否打开目录
            try:
                choice = input("是否打开结果目录？(y/n): ").strip().lower()
                if choice == 'y':
                    if sys.platform == "win32":
                        os.startfile(result_dir)
                    else:
                        subprocess.run(["open", str(result_dir)])
            except KeyboardInterrupt:
                print("\n用户取消操作")
        else:
            print("打包失败，请检查错误信息")
            input("按回车键退出...")
            return 1

    except KeyboardInterrupt:
        print("\n用户中断操作")
        return 1
    except Exception as e:
        print(f"发生错误: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        print("详细错误信息:")
        traceback.print_exc()
        input("按回车键退出...")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
