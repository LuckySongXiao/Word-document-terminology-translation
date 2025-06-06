#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试构建环境
"""

import sys
import subprocess
from pathlib import Path

def test_environment():
    print("=" * 50)
    print("测试构建环境")
    print("=" * 50)
    
    # 检查Python版本
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    
    # 检查当前目录
    current_dir = Path.cwd()
    print(f"当前目录: {current_dir}")
    
    # 检查项目文件
    project_files = [
        "launcher.py",
        "web_server.py", 
        "config.json",
        "logo.ico"
    ]
    
    print("\n检查项目文件:")
    for file in project_files:
        file_path = current_dir / file
        exists = "✓" if file_path.exists() else "✗"
        print(f"  {exists} {file}")
    
    # 检查目录
    project_dirs = [
        "services",
        "utils",
        "web",
        "data",
        "API_config"
    ]
    
    print("\n检查项目目录:")
    for dir_name in project_dirs:
        dir_path = current_dir / dir_name
        exists = "✓" if dir_path.exists() else "✗"
        print(f"  {exists} {dir_name}/")
    
    # 检查关键依赖
    print("\n检查关键依赖:")
    dependencies = [
        "fastapi",
        "uvicorn", 
        "tkinter",
        "PyInstaller"
    ]
    
    for dep in dependencies:
        try:
            if dep == "PyInstaller":
                import PyInstaller
                print(f"  ✓ {dep} - 版本: {PyInstaller.__version__}")
            elif dep == "fastapi":
                import fastapi
                print(f"  ✓ {dep} - 版本: {fastapi.__version__}")
            elif dep == "uvicorn":
                import uvicorn
                print(f"  ✓ {dep}")
            elif dep == "tkinter":
                import tkinter
                print(f"  ✓ {dep}")
        except ImportError as e:
            print(f"  ✗ {dep} - 未安装: {e}")
    
    print("\n" + "=" * 50)
    print("环境检查完成")
    print("=" * 50)

if __name__ == "__main__":
    test_environment()
