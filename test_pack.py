#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试打包脚本 - 用于调试问题
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("=" * 50)
    print("测试打包脚本")
    print("=" * 50)
    print()
    
    # 基本信息
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print(f"当前目录: {Path.cwd()}")
    print()
    
    # 检查conda环境
    if 'CONDA_DEFAULT_ENV' in os.environ:
        print(f"Conda环境: {os.environ['CONDA_DEFAULT_ENV']}")
    else:
        print("未检测到conda环境")
    print()
    
    # 检查必需文件
    print("检查项目文件:")
    files_to_check = [
        "launcher.py",
        "config.json", 
        "logo.ico",
        "data",
        "web",
        "services",
        "utils",
        "API_config"
    ]
    
    all_exist = True
    for item in files_to_check:
        path = Path(item)
        exists = path.exists()
        status = "✓" if exists else "✗"
        file_type = "目录" if path.is_dir() else "文件"
        print(f"  {status} {item} ({file_type})")
        if not exists:
            all_exist = False
    
    print()
    
    if not all_exist:
        print("错误: 缺少必需的文件或目录")
        print("请确保在正确的项目目录中运行")
        input("按回车键退出...")
        return 1
    
    # 检查PyInstaller
    print("检查PyInstaller:")
    try:
        import PyInstaller
        print(f"  ✓ PyInstaller已安装: {PyInstaller.__version__}")
    except ImportError:
        print("  ✗ PyInstaller未安装")
        print("  正在安装...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                         check=True, capture_output=True)
            print("  ✓ PyInstaller安装成功")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ PyInstaller安装失败: {e}")
            input("按回车键退出...")
            return 1
    
    print()
    
    # 询问是否继续打包
    choice = input("是否继续执行打包？(y/n): ").strip().lower()
    if choice != 'y':
        print("用户取消打包")
        return 0
    
    print()
    print("开始打包...")
    
    # 清理旧文件
    print("清理旧文件...")
    for dir_name in ["dist", "build"]:
        dir_path = Path(dir_name)
        if dir_path.exists():
            import shutil
            shutil.rmtree(dir_path)
            print(f"  删除: {dir_name}")
    
    # 执行最简单的打包命令
    print("执行PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--windowed", 
        "--name=多格式文档翻译助手",
        "--add-data=data;data",
        "--add-data=web;web",
        "--add-data=API_config;API_config",
        "--add-data=config.json;.",
        "--clean",
        "--noconfirm",
        "launcher.py"
    ]
    
    print(f"命令: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("打包成功！")
        
        # 检查结果
        result_dir = Path("dist") / "多格式文档翻译助手"
        if result_dir.exists():
            print(f"结果位于: {result_dir.absolute()}")
            
            # 询问是否打开目录
            choice = input("是否打开结果目录？(y/n): ").strip().lower()
            if choice == 'y':
                if sys.platform == "win32":
                    os.startfile(result_dir)
        else:
            print("警告: 未找到打包结果目录")
            
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        print("错误输出:")
        print(e.stderr)
        input("按回车键退出...")
        return 1
    
    print()
    print("测试完成")
    input("按回车键退出...")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")
        sys.exit(1)
