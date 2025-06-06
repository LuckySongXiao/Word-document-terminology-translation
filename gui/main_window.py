import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ui.terminology_editor import create_terminology_editor
from services.document_processor import DocumentProcessor
from services.translator import TranslationService
from services.ollama_translator import OllamaTranslator
from utils.ui_logger import setup_ui_logger
import threading
import os
import logging  # 添加导入

logger = logging.getLogger(__name__)  # 添加logger定义

def create_ui(terminology, root=None):
    """创建主窗口界面"""
    if root is None:
        root = tk.Tk()
    root.title("Word文档翻译助手")
    root.geometry("800x800")

    # 创建服务实例
    translator = TranslationService()
    doc_processor = DocumentProcessor(translator)

    # 创建上部控制区域
    control_frame = ttk.Frame(root)
    control_frame.pack(pady=10, padx=20, fill='x')

    # 设置UI日志
    log_text, message_queue = setup_ui_logger(root)

    # 状态显示 - 移到前面来
    status_var = tk.StringVar()
    status_label = ttk.Label(root, textvariable=status_var)
    status_label.pack(pady=5)

    # 添加文件选择功能
    file_frame = ttk.Frame(control_frame)
    file_frame.pack(fill='x')

    file_path_var = tk.StringVar()
    file_entry = ttk.Entry(file_frame, textvariable=file_path_var)
    file_entry.pack(side='left', expand=True, fill='x', padx=(0, 10))

    def select_file():
        filename = filedialog.askopenfilename(
            title="选择要翻译的文档",
            filetypes=[("Word文档", "*.docx"), ("所有文件", "*.*")]
        )
        if filename:
            file_path_var.set(filename)

    file_btn = ttk.Button(file_frame, text="选择文件", command=select_file)
    file_btn.pack(side='right')

    # 添加语言选择下拉框
    lang_frame = ttk.Frame(control_frame)
    lang_frame.pack(pady=10, fill='x')

    lang_label = ttk.Label(lang_frame, text="选择目标语言:")
    lang_label.pack(side='left')

    lang_var = tk.StringVar()
    lang_combo = ttk.Combobox(lang_frame, textvariable=lang_var)
    lang_combo['values'] = list(terminology.keys())
    lang_combo.set('英语')
    lang_combo.pack(side='left', padx=(10, 0))

    # 添加术语库编辑按钮
    def open_terminology_editor():
        create_terminology_editor(root, terminology)

    edit_btn = ttk.Button(control_frame, text="编辑术语库", command=open_terminology_editor)
    edit_btn.pack(pady=10)

    # 添加术语库开关
    terminology_frame = ttk.Frame(control_frame)
    terminology_frame.pack(pady=5, fill='x')

    use_terminology_var = tk.BooleanVar(value=True)  # 默认开启
    use_terminology_check = ttk.Checkbutton(
        terminology_frame,
        text="使用术语库进行翻译",
        variable=use_terminology_var
    )
    use_terminology_check.pack(side='left')

    # 添加提示标签
    terminology_hint = ttk.Label(
        terminology_frame,
        text="关闭后将使用更自然的翻译风格",
        foreground="gray"
    )
    terminology_hint.pack(side='left', padx=5)

    # 添加Ollama控制区域
    ollama_frame = ttk.LabelFrame(control_frame, text="Ollama设置")
    ollama_frame.pack(pady=10, fill='x')

    # 添加模型选择
    model_frame = ttk.Frame(ollama_frame)
    model_frame.pack(pady=5, fill='x')

    ttk.Label(model_frame, text="模型:").pack(side='left')

    model_var = tk.StringVar()
    model_combo = ttk.Combobox(model_frame, textvariable=model_var, state='readonly')
    model_combo.pack(side='left', padx=(5, 0), fill='x', expand=True)

    def update_model_list():
        """更新模型列表"""
        try:
            # 从配置中获取当前API URL和模型列表
            fallback_config = translator.config.get('fallback_translator', {})
            api_url = fallback_config.get('api_url', '')
            current_model = fallback_config.get('model', '')

            if api_url:
                try:
                    # 创建临时translator来获取最新的模型列表
                    temp_translator = OllamaTranslator("", api_url)
                    available_models = temp_translator.get_available_models()

                    if available_models:
                        logger.info(f"从API获取到的模型列表: {available_models}")
                        model_combo['values'] = available_models
                        if current_model in available_models:
                            model_combo.set(current_model)
                        else:
                            model_combo.set(available_models[0])
                        return
                except Exception as e:
                    logger.error(f"从API获取模型列表失败: {str(e)}")

            # 如果无法从API获取，使用配置文件中的模型列表
            available_models = fallback_config.get('available_models', [])
            if available_models:
                logger.info(f"使用配置文件中的模型列表: {available_models}")
                model_combo['values'] = available_models
                if current_model in available_models:
                    model_combo.set(current_model)
                elif available_models:
                    model_combo.set(available_models[0])

        except Exception as e:
            logger.error(f"更新模型列表失败: {str(e)}")
            # 确保下拉框至少有一个空列表
            model_combo['values'] = []

    # 初始化模型列表
    update_model_list()

    def on_model_change(event):
        translator.set_ollama_model(model_var.get())

    model_combo.bind('<<ComboboxSelected>>', on_model_change)

    # 添加使用Ollama的开关
    use_ollama_var = tk.BooleanVar(value=translator.use_fallback)
    use_ollama_check = ttk.Checkbutton(
        ollama_frame,
        text="优先使用Ollama翻译",
        variable=use_ollama_var,
        command=lambda: translator.set_use_fallback(use_ollama_var.get())
    )
    use_ollama_check.pack(pady=5)

    # 添加翻译状态指示
    translator_status_frame = ttk.Frame(ollama_frame)
    translator_status_frame.pack(pady=5, fill='x')

    zhipuai_status_var = tk.StringVar(value="智谱AI状态: 未知")
    ollama_status_var = tk.StringVar(value="Ollama状态: 未知")

    zhipuai_status_label = ttk.Label(translator_status_frame, textvariable=zhipuai_status_var)
    zhipuai_status_label.pack(side='left', padx=(0, 10))

    ollama_status_label = ttk.Label(translator_status_frame, textvariable=ollama_status_var)
    ollama_status_label.pack(side='left')

    # 添加Ollama状态检查
    def check_translator_status():
        # 检查智谱AI状态
        zhipuai_available = translator._check_zhipuai_available()
        if zhipuai_available:
            zhipuai_status_var.set("智谱AI状态: 可用")
        else:
            zhipuai_status_var.set("智谱AI状态: 不可用")

        # 检查Ollama状态
        ollama_available = False
        try:
            # 使用轻量级检查方法
            ollama_available = translator.check_ollama_service()
            ollama_status_var.set("Ollama状态: 可用")
            # 只要Ollama可用，就更新模型列表并启用模型选择
            update_model_list()  # 添加这行来更新模型列表
            model_combo.configure(state='readonly')
        except Exception as e:
            ollama_status_var.set("Ollama状态: 不可用")
            logger.error(f"Ollama检查失败: {str(e)}")
            model_combo.configure(state='disabled')

        # 更新状态显示，但不强制用户选择
        if ollama_available and zhipuai_available:
            status_var.set("所有翻译服务正常")
            use_ollama_check.configure(state='normal')
            translate_btn.configure(state='normal')
        elif ollama_available and not zhipuai_available:
            status_var.set("智谱AI不可用，但Ollama可用")
            use_ollama_check.configure(state='normal')  # 仍然允许选择
            translate_btn.configure(state='normal')
        elif not ollama_available and zhipuai_available:
            status_var.set("Ollama不可用，但智谱AI可用")
            use_ollama_check.configure(state='normal')  # 仍然允许选择
            translate_btn.configure(state='normal')
        else:
            # 两个翻译器都不可用
            status_var.set("所有翻译服务不可用，请检查网络和Ollama服务")
            use_ollama_check.configure(state='disabled')
            translate_btn.configure(state='disabled')

        return ollama_available or zhipuai_available

    check_btn = ttk.Button(ollama_frame, text="检查翻译服务状态", command=check_translator_status)
    check_btn.pack(pady=5)

    # 添加开始翻译按钮
    def start_translation():
        file_path = file_path_var.get()
        if not file_path:
            messagebox.showwarning("警告", "请先选择要翻译的文件！")
            return

        selected_lang = lang_var.get()
        status_var.set("正在翻译中...")
        translate_btn.configure(state='disabled')  # 禁用按钮

        def translation_task():
            try:
                # 将术语库开关状态传递给文档处理器
                doc_processor.use_terminology = use_terminology_var.get()
                output_path = doc_processor.process_document(file_path, selected_lang, terminology)

                def show_success():
                    status_var.set("翻译完成！")
                    messagebox.showinfo("完成", f"文档已翻译完成！\n保存位置：{output_path}")
                root.after(0, show_success)
            except Exception as e:
                error_msg = str(e)
                def show_error():
                    status_var.set(f"翻译出错：{error_msg}")
                    messagebox.showerror("错误", error_msg)
                root.after(0, show_error)
            finally:
                def enable_button():
                    translate_btn.configure(state='normal')
                root.after(0, enable_button)

        threading.Thread(target=translation_task, daemon=True).start()

    translate_btn = ttk.Button(root, text="开始翻译", command=start_translation)
    translate_btn.pack(pady=10)

    # 初始检查翻译服务状态
    translators_available = check_translator_status()
    if not translators_available:
        translate_btn.configure(state='disabled')

    root.mainloop()