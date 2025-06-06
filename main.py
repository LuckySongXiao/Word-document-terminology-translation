import logging
from ui.main_window import create_ui
from utils.terminology import load_terminology, TERMINOLOGY_PATH
import json
from utils.license import LicenseManager
from ui.license_dialog import LicenseDialog
import tkinter as tk
import tkinter.messagebox as messagebox
import sys
import os
import hashlib
import time
import configparser
from services.translator import TranslationService
from services.document_processor import DocumentProcessor
from services.ollama_translator import OllamaTranslator
from services.ollama_manager import OllamaManager
from utils.api_config import APIConfig
from services.siliconflow_translator import SiliconFlowTranslator
from services.zhipuai_translator import ZhipuAITranslator

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

# 在main函数之前加载配置
config = load_config()

# 全局变量定义
status_var = None  # 状态变量，将在UI创建时被赋值

def main():
    # 设置日志
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    try:
        # 检查授权
        license_manager = LicenseManager()
        is_valid, message, license_data = license_manager.check_license()

        if not is_valid:
            # 显示授权对话框
            response = messagebox.askquestion("授权验证",
                                             f"软件授权验证失败：{message}\n\n是否前往授权页面？")
            if response == 'yes':
                try:
                    # 创建新的Tk窗口作为授权窗口
                    license_root = tk.Tk()
                    license_dialog = LicenseDialog(license_root)

                    # 运行授权窗口的主循环
                    license_root.mainloop()

                    # 重新检查授权
                    is_valid, message, license_data = license_manager.check_license()

                    if not is_valid:
                        messagebox.showerror("授权失败", f"软件未授权，程序将退出。\n{message}")
                        return

                except KeyboardInterrupt:
                    logger.info("用户中断授权过程")
                    return
                except Exception as e:
                    logger.error(f"授权对话框显示出错: {str(e)}")
                    messagebox.showerror("错误", f"显示授权页面时出错: {str(e)}")
                    return
            else:
                return

        # 授权验证通过，创建主应用窗口
        app_root = tk.Tk()
        app_root.title("多格式文档翻译助手")

        # 创建菜单栏
        menubar = tk.Menu(app_root)
        app_root.config(menu=menubar)

        # 创建设置菜单
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)

        # 创建服务实例
        translator = TranslationService()
        global doc_processor  # 声明全局变量
        doc_processor = DocumentProcessor(translator)

        def show_api_settings():
            settings_window = tk.Toplevel(app_root)
            settings_window.title("智谱API配置")
            settings_window.geometry("400x450")

            # 创建API配置目录
            api_config_dir = os.path.join(os.path.dirname(__file__), "API_config")
            if not os.path.exists(api_config_dir):
                os.makedirs(api_config_dir)

            # API密钥设置
            api_frame = tk.LabelFrame(settings_window, text="API设置", padx=10, pady=5)
            api_frame.pack(fill="x", padx=10, pady=5)

            tk.Label(api_frame, text="API Key:").pack(anchor="w")
            api_key_entry = tk.Entry(api_frame, width=40, show="*")
            api_key_entry.pack(fill="x")

            # 从配置文件中获取API key
            zhipu_config_path = os.path.join(api_config_dir, "zhipu_api.json")
            try:
                if os.path.exists(zhipu_config_path):
                    with open(zhipu_config_path, "r", encoding="utf-8") as f:
                        zhipu_config = json.load(f)
                        current_api_key = zhipu_config.get("api_key", "")
                        api_key_entry.insert(0, current_api_key)
            except Exception as e:
                logger.error(f"读取智谱API配置失败: {str(e)}")

            # 模型选择
            model_frame = tk.LabelFrame(settings_window, text="模型设置", padx=10, pady=5)
            model_frame.pack(fill="x", padx=10, pady=5)

            tk.Label(model_frame, text="选择模型:").pack(anchor="w")
            current_model = config.get("zhipuai_translator", {}).get("model", "glm-4-flash")
            model_var = tk.StringVar(value=current_model)

            # 创建临时翻译器获取模型列表
            temp_translator = ZhipuAITranslator("")
            models = temp_translator.get_available_models()

            for model in models:
                tk.Radiobutton(model_frame,
                              text=model,
                              variable=model_var,
                              value=model).pack(anchor="w")

            # 其他参数设置
            params_frame = tk.LabelFrame(settings_window, text="参数设置", padx=10, pady=5)
            params_frame.pack(fill="x", padx=10, pady=5)

            tk.Label(params_frame, text="温度 (0.0-1.0):").pack(anchor="w")
            temp_var = tk.StringVar(value=str(config.get("zhipuai_translator", {}).get("temperature", 0.2)))
            temp_entry = tk.Entry(params_frame, textvariable=temp_var, width=10)
            temp_entry.pack(anchor="w")

            # 超时设置
            timeout_frame = tk.LabelFrame(settings_window, text="超时设置", padx=10, pady=5)
            timeout_frame.pack(fill="x", padx=10, pady=5)

            tk.Label(timeout_frame, text="请求超时时间 (秒):").pack(anchor="w")
            timeout_var = tk.StringVar(value=str(config.get("zhipuai_translator", {}).get("timeout", 60)))
            timeout_entry = tk.Entry(timeout_frame, textvariable=timeout_var, width=10)
            timeout_entry.pack(anchor="w")

            def validate_settings():
                """验证设置"""
                api_key = api_key_entry.get().strip()
                if not api_key:
                    messagebox.showwarning("警告", "API Key不能为空")
                    return False

                try:
                    temp = float(temp_var.get())
                    if not 0 <= temp <= 1:
                        messagebox.showwarning("警告", "温度值必须在0到1之间")
                        return False
                except ValueError:
                    messagebox.showwarning("警告", "温度值必须是有效的数字")
                    return False

                try:
                    timeout = float(timeout_var.get())
                    if timeout <= 0:
                        messagebox.showwarning("警告", "超时时间必须大于0")
                        return False
                except ValueError:
                    messagebox.showwarning("警告", "超时时间必须是有效的数字")
                    return False

                if not model_var.get():
                    messagebox.showwarning("警告", "请选择一个模型")
                    return False

                return True

            def check_connection():
                """检查API连接"""
                api_key = api_key_entry.get().strip()
                if not api_key:
                    messagebox.showwarning("警告", "请先输入API Key")
                    return

                try:
                    # 创建临时翻译器进行测试
                    test_model = model_var.get() or "glm-4-flash"  # 确保有默认值
                    temp_translator = ZhipuAITranslator(api_key, test_model)

                    # 显示测试中的状态
                    status_label = tk.Label(settings_window, text="正在测试连接...", fg="blue")
                    status_label.pack(pady=5)
                    settings_window.update()

                    if temp_translator._check_zhipuai_available():
                        status_label.config(text="连接测试成功", fg="green")
                        messagebox.showinfo("成功", "API连接测试成功！")
                    else:
                        status_label.config(text="连接测试失败", fg="red")
                        messagebox.showerror("错误", "API连接测试失败，请检查API Key是否正确")
                except Exception as e:
                    messagebox.showerror("错误", f"连接测试失败：{str(e)}")
                finally:
                    try:
                        status_label.destroy()
                    except:
                        pass

            def save_settings():
                """保存设置"""
                if not validate_settings():
                    return

                try:
                    api_key = api_key_entry.get().strip()

                    # 保存API key到单独的配置文件
                    zhipu_config = {"api_key": api_key}
                    with open(zhipu_config_path, "w", encoding="utf-8") as f:
                        json.dump(zhipu_config, f, indent=4, ensure_ascii=False)

                    # 更新主配置
                    if "zhipuai_translator" not in config:
                        config["zhipuai_translator"] = {}

                    config["zhipuai_translator"].update({
                        "type": "zhipuai",
                        "model": model_var.get(),
                        "temperature": float(temp_var.get()),
                        "timeout": float(timeout_var.get())
                    })

                    if save_config(config):
                        # 重新初始化翻译服务
                        global doc_processor
                        translator = TranslationService()
                        doc_processor.translator = translator

                        messagebox.showinfo("成功", "设置已保存并更新")
                        settings_window.destroy()

                        # 更新主界面状态
                        if 'status_var' in globals():
                            status_var.set("配置已更新，正在检查服务状态...")
                            app_root.update()
                            check_translator_status()
                except Exception as e:
                    messagebox.showerror("错误", f"保存设置失败：{str(e)}")

            # 按钮区域
            button_frame = tk.Frame(settings_window)
            button_frame.pack(pady=10)

            tk.Button(button_frame, text="保存", command=save_settings).pack(side="left", padx=5)

        settings_menu.add_command(label="智谱API设置", command=show_api_settings)

        def show_ollama_settings():
            settings_window = tk.Toplevel(app_root)
            settings_window.title("Ollama设置")
            settings_window.geometry("400x550")

            # 创建API配置目录
            api_config_dir = os.path.join(os.path.dirname(__file__), "API_config")
            if not os.path.exists(api_config_dir):
                os.makedirs(api_config_dir)

            # API地址设置
            api_frame = tk.LabelFrame(settings_window, text="API设置", padx=10, pady=5)
            api_frame.pack(fill="x", padx=10, pady=5)

            tk.Label(api_frame, text="API地址:").pack(anchor="w")
            api_url_entry = tk.Entry(api_frame, width=40)
            api_url_entry.pack(fill="x")

            # 从配置文件中获取API URL
            ollama_config_path = os.path.join(api_config_dir, "ollama_api.json")
            default_api_url = "http://localhost:11434"

            try:
                if os.path.exists(ollama_config_path):
                    with open(ollama_config_path, "r", encoding="utf-8") as f:
                        ollama_config = json.load(f)
                        current_api_url = ollama_config.get("api_url", default_api_url)
                else:
                    current_api_url = default_api_url
            except Exception as e:
                logger.error(f"读取Ollama API配置失败: {str(e)}")
                current_api_url = default_api_url

            api_url_entry.insert(0, current_api_url)

            # 添加默认值提示
            tk.Label(api_frame, text=f"默认地址: {default_api_url}", fg="gray").pack(anchor="w")

            # 可用模型显示
            model_frame = tk.LabelFrame(settings_window, text="可用模型", padx=10, pady=5)
            model_frame.pack(fill="x", padx=10, pady=5)

            model_listbox = tk.Listbox(model_frame, height=5)
            model_listbox.pack(fill="x")

            # 超时设置
            timeout_frame = tk.LabelFrame(settings_window, text="超时设置", padx=10, pady=5)
            timeout_frame.pack(fill="x", padx=10, pady=5)

            tk.Label(timeout_frame, text="获取模型列表超时时间 (秒):").pack(anchor="w")
            model_timeout_var = tk.StringVar(value=str(config.get("fallback_translator", {}).get("model_list_timeout", 10)))
            model_timeout_entry = tk.Entry(timeout_frame, textvariable=model_timeout_var, width=10)
            model_timeout_entry.pack(anchor="w", pady=(0, 5))

            tk.Label(timeout_frame, text="翻译请求超时时间 (秒):").pack(anchor="w")
            translate_timeout_var = tk.StringVar(value=str(config.get("fallback_translator", {}).get("translate_timeout", 60)))
            translate_timeout_entry = tk.Entry(timeout_frame, textvariable=translate_timeout_var, width=10)
            translate_timeout_entry.pack(anchor="w")

            def refresh_models():
                """刷新模型列表"""
                try:
                    current_url = api_url_entry.get().strip()
                    if not current_url:
                        messagebox.showwarning("警告", "请输入API地址")
                        return

                    # 清空当前列表
                    model_listbox.delete(0, tk.END)

                    # 创建临时翻译器获取模型列表
                    temp_translator = OllamaTranslator(
                        model="",
                        api_url=current_url,
                        model_list_timeout=float(model_timeout_var.get())
                    )

                    models = temp_translator.get_available_models()
                    if models:
                        for model in models:
                            model_listbox.insert(tk.END, model)
                        # 选择第一个模型
                        model_listbox.selection_set(0)
                    else:
                        messagebox.showwarning("警告", "未找到可用模型")
                except Exception as e:
                    messagebox.showerror("错误", f"刷新模型列表失败：{str(e)}")

            def validate_settings():
                """验证设置"""
                try:
                    # 验证API地址
                    api_url = api_url_entry.get().strip()
                    if not api_url:
                        messagebox.showwarning("警告", "API地址不能为空")
                        return False

                    # 验证是否选择了模型
                    if not model_listbox.curselection():
                        messagebox.showwarning("警告", "请选择一个模型")
                        return False

                    # 验证超时设置
                    model_timeout = float(model_timeout_var.get())
                    translate_timeout = float(translate_timeout_var.get())
                    if model_timeout <= 0 or translate_timeout <= 0:
                        messagebox.showwarning("警告", "超时时间必须大于0")
                        return False

                    return True
                except ValueError:
                    messagebox.showwarning("警告", "请输入有效的超时时间")
                    return False

            def save_settings():
                """保存设置"""
                if not validate_settings():
                    return

                try:
                    current_api_url = api_url_entry.get().strip()

                    # 获取选中的模型
                    selection = model_listbox.curselection()
                    if not selection:
                        messagebox.showwarning("警告", "请选择一个模型")
                        return
                    selected_model = model_listbox.get(selection[0])

                    # 保存API配置
                    ollama_config = {
                        "api_url": current_api_url,
                        "api_history": []
                    }

                    # 读取现有历史记录
                    try:
                        if os.path.exists(ollama_config_path):
                            with open(ollama_config_path, "r", encoding="utf-8") as f:
                                existing_config = json.load(f)
                                existing_history = existing_config.get("api_history", [])
                        else:
                            existing_history = []
                    except:
                        existing_history = []

                    # 更新历史记录
                    if current_api_url not in existing_history:
                        existing_history.insert(0, current_api_url)
                    # 保留最近的5个记录
                    ollama_config["api_history"] = existing_history[:5]

                    # 保存到配置文件
                    with open(ollama_config_path, "w", encoding="utf-8") as f:
                        json.dump(ollama_config, f, indent=4, ensure_ascii=False)

                    # 更新主配置
                    if "fallback_translator" not in config:
                        config["fallback_translator"] = {}

                    config["fallback_translator"].update({
                        "type": "ollama",
                        "api_url": current_api_url,
                        "model": selected_model,
                        "model_list_timeout": float(model_timeout_var.get()),
                        "translate_timeout": float(translate_timeout_var.get())
                    })

                    if save_config(config):
                        # 重新初始化翻译服务
                        global doc_processor
                        translator = TranslationService()
                        doc_processor.translator = translator

                        messagebox.showinfo("成功", "设置已保存并更新")
                        settings_window.destroy()

                        # 更新主界面状态
                        if 'status_var' in globals():
                            status_var.set("配置已更新，正在检查服务状态...")
                            app_root.update()
                            check_translator_status()
                except Exception as e:
                    messagebox.showerror("错误", f"保存设置失败：{str(e)}")

            # 添加刷新按钮
            refresh_button = tk.Button(model_frame, text="刷新模型列表", command=refresh_models)
            refresh_button.pack(pady=5)

            # 保存按钮
            tk.Button(settings_window, text="保存", command=save_settings).pack(pady=10)

            # 初始刷新模型列表
            refresh_models()

        settings_menu.add_command(label="Ollama设置", command=show_ollama_settings)

        def show_siliconflow_settings():
            settings_window = tk.Toplevel(app_root)
            settings_window.title("硅基流动设置")
            settings_window.geometry("400x720")

            # 创建API配置目录
            api_config_dir = os.path.join(os.path.dirname(__file__), "API_config")
            if not os.path.exists(api_config_dir):
                os.makedirs(api_config_dir)

            siliconflow_config_path = os.path.join(api_config_dir, "siliconflow_api.json")

            def validate_settings():
                """验证设置"""
                api_key = api_key_entry.get().strip()
                if not api_key:
                    messagebox.showwarning("警告", "API Key不能为空")
                    return False

                try:
                    timeout = float(timeout_var.get())
                    if timeout <= 0:
                        messagebox.showwarning("警告", "超时时间必须大于0")
                        return False
                except ValueError:
                    messagebox.showwarning("警告", "超时时间必须是有效的数字")
                    return False

                if not model_var.get():
                    messagebox.showwarning("警告", "请选择一个模型")
                    return False

                return True

            def save_settings():
                """保存设置"""
                if not validate_settings():
                    return

                try:
                    api_key = api_key_entry.get().strip()

                    # 保存API key到单独的配置文件
                    siliconflow_config = {"api_key": api_key}
                    with open(siliconflow_config_path, "w", encoding="utf-8") as f:
                        json.dump(siliconflow_config, f, indent=4, ensure_ascii=False)

                    # 更新主配置
                    if "siliconflow_translator" not in config:
                        config["siliconflow_translator"] = {}

                    config["siliconflow_translator"].update({
                        "type": "siliconflow",
                        "model": model_var.get(),
                        "timeout": float(timeout_var.get())
                    })

                    if save_config(config):
                        # 重新初始化翻译服务
                        global doc_processor
                        translator = TranslationService()
                        doc_processor.translator = translator

                        messagebox.showinfo("成功", "设置已保存并更新")
                        settings_window.destroy()

                        # 更新主界面状态
                        if 'status_var' in globals():
                            status_var.set("配置已更新，正在检查服务状态...")
                            app_root.update()
                            check_translator_status()
                except Exception as e:
                    messagebox.showerror("错误", f"保存设置失败：{str(e)}")

            # API密钥设置
            api_frame = tk.LabelFrame(settings_window, text="API设置", padx=10, pady=5)
            api_frame.pack(fill="x", padx=10, pady=5)

            tk.Label(api_frame, text="API Key:").pack(anchor="w")
            api_key_entry = tk.Entry(api_frame, width=40, show="*")
            api_key_entry.pack(fill="x")

            # 从配置文件中获取API key
            try:
                if os.path.exists(siliconflow_config_path):
                    with open(siliconflow_config_path, "r", encoding="utf-8") as f:
                        siliconflow_config = json.load(f)
                        current_api_key = siliconflow_config.get("api_key", "")
                        api_key_entry.insert(0, current_api_key)
            except Exception as e:
                logger.error(f"读取硅基流动API配置失败: {str(e)}")

            # 添加超时设置
            timeout_frame = tk.LabelFrame(settings_window, text="超时设置", padx=10, pady=5)
            timeout_frame.pack(fill="x", padx=10, pady=5)

            tk.Label(timeout_frame, text="请求超时时间 (秒):").pack(anchor="w")
            timeout_var = tk.StringVar(value=str(config.get("siliconflow_translator", {}).get("timeout", 60)))
            timeout_entry = tk.Entry(timeout_frame, textvariable=timeout_var, width=10)
            timeout_entry.pack(anchor="w")

            # 添加超时设置说明
            tk.Label(timeout_frame, text="注意：较长的文本可能需要更长的超时时间", fg="gray").pack(anchor="w", pady=(5, 0))

            # 模型选择
            model_frame = tk.LabelFrame(settings_window, text="模型设置", padx=10, pady=5)
            model_frame.pack(fill="x", padx=10, pady=5)

            tk.Label(model_frame, text="选择模型:").pack(anchor="w")
            model_var = tk.StringVar(value=config.get("siliconflow_translator", {}).get("model", "deepseek-ai/DeepSeek-V2.5"))

            # 创建临时翻译器获取模型列表
            temp_translator = SiliconFlowTranslator("")
            models = temp_translator.get_available_models()

            for model in models:
                tk.Radiobutton(model_frame,
                              text=model,
                              variable=model_var,
                              value=model).pack(anchor="w")

            # 保存按钮
            tk.Button(settings_window, text="保存", command=save_settings).pack(pady=10)

        settings_menu.add_command(label="硅基流动设置", command=show_siliconflow_settings)

        # 创建帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)

        # 添加查看授权信息的菜单项
        def show_license_info():
            # 获取授权信息
            license_info = f"授权状态：{message}\n"
            if license_data:
                if "expiry_date" in license_data:
                    expiry_date = time.strftime("%Y-%m-%d", time.localtime(license_data["expiry_date"]))
                    license_info += f"到期时间：{expiry_date}\n"
                if license_id in usage_data:
                    license_info += f"已使用次数：{current_usage}次\n"
                    license_info += f"剩余使用次数：{remaining_usage}次\n"
                    license_info += f"总授权次数：{max_usage}次\n"

            messagebox.showinfo("授权信息", license_info)

        help_menu.add_command(label="授权信息", command=show_license_info)

        # 记录使用情况
        license_manager._track_usage(license_data)

        # 获取使用情况数据
        usage_data = license_manager._load_usage_data()
        license_id = hashlib.md5(str(license_data).encode()).hexdigest()

        if license_id in usage_data:
            # 计算剩余使用次数
            license_period = license_data.get("valid_days", 365)

            # 如果是永久授权，使用很大的期限
            if license_data.get("expiry_date", 0) > time.time() + 30*365*24*3600:
                license_period = 36500  # 约100年

            max_usage = int(license_manager.usage_limit_per_year * (license_period / 365))
            current_usage = usage_data[license_id]["count"]
            remaining_usage = max_usage - current_usage

            # 如果剩余使用次数小于最大次数的10%，提示用户
            if remaining_usage < max_usage * 0.1 and max_usage > 0:
                def show_usage_notice():
                    messagebox.showwarning(
                        "授权使用次数即将用尽",
                        f"剩余使用次数: {remaining_usage}次\n已使用: {current_usage}次\n"
                        f"总授权次数: {max_usage}次\n\n请联系软件供应商更新授权"
                    )
                app_root.after(2000, show_usage_notice)

        # 检查授权是否即将到期
        if "即将过期" in message:
            # 在主窗口加载完成后显示提醒
            def show_expiry_notice():
                messagebox.showwarning("授权即将过期", message + "\n\n请及时联系软件供应商续期授权")
            app_root.after(2000, show_expiry_notice)

        # 初始化术语表
        terminology = load_terminology()

        # 启动UI
        create_ui(app_root, terminology)

        # 运行主循环，保持窗口打开
        app_root.mainloop()

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

    Args:
        text: 要翻译的文本
        target_lang: 目标语言（此参数在当前实现中未使用，但保留以兼容旧代码）
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

    # 构建带术语表的提示词
    prompt = f"""你是一位专业的技术文档翻译专家。请将以下文本翻译成{target_lang}，并严格遵循以下要求：

1. 这是一份专业的技术文档，请保持专业性和准确性
2. 必须严格使用以下专业术语对照表进行翻译，这些是标准化的术语：

专业术语对照表：
"""

    # 添加术语表内容，按照更清晰的格式排列
    for cn_term, foreign_term in terms_dict.items():
        prompt += f"[{cn_term}] ➜ [{foreign_term}]\n"

    prompt += f"""
翻译要求：
1. 上述术语表中的词语必须严格按照给定的对应关系翻译，不得改变
2. 遇到术语表中的词语时，必须使用术语表中的标准译法
3. 对于术语表之外的词语，请采用该领域的专业表达方式
4. 保持原文的格式、换行和标点符号
5. 确保专业性和一致性，禁止出现翻译解析，禁止输出术语表
6.不要输出与翻译结果无关的扩展补充内容，例如提示词、总结、解释等

原文：
{text}

译文："""

    # 调用翻译API
    translated = translate_text(prompt, target_lang)
    logging.info(f"使用了 {len(terms_dict)} 个{target_lang}术语进行翻译")

    return translated

