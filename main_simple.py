#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版本的main.py，用于测试和调试
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
    """简化版主函数"""
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        print("=== 简化版程序启动 ===")
        
        # 1. 启动终端捕获
        print("1. 启动终端输出捕获...")
        from utils.terminal_capture import start_terminal_capture
        start_terminal_capture()
        print("   终端输出捕获启动完成")
        
        # 2. 检查授权（简化版）
        print("2. 检查授权...")
        from utils.license import LicenseManager
        license_manager = LicenseManager()
        is_valid, message, license_data = license_manager.check_license()
        print(f"   授权状态: {'有效' if is_valid else '无效'}")
        
        if not is_valid:
            print(f"   授权失败: {message}")
            return
        
        # 3. 显示AI引擎选择对话框
        print("3. 显示AI引擎选择对话框...")
        from ui.ai_engine_selector import show_ai_engine_selector
        result, selected_engine, selected_model = show_ai_engine_selector(None)
        print(f"   选择结果: {result}, 引擎: {selected_engine}, 模型: {selected_model}")
        
        if result != "confirm":
            print("   用户取消选择，程序退出")
            return
        
        # 4. 创建主应用窗口
        print("4. 创建主应用窗口...")
        app_root = tk.Tk()
        app_root.title("多格式文档翻译助手")
        print("   主窗口创建完成")
        
        # 5. 创建翻译服务
        print("5. 创建翻译服务...")
        from services.translator import TranslationService
        translator = TranslationService(
            preferred_engine=selected_engine,
            preferred_model=selected_model
        )
        print("   翻译服务创建完成")
        
        # 6. 创建文档处理器
        print("6. 创建文档处理器...")
        from services.document_processor import DocumentProcessor
        doc_processor = DocumentProcessor(translator)
        print("   文档处理器创建完成")
        
        # 7. 加载术语表
        print("7. 加载术语表...")
        from utils.terminology import load_terminology
        terminology = load_terminology()
        print(f"   术语表加载完成，包含 {len(terminology)} 种语言")
        
        # 8. 创建主界面
        print("8. 创建主界面...")
        from ui.main_window import create_ui
        status_var = create_ui(app_root, terminology, translator)
        print("   主界面创建完成")
        
        # 9. 启动主循环
        print("9. 启动主循环...")
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
