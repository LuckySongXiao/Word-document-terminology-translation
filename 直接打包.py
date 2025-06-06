#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接打包脚本 - 最简单的打包方式
双击此文件即可开始打包
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("🚀 多格式文档翻译助手 - 直接打包")
    print("=" * 50)

    # 检查环境
    print(f"Python: {sys.version.split()[0]}")
    print(f"目录: {Path.cwd()}")

    if 'CONDA_DEFAULT_ENV' in os.environ:
        print(f"Conda环境: {os.environ['CONDA_DEFAULT_ENV']}")

    print()

    # 检查必需文件
    if not Path("launcher.py").exists():
        print("❌ 错误: 未找到 launcher.py")
        print("请确保在项目根目录运行此脚本")
        input("按回车键退出...")
        return

    print("✅ 项目文件检查通过")

    # 安装PyInstaller
    print("\n📦 检查PyInstaller...")
    try:
        import PyInstaller
        print(f"✅ PyInstaller已安装: {PyInstaller.__version__}")
    except ImportError:
        print("📥 安装PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 清理
    print("\n🧹 清理旧文件...")
    for folder in ["dist", "build"]:
        if Path(folder).exists():
            shutil.rmtree(folder)
            print(f"删除: {folder}")

    # 打包
    print("\n🔨 开始打包...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--windowed",
        "--name=多格式文档翻译助手",
        "--icon=logo.ico",
        "--add-data=data;data",
        "--add-data=web;web",
        "--add-data=API_config;API_config",
        "--add-data=config.json;.",
        "--add-data=web_server.py;.",
        "--add-data=services;services",
        "--add-data=utils;utils",
        "--add-data=requirements.txt;.",
        "--clean",
        "--noconfirm",
        "launcher.py"
    ]

    try:
        subprocess.run(cmd, check=True)
        print("\n✅ 打包成功！")

        result_path = Path("dist") / "多格式文档翻译助手"
        if result_path.exists():
            print(f"📁 结果位于: {result_path.absolute()}")

            # 创建使用说明
            readme_path = result_path / "使用说明.txt"
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write("""多格式文档翻译助手 v3.0

使用方法:
1. 双击 "多格式文档翻译助手.exe" 启动
2. 程序会自动打开Web界面
3. 配置API密钥开始翻译

支持格式: Word、PDF、Excel、TXT
""")

            print("📝 已创建使用说明")

            # 询问是否打开
            choice = input("\n是否打开结果文件夹？(y/n): ")
            if choice.lower() == 'y':
                if sys.platform == "win32":
                    os.startfile(result_path)

    except subprocess.CalledProcessError:
        print("\n❌ 打包失败")
        print("请检查错误信息")

    input("\n按回车键退出...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        input("按回车键退出...")
