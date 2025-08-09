#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
彻底修复版本的main.py
解决GUI阻塞和未响应的根本问题
"""

import logging
import tkinter as tk
import tkinter.messagebox as messagebox
import sys
import os
import json
import time
import hashlib
import threading

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import create_ui
from utils.terminology import load_terminology
from utils.license import LicenseManager
from ui.license_dialog import LicenseDialog
from services.translator import TranslationService
from services.document_processor import DocumentProcessor

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    """保存配置文件"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        messagebox.showerror("错误", f"保存配置文件失败：{str(e)}")
        return False

# 全局变量定义
config = load_config()
status_var = None
doc_processor = None

def setup_safe_logging():
    """设置安全的日志系统"""
    # 创建简单的日志配置，避免复杂的处理器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def main():
    """主函数 - 彻底修复版本"""
    print("=== 彻底修复版本启动 ===")
    
    # 设置安全的日志系统
    logger = setup_safe_logging()
    logger.info("开始启动彻底修复版本")

    try:
        print("1. 检查授权...")
        # 简化的授权检查
        license_manager = LicenseManager()
        is_valid, message, license_data = license_manager.check_license()

        if not is_valid:
            response = messagebox.askquestion("授权验证",
                                             f"软件授权验证失败：{message}\n\n是否前往授权页面？")
            if response == 'yes':
                try:
                    license_root = tk.Tk()
                    license_dialog = LicenseDialog(license_root)
                    license_root.mainloop()
                    
                    # 重新检查授权
                    is_valid, message, license_data = license_manager.check_license()
                    if not is_valid:
                        messagebox.showerror("授权失败", f"软件未授权，程序将退出。\n{message}")
                        return
                except Exception as e:
                    logger.error(f"授权对话框显示出错: {str(e)}")
                    messagebox.showerror("错误", f"显示授权页面时出错: {str(e)}")
                    return
            else:
                return

        print("2. 初始化服务...")
        # 简化的服务初始化
        logger.info("使用默认AI引擎设置...")
        selected_engine = "zhipuai"
        selected_model = "glm-4-flash-250414"
        
        logger.info(f"创建翻译服务，引擎: {selected_engine}, 模型: {selected_model}")
        translator = TranslationService(
            preferred_engine=selected_engine,
            preferred_model=selected_model
        )
        
        global doc_processor
        logger.info("创建文档处理器...")
        doc_processor = DocumentProcessor(translator)
        
        print("3. 加载术语表...")
        logger.info("加载术语表...")
        terminology = load_terminology()
        
        print("4. 创建主窗口...")
        # 创建主应用窗口
        app_root = tk.Tk()
        app_root.title("多格式文档翻译助手 - 彻底修复版")
        
        # 设置窗口大小和位置
        app_root.geometry("1200x800")
        
        # 确保窗口正常显示
        app_root.state('normal')
        app_root.deiconify()
        
        # 创建简化的菜单栏
        menubar = tk.Menu(app_root)
        app_root.config(menu=menubar)
        
        # 创建帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        
        def show_license_info():
            license_info = f"授权状态：{message}\n"
            if license_data and "expiry_date" in license_data:
                expiry_date = time.strftime("%Y-%m-%d", time.localtime(license_data["expiry_date"]))
                license_info += f"到期时间：{expiry_date}\n"
            messagebox.showinfo("授权信息", license_info)
        
        help_menu.add_command(label="授权信息", command=show_license_info)
        
        # 记录使用情况
        license_manager._track_usage(license_data)
        
        print("5. 创建主界面...")
        logger.info("创建主界面...")
        global status_var
        
        # 关键修复：延迟创建UI，确保窗口完全初始化
        def delayed_ui_creation():
            try:
                print("开始延迟创建UI...")
                global status_var
                status_var = create_ui(app_root, terminology, translator)
                logger.info("主界面创建完成")
                print("UI创建完成")
                
                # 窗口居中
                app_root.update_idletasks()
                width = 1200
                height = 800
                x = (app_root.winfo_screenwidth() // 2) - (width // 2)
                y = (app_root.winfo_screenheight() // 2) - (height // 2)
                app_root.geometry(f"{width}x{height}+{x}+{y}")
                
                # 最终的窗口显示
                app_root.lift()
                app_root.focus_force()
                
                print("UI完全初始化完成")
                
            except Exception as e:
                logger.error(f"延迟创建UI失败: {e}")
                messagebox.showerror("错误", f"创建主界面失败: {e}")
                app_root.quit()
        
        # 延迟1秒后创建UI，确保窗口完全初始化
        app_root.after(1000, delayed_ui_creation)
        
        print("6. 启动主循环...")
        logger.info("启动主循环...")
        
        # 添加安全的状态检查
        def safe_status_check():
            try:
                if app_root.winfo_exists():
                    print("DEBUG: GUI正在正常运行...")
                    logger.info("GUI正在正常运行")
                    app_root.after(10000, safe_status_check)  # 每10秒检查一次
            except Exception as e:
                print(f"状态检查错误: {e}")
        
        # 延迟启动状态检查
        app_root.after(5000, safe_status_check)
        
        print("7. 调用mainloop()...")
        try:
            if app_root.winfo_exists():
                print("窗口存在，开始主循环")
                app_root.mainloop()
                print("主循环结束")
                logger.info("主循环结束")
            else:
                print("窗口不存在")
                logger.error("窗口不存在，无法启动主循环")
        except Exception as e:
            print(f"主循环失败: {e}")
            logger.error(f"主循环失败: {e}")
            raise

    except KeyboardInterrupt:
        logger.info("用户中断程序运行")
        print("\n程序已被用户中断，正在退出...")
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
        try:
            messagebox.showerror("程序错误", f"程序运行时发生错误：\n{str(e)}\n\n程序将退出。")
        except:
            print(f"程序运行时发生错误：{str(e)}")
    finally:
        logger.info("程序退出")

def get_terminology(target_lang):
    """获取指定语言的术语对照表"""
    try:
        # 直接从文件读取最新的术语表
        from utils.terminology import TERMINOLOGY_PATH
        with open(TERMINOLOGY_PATH, 'r', encoding='utf-8') as f:
            terminology = json.load(f)

        # 获取目标语言的术语表
        if target_lang in terminology:
            terms = terminology[target_lang]
            if terms:  # 确保术语表不为空
                logging.info(f"成功加载{target_lang}术语表，包含 {len(terms)} 个术语")
                return terms
            else:
                logging.warning(f"{target_lang}术语表为空")
                return {}
        else:
            logging.warning(f"未找到{target_lang}的术语表")
            return {}

    except Exception as e:
        logging.error(f"读取术语表出错: {e}")
        return {}

def translate_text(text, target_lang=None):
    """
    翻译文本的基础函数
    注意：此函数仅作为兼容性保留，实际翻译应使用TranslationService
    """
    logging.warning("使用了过时的translate_text函数，应该使用TranslationService")
    
    # 创建临时翻译服务
    translator = TranslationService()
    return translator.translate_text(text)

def translate_with_terminology(text, target_lang):
    """使用术语表辅助翻译"""
    
    # 获取目标语言的术语表
    terms_dict = get_terminology(target_lang)
    
    if not terms_dict:
        logging.warning(f"未找到{target_lang}术语表或术语表为空，将直接进行翻译")
        return translate_text(text, target_lang)
    
    # 注意：这个函数已经过时，不应该再使用
    # 现在应该直接使用DocumentProcessor中的翻译逻辑
    logging.warning("translate_with_terminology函数已过时，应该使用DocumentProcessor进行翻译")

    # 直接调用翻译服务，不使用复杂的提示词
    translator = TranslationService()
    return translator.translate_text(text)

def check_translator_status():
    """检查翻译器状态"""
    try:
        if doc_processor and doc_processor.translator:
            # 检查当前选择的翻译器状态
            current_type = doc_processor.translator.get_current_translator_type()
            
            if current_type == "zhipuai":
                zhipuai_status = doc_processor.translator._check_zhipuai_available()
                if zhipuai_status:
                    status_var.set("智谱AI服务正常")
                else:
                    status_var.set("智谱AI服务不可用，请检查配置")
            elif current_type == "ollama":
                ollama_status = doc_processor.translator.check_ollama_service()
                if ollama_status:
                    status_var.set("Ollama服务正常")
                else:
                    status_var.set("Ollama服务不可用，请检查配置")
            elif current_type == "siliconflow":
                siliconflow_status = doc_processor.translator.check_siliconflow_service()
                if siliconflow_status:
                    status_var.set("硅基流动服务正常")
                else:
                    status_var.set("硅基流动服务不可用，请检查配置")
            elif current_type == "intranet":
                intranet_status = doc_processor.translator.check_intranet_service()
                if intranet_status:
                    status_var.set("内网OpenAI服务正常")
                else:
                    status_var.set("内网OpenAI服务不可用，请检查配置")
            else:
                status_var.set(f"当前翻译器类型: {current_type}")
        else:
            status_var.set("翻译服务未初始化")
    except Exception as e:
        status_var.set(f"检查服务状态时出错: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序启动被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
