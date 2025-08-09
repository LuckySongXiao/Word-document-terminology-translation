#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作版本的main.py - 基于成功的最小化版本
"""

import logging
import tkinter as tk
from tkinter import messagebox
import sys
import os

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('translation_app.log', encoding='utf-8')
        ]
    )
    logger = logging.getLogger(__name__)
    
    try:
        print("=== 多格式文档翻译助手启动 ===")
        
        # 1. 启动终端输出捕获
        logger.info("启动终端输出捕获...")
        from utils.terminal_capture import start_terminal_capture
        start_terminal_capture()
        logger.info("终端输出捕获已启动，所有输出将在GUI中实时显示")
        
        # 2. 检查授权
        logger.info("检查软件授权...")
        from utils.license import LicenseManager
        license_manager = LicenseManager()
        is_valid, message, license_data = license_manager.check_license()
        
        if not is_valid:
            logger.warning(f"授权验证失败: {message}")
            # 显示授权对话框
            result = messagebox.askquestion(
                "授权验证",
                f"授权验证失败：\n{message}\n\n是否继续使用？",
                icon='warning'
            )
            if result != 'yes':
                logger.info("用户选择退出程序")
                return
        else:
            logger.info("授权验证成功")
        
        # 3. 显示AI引擎选择对话框
        logger.info("显示AI引擎选择对话框...")
        from ui.ai_engine_selector import show_ai_engine_selector
        result, selected_engine, selected_model = show_ai_engine_selector(None)
        logger.info(f"AI引擎选择结果: {result}, 引擎: {selected_engine}, 模型: {selected_model}")
        
        if result != "confirm":
            logger.info("用户取消选择，程序退出")
            return
        
        # 4. 创建翻译服务
        logger.info(f"创建翻译服务，引擎: {selected_engine}, 模型: {selected_model}")
        from services.translator import TranslationService
        translator = TranslationService(
            preferred_engine=selected_engine,
            preferred_model=selected_model
        )
        logger.info("翻译服务创建完成")
        
        # 5. 创建文档处理器
        logger.info("创建文档处理器...")
        from services.document_processor import DocumentProcessor
        doc_processor = DocumentProcessor(translator)
        logger.info("文档处理器创建完成")
        
        # 6. 加载术语表
        logger.info("加载术语表...")
        from utils.terminology import load_terminology
        terminology = load_terminology()
        logger.info(f"术语表加载完成，包含 {len(terminology)} 种语言")
        
        # 7. 创建主应用窗口
        logger.info("创建主应用窗口...")
        app_root = tk.Tk()
        app_root.title("多格式文档翻译助手")
        
        # 8. 创建主界面
        logger.info("创建主界面...")
        from ui.main_window import create_ui
        status_var = create_ui(app_root, terminology, translator)
        logger.info("主界面创建完成")
        
        # 9. 启动主循环
        logger.info("启动主循环...")
        print("🎉 程序启动成功！主界面应该已经显示。")
        app_root.mainloop()
        logger.info("主循环结束")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序运行")
        print("\n程序已被用户中断，正在退出...")
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
        print(f"程序运行时发生错误：{str(e)}")
        import traceback
        traceback.print_exc()
        try:
            messagebox.showerror("程序错误", f"程序运行时发生错误：\n{str(e)}\n\n程序将退出。")
        except:
            pass
    finally:
        logger.info("程序退出")
        print("程序已退出")

if __name__ == "__main__":
    main()
