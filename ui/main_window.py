import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .terminology_editor import create_terminology_editor
from services.document_processor import DocumentProcessor
from services.pdf_processor import PDFProcessor
from services.document_factory import DocumentProcessorFactory
from services.translator import TranslationService
from services.ollama_translator import OllamaTranslator
from utils.ui_logger import setup_ui_logger
import threading
import os
import logging  # 添加导入

# Excel处理器支持
EXCEL_SUPPORT = True

logger = logging.getLogger(__name__)  # 添加logger定义

def create_ui(root, terminology):
    """创建主窗口界面"""
    root.title("多格式文档翻译助手")
    root.geometry("800x800")

    # 创建翻译服务实例
    translator = TranslationService()
    # 文档处理器将在选择文件后动态创建

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
        # 构建支持的文件类型列表
        filetypes = [
            ("Word文档", "*.docx"),
            ("PDF文档", "*.pdf"),
            ("Excel文档", "*.xlsx;*.xls")
        ]

        # 添加所有文件选项
        filetypes.append(("所有文件", "*.*"))

        filename = filedialog.askopenfilename(
            title="选择要翻译的文档",
            filetypes=filetypes
        )
        if filename:
            file_path_var.set(filename)

    file_btn = ttk.Button(file_frame, text="选择文件", command=select_file)
    file_btn.pack(side='right')

    # 添加翻译方向选择
    direction_frame = ttk.Frame(control_frame)
    direction_frame.pack(pady=5, fill='x')

    direction_label = ttk.Label(direction_frame, text="翻译方向:")
    direction_label.pack(side='left')

    direction_var = tk.StringVar(value="zh_to_en")

    zh_to_en_radio = ttk.Radiobutton(
        direction_frame,
        text="中文 → 外语",
        value="zh_to_en",
        variable=direction_var,
        command=lambda: update_language_options()
    )
    zh_to_en_radio.pack(side='left', padx=(10, 5))

    en_to_zh_radio = ttk.Radiobutton(
        direction_frame,
        text="外语 → 中文",
        value="en_to_zh",
        variable=direction_var,
        command=lambda: update_language_options()
    )
    en_to_zh_radio.pack(side='left', padx=5)

    # 添加语言选择下拉框
    lang_frame = ttk.Frame(control_frame)
    lang_frame.pack(pady=5, fill='x')

    lang_label = ttk.Label(lang_frame, text="选择目标语言:")
    lang_label.pack(side='left')

    lang_var = tk.StringVar()
    lang_combo = ttk.Combobox(lang_frame, textvariable=lang_var)
    lang_combo['values'] = list(terminology.keys())
    lang_combo.set('英语')
    lang_combo.pack(side='left', padx=(10, 0))

    # 语言名称到语言代码的映射
    language_code_map = {
        "英语": "en",
        "日语": "ja",
        "韩语": "ko",
        "法语": "fr",
        "德语": "de",
        "西班牙语": "es",
        "意大利语": "it",
        "俄语": "ru",
        "葡萄牙语": "pt",
        "荷兰语": "nl",
        "阿拉伯语": "ar",
        "泰语": "th",
        "越南语": "vi",
        "中文": "zh"
    }

    # 添加源语言和目标语言代码变量
    source_lang_var = tk.StringVar(value="zh")
    target_lang_var = tk.StringVar(value="en")

    def update_language_options():
        """根据翻译方向更新语言选项"""
        direction = direction_var.get()
        if direction == "zh_to_en":
            # 中文 → 外语
            source_lang_var.set("zh")
            # 根据当前选择的语言更新目标语言代码
            selected_lang = lang_var.get()
            if selected_lang in language_code_map:
                target_lang_var.set(language_code_map[selected_lang])
            else:
                target_lang_var.set("en")  # 默认英语
            lang_label.config(text="选择目标语言:")
        else:
            # 外语 → 中文
            target_lang_var.set("zh")
            # 根据当前选择的语言更新源语言代码
            selected_lang = lang_var.get()
            if selected_lang in language_code_map:
                source_lang_var.set(language_code_map[selected_lang])
            else:
                source_lang_var.set("en")  # 默认英语
            lang_label.config(text="选择源语言:")

    # 当语言选择改变时更新语言代码
    def on_language_change(_):  # 使用下划线表示未使用的参数
        selected_lang = lang_var.get()
        if selected_lang in language_code_map:
            if direction_var.get() == "zh_to_en":
                # 中文 → 外语
                target_lang_var.set(language_code_map[selected_lang])
            else:
                # 外语 → 中文
                source_lang_var.set(language_code_map[selected_lang])

    # 绑定语言选择事件
    lang_combo.bind('<<ComboboxSelected>>', on_language_change)

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

    # 添加术语预处理开关
    preprocess_frame = ttk.Frame(control_frame)
    preprocess_frame.pack(pady=5, fill='x')

    preprocess_terms_var = tk.BooleanVar(value=True)  # 默认启用
    preprocess_check = ttk.Checkbutton(
        preprocess_frame,
        text="使用术语预处理",
        variable=preprocess_terms_var
    )
    preprocess_check.pack(side='left')

    # 添加提示标签
    preprocess_hint = ttk.Label(
        preprocess_frame,
        text="先检测文本中的术语并替换，再进行翻译",
        foreground="gray"
    )
    preprocess_hint.pack(side='left', padx=5)

    # 添加PDF导出开关
    pdf_frame = ttk.Frame(control_frame)
    pdf_frame.pack(pady=5, fill='x')

    export_pdf_var = tk.BooleanVar(value=False)  # 默认关闭
    export_pdf_check = ttk.Checkbutton(
        pdf_frame,
        text="导出PDF文件",
        variable=export_pdf_var
    )
    export_pdf_check.pack(side='left')

    # 添加提示标签
    pdf_hint = ttk.Label(
        pdf_frame,
        text="同时将翻译结果导出为PDF格式（Word文档需要安装Microsoft Word）",
        foreground="gray"
    )
    pdf_hint.pack(side='left', padx=5)

    # 添加双语对照/仅翻译选项
    output_format_frame = ttk.Frame(control_frame)
    output_format_frame.pack(pady=5, fill='x')

    output_format_label = ttk.Label(output_format_frame, text="输出格式:")
    output_format_label.pack(side='left')

    output_format_var = tk.StringVar(value="bilingual")  # 默认双语对照

    bilingual_radio = ttk.Radiobutton(
        output_format_frame,
        text="双语对照",
        value="bilingual",
        variable=output_format_var
    )
    bilingual_radio.pack(side='left', padx=(10, 5))

    translation_only_radio = ttk.Radiobutton(
        output_format_frame,
        text="仅翻译结果",
        value="translation_only",
        variable=output_format_var
    )
    translation_only_radio.pack(side='left', padx=5)

    # 添加提示标签
    output_format_hint = ttk.Label(
        output_format_frame,
        text="选择输出格式，双语对照会同时显示原文和译文，仅翻译结果只保留译文",
        foreground="gray"
    )
    output_format_hint.pack(side='left', padx=5)

    # 添加翻译器选择区域
    translator_frame = ttk.LabelFrame(control_frame, text="翻译器设置")
    translator_frame.pack(pady=10, fill='x')

    # 添加翻译器类型选择
    translator_type_frame = ttk.Frame(translator_frame)
    translator_type_frame.pack(pady=5, fill='x')

    ttk.Label(translator_type_frame, text="翻译器:").pack(side='left')

    # 获取当前翻译器类型
    current_type = translator.get_current_translator_type()
    translator_type_var = tk.StringVar(value=current_type)

    # 创建单选按钮组
    translator_types = [
        ("智谱AI", "zhipuai"),
        ("Ollama", "ollama"),
        ("硅基流动", "siliconflow")
    ]

    for text, value in translator_types:
        ttk.Radiobutton(
            translator_type_frame,
            text=text,
            value=value,
            variable=translator_type_var,
            command=lambda: on_translator_type_change()
        ).pack(side='left', padx=5)

    # 添加模型选择
    model_frame = ttk.Frame(translator_frame)
    model_frame.pack(pady=5, fill='x')

    ttk.Label(model_frame, text="模型:").pack(side='left')

    model_var = tk.StringVar()
    model_combo = ttk.Combobox(model_frame, textvariable=model_var, state='readonly')
    model_combo.pack(side='left', padx=(5, 0), fill='x', expand=True)

    def on_translator_type_change():
        """当翻译器类型改变时调用"""
        translator_type = translator_type_var.get()
        if translator.set_translator_type(translator_type):
            update_model_list()
            check_translator_status()  # 更新状态

    def update_model_list():
        """更新模型列表"""
        try:
            # 获取当前翻译器类型
            current_type = translator_type_var.get()

            # 获取当前翻译器类型的可用模型
            available_models = translator.get_available_models(current_type)

            if available_models:
                logger.info(f"获取到的模型列表: {available_models}")
                model_combo['values'] = available_models

                # 获取当前配置中的模型
                current_config = None
                if current_type == "zhipuai":
                    current_config = translator.config.get("zhipuai_translator", {})
                elif current_type == "ollama":
                    current_config = translator.config.get("fallback_translator", {})
                elif current_type == "siliconflow":
                    current_config = translator.config.get("siliconflow_translator", {})

                if current_config and "model" in current_config:
                    current_model = current_config.get("model")
                    if current_model in available_models:
                        model_combo.set(current_model)
                    else:
                        model_combo.set(available_models[0])
                else:
                    model_combo.set(available_models[0])

                model_combo.configure(state='readonly')
            else:
                model_combo['values'] = ["无可用模型"]
                model_combo.set("无可用模型")
                model_combo.configure(state='disabled')

        except Exception as e:
            logger.error(f"更新模型列表失败: {str(e)}")
            # 确保下拉框至少有一个空列表
            model_combo['values'] = ["无可用模型"]
            model_combo.set("无可用模型")
            model_combo.configure(state='disabled')

    # 初始化模型列表
    update_model_list()

    def on_model_change(_):  # 使用下划线表示未使用的参数
        """当模型选择变化时调用"""
        current_type = translator_type_var.get()
        selected_model = model_var.get()

        # 更新配置
        if current_type == "zhipuai":
            if "zhipuai_translator" not in translator.config:
                translator.config["zhipuai_translator"] = {}
            translator.config["zhipuai_translator"]["model"] = selected_model
        elif current_type == "ollama":
            if "fallback_translator" not in translator.config:
                translator.config["fallback_translator"] = {}
            translator.config["fallback_translator"]["model"] = selected_model
        elif current_type == "siliconflow":
            if "siliconflow_translator" not in translator.config:
                translator.config["siliconflow_translator"] = {}
            translator.config["siliconflow_translator"]["model"] = selected_model

        # 保存配置
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(translator.config, f, ensure_ascii=False, indent=4)

    model_combo.bind('<<ComboboxSelected>>', on_model_change)

    # 添加翻译状态指示
    translator_status_frame = ttk.Frame(translator_frame)
    translator_status_frame.pack(pady=5, fill='x')

    zhipuai_status_var = tk.StringVar(value="智谱AI状态: 未知")
    ollama_status_var = tk.StringVar(value="Ollama状态: 未知")
    siliconflow_status_var = tk.StringVar(value="硅基流动状态: 未知")

    zhipuai_status_label = ttk.Label(translator_status_frame, textvariable=zhipuai_status_var)
    zhipuai_status_label.pack(side='left', padx=(0, 10))

    ollama_status_label = ttk.Label(translator_status_frame, textvariable=ollama_status_var)
    ollama_status_label.pack(side='left', padx=(0, 10))

    siliconflow_status_label = ttk.Label(translator_status_frame, textvariable=siliconflow_status_var)
    siliconflow_status_label.pack(side='left')

    # 添加模型刷新按钮
    def refresh_models():
        """刷新模型列表"""
        current_type = translator_type_var.get()
        models = translator.refresh_models(current_type)
        if models:
            model_combo['values'] = models
            # 如果当前选中的模型不在刷新后的列表中，选择第一个
            if model_var.get() not in models:
                model_var.set(models[0])
            model_combo.configure(state='readonly')
        else:
            model_combo['values'] = ["无可用模型"]
            model_var.set("无可用模型")
            model_combo.configure(state='disabled')

    refresh_btn = ttk.Button(model_frame, text="刷新模型", command=refresh_models)
    refresh_btn.pack(side='left', padx=5)

    # 添加翻译器状态检查
    def check_translator_status():
        # 检查智谱AI状态
        try:
            zhipuai_available = translator._check_zhipuai_available()
            if zhipuai_available:
                zhipuai_status_var.set("智谱AI状态: 可用")
            else:
                zhipuai_status_var.set("智谱AI状态: 不可用")
        except Exception as e:
            zhipuai_available = False
            zhipuai_status_var.set("智谱AI状态: 检查失败")

        # 检查Ollama状态
        try:
            ollama_available = translator.check_ollama_service()
            if ollama_available:
                ollama_status_var.set("Ollama状态: 可用")
            else:
                ollama_status_var.set("Ollama状态: 不可用")
        except Exception as e:
            ollama_available = False
            ollama_status_var.set("Ollama状态: 检查失败")

        # 检查硅基流动状态（暂时跳过以避免网络超时）
        siliconflow_available = False
        siliconflow_status_var.set("硅基流动状态: 跳过检查")

        # 更新状态显示
        if zhipuai_available or ollama_available or siliconflow_available:
            status_var.set("至少有一个翻译服务可用")
            translate_btn.configure(state='normal')
        else:
            status_var.set("所有翻译服务不可用，请检查配置和网络")
            translate_btn.configure(state='disabled')

        # 如果当前选择的翻译器不可用，提示用户
        current_type = translator_type_var.get()
        current_available = False

        if current_type == "zhipuai" and zhipuai_available:
            current_available = True
        elif current_type == "ollama" and ollama_available:
            current_available = True
        elif current_type == "siliconflow" and siliconflow_available:
            current_available = True

        if not current_available:
            # 找一个可用的翻译器自动切换
            if zhipuai_available:
                translator_type_var.set("zhipuai")
                translator.set_translator_type("zhipuai")
            elif ollama_available:
                translator_type_var.set("ollama")
                translator.set_translator_type("ollama")
            elif siliconflow_available:
                translator_type_var.set("siliconflow")
                translator.set_translator_type("siliconflow")

            # 更新模型列表
            update_model_list()

        return zhipuai_available or ollama_available or siliconflow_available

    check_btn = ttk.Button(translator_frame, text="检查翻译服务状态", command=check_translator_status)
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
                # 根据文件类型创建合适的文档处理器
                try:
                    doc_processor = DocumentProcessorFactory.create_processor(file_path, translator)
                except ValueError as e:
                    messagebox.showerror("错误", str(e))
                    return

                # 将术语库开关状态传递给文档处理器
                doc_processor.use_terminology = use_terminology_var.get()
                # 将术语预处理开关状态传递给文档处理器
                doc_processor.preprocess_terms = preprocess_terms_var.get()
                # 将PDF导出开关状态传递给文档处理器
                doc_processor.export_pdf = export_pdf_var.get()
                # 将输出格式选项传递给文档处理器
                doc_processor.output_format = output_format_var.get()

                # 记录日志
                logger.info(f"开始翻译文档: {file_path}")
                logger.info(f"翻译方向: {source_lang_var.get()} → {target_lang_var.get()}")
                logger.info(f"语言选择: {selected_lang}")
                logger.info(f"使用术语库: {doc_processor.use_terminology}")
                logger.info(f"使用术语预处理: {doc_processor.preprocess_terms}")
                logger.info(f"导出PDF: {doc_processor.export_pdf}")
                logger.info(f"输出格式: {doc_processor.output_format}")

                # 获取当前的源语言和目标语言代码
                current_source_lang = source_lang_var.get()
                current_target_lang = target_lang_var.get()

                # 处理文档
                output_path = doc_processor.process_document(
                    file_path,
                    selected_lang,
                    terminology,
                    source_lang=current_source_lang,
                    target_lang=current_target_lang
                )

                def show_success():
                    try:
                        if root.winfo_exists():
                            status_var.set("翻译完成！")

                            # 获取文件类型
                            _, ext = os.path.splitext(output_path)
                            ext = ext.lower()

                            # 根据文件类型显示不同的成功消息
                            if ext == '.docx':
                                file_type = "Word文档"
                            elif ext == '.pdf':
                                file_type = "PDF文档"
                            elif ext in ['.xlsx', '.xls']:
                                file_type = "Excel文档"
                            else:
                                file_type = "文档"

                            success_message = f"{file_type}已翻译完成！\n保存位置：{output_path}"

                            # 如果导出了PDF，显示PDF文件路径
                            if doc_processor.export_pdf:
                                # 获取PDF文件路径
                                pdf_path = os.path.splitext(output_path)[0] + ".pdf"
                                if os.path.exists(pdf_path):
                                    success_message += f"\n\nPDF文件已保存到：\n{pdf_path}"

                            messagebox.showinfo("完成", success_message)
                    except Exception as e:
                        logger.error(f"显示成功信息时出错: {str(e)}")

                # 使用after方法在主线程中执行，增加延迟
                if root.winfo_exists():
                    root.after(100, show_success)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"翻译出错: {error_msg}")
                def show_error():
                    try:
                        if root.winfo_exists():
                            status_var.set(f"翻译出错：{error_msg}")
                            messagebox.showerror("错误", error_msg)
                    except Exception as e:
                        logger.error(f"显示错误信息时出错: {str(e)}")

                # 使用after方法在主线程中执行，增加延迟
                if root.winfo_exists():
                    root.after(100, show_error)
            finally:
                # 直接在主线程中启用按钮，避免使用回调函数
                def enable_button():
                    try:
                        # 使用更安全的方式设置按钮状态
                        if translate_btn.winfo_exists():
                            translate_btn['state'] = 'normal'
                    except Exception as e:
                        logger.error(f"启用按钮时出错: {str(e)}")

                # 使用after方法在主线程中执行
                if root.winfo_exists():  # 确保根窗口仍然存在
                    root.after(100, enable_button)  # 增加延迟，避免可能的竞态条件

        threading.Thread(target=translation_task, daemon=True).start()

    translate_btn = ttk.Button(root, text="开始翻译", command=start_translation)
    translate_btn.pack(pady=10)

    # 初始检查翻译服务状态
    translators_available = check_translator_status()
    if not translators_available:
        translate_btn.configure(state='disabled')

    # 返回状态变量，供main.py使用
    return status_var