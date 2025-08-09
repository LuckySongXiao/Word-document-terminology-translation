#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修复版本的main.py
解决GUI窗口空白和未响应问题
"""

import logging
import tkinter as tk
import tkinter.messagebox as messagebox
import sys
import os
import json
import time
import hashlib

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window_fixed import create_ui_fixed
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

def main():
    """主函数 - 修复版本"""
    # 设置简化的日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        print("=== 修复版本启动 ===")
        logger.info("开始启动修复版本")

        # 简化的授权检查
        print("1. 检查授权...")
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

        # 简化的服务初始化
        print("2. 初始化服务...")
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
        
        # 加载术语表
        print("3. 加载术语表...")
        logger.info("加载术语表...")
        terminology = load_terminology()
        
        # 创建主应用窗口
        print("4. 创建主窗口...")
        app_root = tk.Tk()
        app_root.title("多格式文档翻译助手 - 修复版")
        
        # 设置窗口大小和位置
        app_root.geometry("1200x800")
        app_root.update_idletasks()
        
        width = 1200
        height = 800
        x = (app_root.winfo_screenwidth() // 2) - (width // 2)
        y = (app_root.winfo_screenheight() // 2) - (height // 2)
        app_root.geometry(f"{width}x{height}+{x}+{y}")
        
        # 确保窗口正常显示
        app_root.state('normal')
        app_root.deiconify()
        
        # 创建菜单栏（简化版）
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
        
        # 创建主界面
        print("5. 创建主界面...")
        logger.info("创建主界面...")
        global status_var
        
        try:
            status_var = create_ui_fixed(app_root, terminology, translator)
            logger.info("主界面创建完成")
        except Exception as e:
            logger.error(f"创建主界面失败: {e}")
            messagebox.showerror("错误", f"创建主界面失败: {e}")
            return
        
        # 强制刷新窗口
        print("6. 刷新窗口...")
        app_root.update()
        app_root.update_idletasks()
        
        # 添加状态检查
        def gui_status_check():
            try:
                if app_root.winfo_exists():
                    print("DEBUG: GUI正在正常运行...")
                    logger.info("GUI正在正常运行")
                    app_root.after(10000, gui_status_check)  # 每10秒检查一次
            except:
                pass
        
        # 延迟启动状态检查
        app_root.after(3000, gui_status_check)
        
        # 启动主循环
        print("7. 启动主循环...")
        logger.info("启动主循环...")
        
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

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序启动被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        sys.exit(1)