def check_translator_status():
    """检查翻译器状态"""
    try:
        if doc_processor and doc_processor.translator:
            zhipuai_status = doc_processor.translator._check_zhipuai_available()
            if zhipuai_status:
                status_var.set("智谱AI服务正常")
            else:
                status_var.set("智谱AI服务不可用，请检查配置")
        else:
            status_var.set("翻译服务未初始化")
    except Exception as e:
        status_var.set(f"检查服务状态时出错: {str(e)}")

if __name__ == "__main__":
    try:
        # 处理命令行参数
        if len(sys.argv) > 1 and sys.argv[1] == "--activate-license":
            # 从临时文件读取授权码并激活
            try:
                temp_license_path = os.path.join(os.environ.get('TEMP', '.'), 'temp_license.dat')
                if os.path.exists(temp_license_path):
                    with open(temp_license_path, 'r', encoding='utf-8') as f:
                        license_code = f.read().strip()

                    license_manager = LicenseManager()
                    is_valid, message, license_data = license_manager.verify_license(license_code)

                    root = tk.Tk()
                    root.withdraw()  # 隐藏窗口，只显示对话框

                    try:
                        if is_valid and license_manager.save_license(license_code):
                            messagebox.showinfo("成功", f"管理员权限授权激活成功！\n{message}")
                        else:
                            messagebox.showerror("失败", "管理员权限授权激活失败：" + message)
                    finally:
                        try:
                            os.remove(temp_license_path)
                        except OSError:
                            pass  # 忽略删除错误

                    root.destroy()
                    sys.exit(0 if is_valid else 1)
            except Exception as e:
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("错误", f"管理员权限授权处理出错: {str(e)}")
                root.destroy()
                sys.exit(1)

        # 正常启动
        main()
    except KeyboardInterrupt:
        print("\n程序启动被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        sys.exit(1)