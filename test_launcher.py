#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试启动器 - 用于诊断打包问题
"""

import sys
import os
import traceback
from pathlib import Path

def test_imports():
    """测试所有必要的导入"""
    print("开始测试导入...")
    
    try:
        print("测试基础模块...")
        import tkinter as tk
        print("✓ tkinter 导入成功")
        
        from tkinter import ttk, messagebox
        print("✓ tkinter.ttk, messagebox 导入成功")
        
        import subprocess
        print("✓ subprocess 导入成功")
        
        import threading
        print("✓ threading 导入成功")
        
        import time
        print("✓ time 导入成功")
        
        import webbrowser
        print("✓ webbrowser 导入成功")
        
        import logging
        print("✓ logging 导入成功")
        
        import socket
        print("✓ socket 导入成功")
        
        import datetime
        print("✓ datetime 导入成功")
        
    except Exception as e:
        print(f"✗ 基础模块导入失败: {e}")
        traceback.print_exc()
        return False
    
    try:
        print("\n测试Web相关模块...")
        import uvicorn
        print("✓ uvicorn 导入成功")
        
        from web.api import app
        print("✓ web.api 导入成功")
        
        from utils.terminology import load_terminology
        print("✓ utils.terminology 导入成功")
        
        from services.translator import TranslationService
        print("✓ services.translator 导入成功")
        
    except Exception as e:
        print(f"✗ Web模块导入失败: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_environment():
    """测试运行环境"""
    print("\n检查运行环境...")
    
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"脚本路径: {__file__}")
    
    if getattr(sys, 'frozen', False):
        print("✓ 检测到打包环境")
        app_dir = Path(sys.executable).parent
        print(f"应用目录: {app_dir}")
        
        # 检查关键文件
        web_server_path = app_dir / "_internal" / "web_server.py"
        print(f"web_server.py路径: {web_server_path}")
        print(f"web_server.py存在: {web_server_path.exists()}")
        
        # 检查_internal目录内容
        internal_dir = app_dir / "_internal"
        if internal_dir.exists():
            print(f"_internal目录内容:")
            for item in internal_dir.iterdir():
                print(f"  - {item.name}")
        
    else:
        print("✓ 检测到源码环境")
        app_dir = Path(__file__).parent
        print(f"应用目录: {app_dir}")

def test_simple_gui():
    """测试简单的GUI"""
    print("\n测试GUI...")
    
    try:
        import tkinter as tk
        
        root = tk.Tk()
        root.title("测试窗口")
        root.geometry("300x200")
        
        label = tk.Label(root, text="测试成功！\n如果看到这个窗口，说明GUI正常工作")
        label.pack(expand=True)
        
        # 3秒后自动关闭
        root.after(3000, root.quit)
        
        print("✓ GUI测试窗口已创建，3秒后自动关闭")
        root.mainloop()
        
        return True
        
    except Exception as e:
        print(f"✗ GUI测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("文档术语翻译助手 - 启动器诊断工具")
    print("=" * 50)
    
    try:
        # 测试环境
        test_environment()
        
        # 测试导入
        if not test_imports():
            print("\n❌ 导入测试失败，程序无法正常运行")
            input("按回车键退出...")
            return
        
        print("\n✅ 所有导入测试通过")
        
        # 测试GUI
        if test_simple_gui():
            print("✅ GUI测试通过")
        else:
            print("❌ GUI测试失败")
            
        print("\n诊断完成！")
        
    except Exception as e:
        print(f"\n❌ 诊断过程中出现异常: {e}")
        traceback.print_exc()
    
    input("按回车键退出...")

if __name__ == "__main__":
    main()
