#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最小化版本的main.py，用于测试主界面显示
"""

import logging
import tkinter as tk
import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def main():
    """最小化主函数"""
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        print("=== 最小化程序启动 ===")
        
        # 1. 检查授权（简化版）
        print("1. 检查授权...")
        from utils.license import LicenseManager
        license_manager = LicenseManager()
        is_valid, message, license_data = license_manager.check_license()
        print(f"   授权状态: {'有效' if is_valid else '无效'}")
        
        if not is_valid:
            print(f"   授权失败: {message}")
            # 不退出，继续测试
        
        # 2. 创建主应用窗口
        print("2. 创建主应用窗口...")
        app_root = tk.Tk()
        app_root.title("多格式文档翻译助手 - 最小化测试")
        app_root.geometry("800x600")
        print("   主窗口创建完成")
        
        # 3. 创建翻译服务（简化版）
        print("3. 创建翻译服务...")
        from services.translator import TranslationService
        translator = TranslationService(
            preferred_engine="zhipuai",
            preferred_model="glm-4-flash-250414"
        )
        print("   翻译服务创建完成")
        
        # 4. 加载术语表
        print("4. 加载术语表...")
        from utils.terminology import load_terminology
        terminology = load_terminology()
        print(f"   术语表加载完成，包含 {len(terminology)} 种语言")
        
        # 5. 创建主界面
        print("5. 创建主界面...")
        from ui.main_window import create_ui
        print("   正在调用create_ui...")
        status_var = create_ui(app_root, terminology, translator)
        print("   create_ui调用完成")
        
        # 6. 启动主循环
        print("6. 启动主循环...")
        print("   窗口应该已经显示，正在启动mainloop...")
        app_root.mainloop()
        print("   主循环结束")
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("程序退出")

if __name__ == "__main__":
    main()
