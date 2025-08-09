import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .terminology_editor import create_terminology_editor
from services.document_processor import DocumentProcessor
from services.pdf_processor import PDFProcessor
from services.document_factory import DocumentProcessorFactory
from services.translator import TranslationService
from services.ollama_translator import OllamaTranslator
from utils.safe_ui_logger import setup_safe_ui_logger_horizontal
import threading
import os
import time
import logging  # 添加导入

# Excel处理器支持
EXCEL_SUPPORT = True

logger = logging.getLogger(__name__)  # 添加logger定义

def create_ui(root, terminology, translator=None):
    """
    创建主窗口界面

    Args:
        root: 主窗口
        terminology: 术语表
        translator: 翻译服务实例（如果为None则会创建默认实例）
    """
    print("DEBUG: create_ui函数开始执行")
    root.title("多格式文档翻译助手")
    root.geometry("1200x800")  # 增加宽度以适应横向布局

    # 确保窗口能够正确显示
    root.state('normal')  # 确保窗口状态正常
    root.deiconify()  # 确保窗口不是最小化状态
    root.lift()  # 将窗口提升到前台
    root.focus_force()  # 强制获取焦点
    root.update()  # 强制更新窗口
    print("DEBUG: 窗口标题和大小设置完成")

    # 如果没有传入翻译服务实例，则创建默认实例（兼容旧版本）
    print("DEBUG: 检查翻译服务实例")
    if translator is None:
        from services.translator import TranslationService
        translator = TranslationService()
    print("DEBUG: 翻译服务实例准备完成")
    # 文档处理器将在选择文件后动态创建

    # 创建主容器，使用横向布局
    main_container = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 左侧控制面板
    left_panel = ttk.Frame(main_container)
    main_container.add(left_panel, weight=1)

    # 右侧日志面板
    right_panel = ttk.Frame(main_container)
    main_container.add(right_panel, weight=2)

    # 在左侧面板创建滚动区域
    canvas = tk.Canvas(left_panel, highlightthickness=0)
    scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # 在右侧面板设置安全的UI日志
    log_text, message_queue, ui_logger = setup_safe_ui_logger_horizontal(right_panel)

    # 创建多层卡片式布局的控制面板
    def create_collapsible_card(parent, title, bg_color="#f0f0f0", expanded=True):
        """创建可折叠的卡片式容器"""
        # 主卡片容器
        card_frame = tk.Frame(parent, bg=bg_color, relief="raised", bd=2)
        card_frame.pack(pady=6, padx=8, fill='x')

        # 标题栏（可点击折叠/展开）
        title_frame = tk.Frame(card_frame, bg=bg_color, cursor="hand2")
        title_frame.pack(fill='x', padx=5, pady=5)

        # 折叠/展开状态
        expanded_var = tk.BooleanVar(value=expanded)

        # 折叠图标和标题
        icon_label = tk.Label(title_frame, text="▼" if expanded else "▶",
                             font=("TkDefaultFont", 8), bg=bg_color, fg="#666666")
        icon_label.pack(side='left', padx=(5, 10))

        title_label = tk.Label(title_frame, text=title, font=("TkDefaultFont", 10, "bold"),
                              bg=bg_color, fg="#333333")
        title_label.pack(side='left')

        # 内容区域
        content_frame = tk.Frame(card_frame, bg="white", relief="flat")
        if expanded:
            content_frame.pack(fill='x', padx=10, pady=(0, 10))

        def toggle_card():
            """切换卡片展开/折叠状态"""
            if expanded_var.get():
                # 折叠
                content_frame.pack_forget()
                icon_label.config(text="▶")
                expanded_var.set(False)
            else:
                # 展开
                content_frame.pack(fill='x', padx=10, pady=(0, 10))
                icon_label.config(text="▼")
                expanded_var.set(True)

        # 绑定点击事件
        title_frame.bind("<Button-1>", lambda e: toggle_card())
        icon_label.bind("<Button-1>", lambda e: toggle_card())
        title_label.bind("<Button-1>", lambda e: toggle_card())

        return content_frame, expanded_var

    def create_nested_card(parent, title, bg_color="#f8f9fa"):
        """创建嵌套子卡片"""
        nested_frame = ttk.Frame(parent)
        nested_frame.pack(pady=4, padx=5, fill='x')

        # 子标题
        if title:
            title_label = ttk.Label(nested_frame, text=title, font=("TkDefaultFont", 9, "bold"))
            title_label.pack(anchor='w', padx=8, pady=(5, 2))

        # 子内容区域
        sub_content = ttk.Frame(nested_frame)
        sub_content.pack(fill='x', padx=8, pady=(0, 8))

        return sub_content

    # 1. 状态信息卡片
    status_card, status_expanded = create_collapsible_card(scrollable_frame, "📊 系统状态", "#e3f2fd", True)

    status_var = tk.StringVar(value="🟢 系统就绪")
    status_label = ttk.Label(status_card, textvariable=status_var, font=("TkDefaultFont", 9))
    status_label.pack(pady=5)

    # 进度显示子卡片
    progress_sub_card = create_nested_card(status_card, "📈 翻译进度", "#f0f8ff")

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_sub_card, variable=progress_var, maximum=100)
    progress_bar.pack(pady=5, padx=5, fill='x')

    progress_text_var = tk.StringVar(value="")
    progress_label = ttk.Label(progress_sub_card, textvariable=progress_text_var, foreground="blue", font=("TkDefaultFont", 8))
    progress_label.pack(pady=2)

    # 2. 文件选择卡片
    file_card, file_expanded = create_collapsible_card(scrollable_frame, "📁 文档管理", "#f3e5f5", True)

    file_path_var = tk.StringVar()

    # 文件信息子卡片
    file_info_card = create_nested_card(file_card, "📄 当前文档", "#faf0e6")

    file_entry = ttk.Entry(file_info_card, textvariable=file_path_var, state='readonly')
    file_entry.pack(fill='x', pady=2)

    # 文件操作子卡片
    file_ops_card = create_nested_card(file_card, "🛠️ 文档操作", "#f0fff0")

    file_btn_frame = ttk.Frame(file_ops_card)
    file_btn_frame.pack(fill='x', pady=2)

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
            # 更新状态
            import os
            file_size = os.path.getsize(filename) / 1024  # KB
            status_var.set(f"📄 已选择文档 ({file_size:.1f} KB)")

    file_btn = ttk.Button(file_btn_frame, text="🔍 选择文件", command=select_file)
    file_btn.pack(side='left', padx=(0, 5))

    # 添加清除按钮
    def clear_file():
        file_path_var.set("")
        status_var.set("🟢 系统就绪")

    clear_btn = ttk.Button(file_btn_frame, text="🗑️ 清除", command=clear_file)
    clear_btn.pack(side='left')

    # 3. 翻译设置卡片
    translation_card, trans_expanded = create_collapsible_card(scrollable_frame, "🌐 翻译配置", "#e8f5e8", True)

    # 翻译方向子卡片
    direction_sub_card = create_nested_card(translation_card, "🔄 翻译方向", "#f0fff0")

    direction_var = tk.StringVar(value="zh_to_en")

    zh_to_en_radio = ttk.Radiobutton(
        direction_sub_card,
        text="🇨🇳 中文 → 外语",
        value="zh_to_en",
        variable=direction_var,
        command=lambda: update_language_options()
    )
    zh_to_en_radio.pack(anchor='w', pady=2)

    en_to_zh_radio = ttk.Radiobutton(
        direction_sub_card,
        text="🌍 外语 → 中文",
        value="en_to_zh",
        variable=direction_var,
        command=lambda: update_language_options()
    )
    en_to_zh_radio.pack(anchor='w', pady=2)

    # 语言选择子卡片
    lang_sub_card = create_nested_card(translation_card, "🗣️ 目标语言", "#fff8dc")

    lang_var = tk.StringVar()
    lang_combo = ttk.Combobox(lang_sub_card, textvariable=lang_var, state='readonly')
    lang_combo['values'] = list(terminology.keys())
    lang_combo.set('英语')
    lang_combo.pack(fill='x', pady=5)

    # 语言状态显示
    lang_status_label = ttk.Label(lang_sub_card, text="✅ 支持术语库翻译", foreground="green", font=("TkDefaultFont", 8))
    lang_status_label.pack(anchor='w', pady=2)

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

    # 4. 术语库设置卡片
    terminology_card, term_expanded = create_collapsible_card(scrollable_frame, "📚 术语库管理", "#fff3e0", False)

    # 术语库编辑子卡片
    term_edit_card = create_nested_card(terminology_card, "📝 术语库编辑", "#faf0e6")

    def open_terminology_editor():
        create_terminology_editor(root, terminology)

    edit_btn = ttk.Button(term_edit_card, text="📝 打开术语库编辑器", command=open_terminology_editor)
    edit_btn.pack(fill='x', pady=5)

    # 术语库选项子卡片
    term_options_card = create_nested_card(terminology_card, "⚙️ 翻译选项", "#f0fff0")

    use_terminology_var = tk.BooleanVar(value=True)  # 默认开启
    use_terminology_check = ttk.Checkbutton(
        term_options_card,
        text="✅ 使用术语库进行翻译",
        variable=use_terminology_var
    )
    use_terminology_check.pack(anchor='w', pady=2)

    terminology_hint = ttk.Label(
        term_options_card,
        text="💡 关闭后将使用更自然的翻译风格",
        foreground="gray",
        font=("TkDefaultFont", 8)
    )
    terminology_hint.pack(anchor='w', padx=20, pady=1)

    preprocess_terms_var = tk.BooleanVar(value=True)  # 默认启用
    preprocess_check = ttk.Checkbutton(
        term_options_card,
        text="⚡ 使用术语预处理",
        variable=preprocess_terms_var
    )
    preprocess_check.pack(anchor='w', pady=2)

    preprocess_hint = ttk.Label(
        term_options_card,
        text="💡 先检测文本中的术语并替换，再进行翻译",
        foreground="gray",
        font=("TkDefaultFont", 8)
    )
    preprocess_hint.pack(anchor='w', padx=20, pady=1)

    # 5. 输出设置卡片
    output_card, output_expanded = create_collapsible_card(scrollable_frame, "📄 输出配置", "#f1f8e9", False)

    # PDF导出子卡片
    pdf_export_card = create_nested_card(output_card, "📑 PDF导出", "#fff8dc")

    export_pdf_var = tk.BooleanVar(value=False)  # 默认关闭
    export_pdf_check = ttk.Checkbutton(
        pdf_export_card,
        text="📑 同时导出PDF文件",
        variable=export_pdf_var
    )
    export_pdf_check.pack(anchor='w', pady=2)

    pdf_hint = ttk.Label(
        pdf_export_card,
        text="💡 将翻译结果同时保存为PDF格式",
        foreground="gray",
        font=("TkDefaultFont", 8)
    )
    pdf_hint.pack(anchor='w', padx=20, pady=1)

    # 输出格式子卡片
    format_card = create_nested_card(output_card, "📋 输出格式", "#f0fff0")

    output_format_var = tk.StringVar(value="bilingual")  # 默认双语对照

    bilingual_radio = ttk.Radiobutton(
        format_card,
        text="📋 双语对照显示",
        value="bilingual",
        variable=output_format_var
    )
    bilingual_radio.pack(anchor='w', pady=2)

    translation_only_radio = ttk.Radiobutton(
        format_card,
        text="📝 仅显示翻译结果",
        value="translation_only",
        variable=output_format_var
    )
    translation_only_radio.pack(anchor='w', pady=2)

    format_hint = ttk.Label(
        format_card,
        text="💡 双语对照便于对比，仅翻译结果更简洁",
        foreground="gray",
        font=("TkDefaultFont", 8)
    )
    format_hint.pack(anchor='w', padx=20, pady=1)

    # 6. 翻译器设置卡片 - 多层设计
    translator_card, trans_expanded = create_collapsible_card(scrollable_frame, "🤖 AI翻译引擎", "#e1f5fe", True)

    # 获取当前翻译器类型
    current_type = translator.get_current_translator_type()
    translator_type_var = tk.StringVar(value=current_type)

    # 翻译器选择子卡片
    translator_selector_card = create_nested_card(translator_card, "🎯 选择翻译器", "#f0f8ff")

    # 创建翻译器选择按钮组（水平布局）
    translator_types = [
        ("🧠 智谱AI", "zhipuai", "#e8f5e8"),
        ("🦙 Ollama", "ollama", "#fff8dc"),
        ("💎 硅基流动", "siliconflow", "#f0f8ff"),
        ("🌐 内网OPENAI", "intranet", "#ffe4e1")
    ]

    translator_buttons = {}
    translator_btn_frame = ttk.Frame(translator_selector_card)
    translator_btn_frame.pack(fill='x', pady=5)

    # 防抖动变量
    switch_lock = threading.Lock()
    current_switch_task = None

    def switch_translator(trans_type):
        """丝滑切换翻译器 - 优化版本，优先停止之前的引擎"""
        nonlocal current_switch_task

        # 防抖动：如果正在切换，忽略新的切换请求
        if not switch_lock.acquire(blocking=False):
            logger.info(f"切换请求被忽略，正在切换中: {trans_type}")
            return

        try:
            # 强制取消之前的切换任务
            if current_switch_task and current_switch_task.is_alive():
                logger.info("强制停止之前的切换任务")
                # 设置停止标志（如果任务支持的话）

            # 优先停止当前翻译器的活动连接
            current_type = translator_type_var.get()
            if current_type and current_type != trans_type:
                logger.info(f"优先停止当前翻译器: {current_type}")
                try:
                    # 快速停止当前翻译器的连接
                    if hasattr(translator, 'stop_current_operations'):
                        translator.stop_current_operations()
                except Exception as e:
                    logger.warning(f"停止当前翻译器操作失败: {str(e)}")

            # 立即更新UI状态，避免卡顿
            translator_type_var.set(trans_type)

            # 立即更新按钮样式
            for btn_type, btn in translator_buttons.items():
                if btn_type == trans_type:
                    btn.configure(state='pressed')
                else:
                    btn.configure(state='normal')

            # 立即显示切换状态
            status_var.set(f"🔄 正在切换到 {trans_type}...")
            test_status_var.set("🔄 切换中...")
            model_status_label.config(text="🔄 正在加载模型...", foreground="blue")

            # 禁用所有翻译器按钮，防止重复操作
            for btn in translator_buttons.values():
                btn.configure(state='disabled')

            # 禁用测试和刷新按钮
            test_btn.configure(state='disabled')
            refresh_btn.configure(state='disabled')

            # 异步执行耗时操作
            def async_switch():
                stop_requested = False
                try:
                    logger.info(f"开始异步切换到: {trans_type}")

                    # 第一步：快速设置翻译器类型（跳过网络检查）
                    def quick_update():
                        try:
                            # 快速设置翻译器类型，跳过网络检查以提高速度
                            if translator.set_translator_type(trans_type, skip_check=True):
                                status_var.set(f"✅ 已切换到 {trans_type}")
                                logger.info(f"快速切换完成: {trans_type}")
                            else:
                                status_var.set(f"⚠️ 切换失败: 配置错误")
                        except Exception as e:
                            logger.error(f"快速切换失败: {str(e)}")
                            status_var.set(f"⚠️ 切换失败: {str(e)[:30]}...")

                    # 立即执行快速更新
                    root.after(0, quick_update)

                    # 第二步：后台异步更新模型列表
                    if not stop_requested:
                        # 短暂延迟，让UI先响应
                        time.sleep(0.2)

                        # 异步更新翻译器显示和模型
                        update_translator_display_async(trans_type)

                        # 第三步：切换完成后进行通讯测试
                        time.sleep(0.3)
                        if not stop_requested:
                            def auto_test_after_switch():
                                try:
                                    logger.info(f"开始对 {trans_type} 进行切换后通讯测试")
                                    # 使用新的auto_test参数进行测试
                                    test_result = translator.set_translator_type(trans_type, skip_check=False, auto_test=True)

                                    def update_test_result():
                                        if test_result:
                                            status_var.set(f"🟢 {trans_type} 切换并测试成功")
                                            test_status_var.set("✅ 自动测试成功")
                                            test_status_label.config(foreground="green")
                                            # 翻译按钮状态将在按钮创建后通过其他机制更新
                                        else:
                                            status_var.set(f"🔴 {trans_type} 切换成功但通讯测试失败")
                                            test_status_var.set("❌ 自动测试失败")
                                            test_status_label.config(foreground="red")
                                            # 翻译按钮状态将在按钮创建后通过其他机制更新

                                    root.after(0, update_test_result)
                                except Exception as e:
                                    logger.error(f"自动测试失败: {str(e)}")
                                    def update_error():
                                        status_var.set(f"⚠️ {trans_type} 自动测试出错")
                                        test_status_var.set("⚠️ 测试出错")
                                        test_status_label.config(foreground="orange")
                                    root.after(0, update_error)

                            auto_test_after_switch()

                    logger.info(f"异步切换完成: {trans_type}")

                except Exception as e:
                    logger.error(f"异步切换失败: {str(e)}")
                    # 错误处理
                    def update_error():
                        status_var.set(f"⚠️ 切换失败: {str(e)[:30]}...")
                        test_status_var.set("❌ 切换失败")

                        # 重新启用按钮
                        for btn in translator_buttons.values():
                            btn.configure(state='normal')
                        test_btn.configure(state='normal')
                        refresh_btn.configure(state='normal')

                    root.after(0, update_error)
                finally:
                    # 确保按钮重新启用
                    def re_enable_buttons():
                        for btn in translator_buttons.values():
                            btn.configure(state='normal')
                        test_btn.configure(state='normal')
                        refresh_btn.configure(state='normal')

                    root.after(1000, re_enable_buttons)  # 1秒后重新启用按钮

                    # 释放锁
                    if switch_lock.locked():
                        switch_lock.release()

            # 启动异步线程
            current_switch_task = threading.Thread(target=async_switch, daemon=True)
            current_switch_task.start()

        except Exception as e:
            logger.error(f"切换翻译器失败: {str(e)}")
            if switch_lock.locked():
                switch_lock.release()
            status_var.set(f"⚠️ 切换失败: {str(e)[:30]}...")

    # 创建翻译器切换按钮
    for i, (text, value, color) in enumerate(translator_types):
        btn = ttk.Button(
            translator_btn_frame,
            text=text,
            command=lambda v=value: switch_translator(v),
            width=12
        )
        btn.grid(row=i//2, column=i%2, padx=2, pady=2, sticky="ew")
        translator_buttons[value] = btn

        # 设置初始选中状态
        if value == current_type:
            btn.configure(state='pressed')

    # 配置网格权重
    translator_btn_frame.grid_columnconfigure(0, weight=1)
    translator_btn_frame.grid_columnconfigure(1, weight=1)

    # 当前翻译器详情卡片 - 动态显示
    current_translator_card = create_nested_card(translator_card, "", "#ffffff")

    # 翻译器详情容器
    translator_details_frame = ttk.Frame(current_translator_card)
    translator_details_frame.pack(fill='x', pady=5)

    # 模型选择区域
    model_frame = ttk.Frame(translator_details_frame)
    model_frame.pack(fill='x', pady=5)

    model_label_frame = ttk.Frame(model_frame)
    model_label_frame.pack(fill='x')

    model_title_label = ttk.Label(model_label_frame, text="🎯 模型选择", font=("TkDefaultFont", 9, "bold"))
    model_title_label.pack(side='left')

    # 刷新按钮
    def refresh_models():
        """刷新当前翻译器的模型列表 - 异步版本"""
        current_type = translator_type_var.get()

        # 立即显示刷新状态
        model_status_label.config(text="🔄 正在刷新模型列表...", foreground="blue")
        refresh_btn.configure(state='disabled', text="🔄 刷新中...")

        def async_refresh():
            try:
                models = translator.refresh_models(current_type)

                def update_ui():
                    try:
                        if models:
                            model_combo['values'] = models
                            if model_var.get() not in models:
                                model_var.set(models[0])
                            model_combo.configure(state='readonly')
                            model_status_label.config(text=f"✅ 找到 {len(models)} 个模型", foreground="green")
                        else:
                            model_combo['values'] = ["无可用模型"]
                            model_var.set("无可用模型")
                            model_combo.configure(state='disabled')
                            model_status_label.config(text="❌ 未找到可用模型", foreground="red")
                    except Exception as e:
                        model_status_label.config(text=f"⚠️ UI更新失败: {str(e)[:30]}...", foreground="orange")
                    finally:
                        refresh_btn.configure(state='normal', text="🔄 刷新")

                root.after(0, update_ui)

            except Exception as e:
                def update_error():
                    model_status_label.config(text=f"⚠️ 获取模型失败: {str(e)[:30]}...", foreground="orange")
                    refresh_btn.configure(state='normal', text="🔄 刷新")

                root.after(0, update_error)

        threading.Thread(target=async_refresh, daemon=True).start()

    refresh_btn = ttk.Button(model_label_frame, text="🔄 刷新", command=refresh_models, width=8)
    refresh_btn.pack(side='right')

    model_var = tk.StringVar()
    model_combo = ttk.Combobox(model_frame, textvariable=model_var, state='readonly')
    model_combo.pack(fill='x', pady=3)

    # 模型状态显示
    model_status_label = ttk.Label(model_frame, text="🔍 请选择模型", font=("TkDefaultFont", 8))
    model_status_label.pack(anchor='w', pady=2)

    # 测试区域
    test_frame = ttk.Frame(translator_details_frame)
    test_frame.pack(fill='x', pady=10)

    test_title_label = ttk.Label(test_frame, text="🧪 连接测试", font=("TkDefaultFont", 9, "bold"))
    test_title_label.pack(anchor='w', pady=(0, 5))

    # 测试按钮和状态
    test_btn_frame = ttk.Frame(test_frame)
    test_btn_frame.pack(fill='x')

    test_status_var = tk.StringVar(value="🔍 未测试")
    test_status_label = ttk.Label(test_btn_frame, textvariable=test_status_var, font=("TkDefaultFont", 8))
    test_status_label.pack(side='left')

    def test_current_translator():
        """测试当前选择的翻译器和模型"""
        current_type = translator_type_var.get()
        current_model = model_var.get()

        if not current_model or current_model == "无可用模型":
            test_status_var.set("⚠️ 请先选择模型")
            return

        test_status_var.set("🔄 测试中...")
        test_btn.configure(state='disabled')

        def run_test():
            try:
                # 测试连接
                if current_type == "zhipuai":
                    result = translator._check_zhipuai_available()
                elif current_type == "ollama":
                    result = translator.check_ollama_service()
                elif current_type == "siliconflow":
                    result = translator.check_siliconflow_service()
                elif current_type == "intranet":
                    result = translator.check_intranet_service()
                else:
                    result = False

                # 更新UI
                def update_ui():
                    if result:
                        test_status_var.set("✅ 测试成功")
                        test_status_label.config(foreground="green")
                        # 启用翻译按钮
                        translate_btn.configure(state='normal')
                        status_var.set(f"🟢 {current_type} 翻译器就绪")
                    else:
                        test_status_var.set("❌ 测试失败")
                        test_status_label.config(foreground="red")
                        translate_btn.configure(state='disabled')
                        status_var.set(f"🔴 {current_type} 翻译器不可用")

                    test_btn.configure(state='normal')

                root.after(0, update_ui)

            except Exception as e:
                def update_error():
                    test_status_var.set(f"⚠️ 测试异常")
                    test_status_label.config(foreground="orange")
                    test_btn.configure(state='normal')
                    translate_btn.configure(state='disabled')

                root.after(0, update_error)

        threading.Thread(target=run_test, daemon=True).start()

    test_btn = ttk.Button(test_btn_frame, text="🧪 测试连接", command=test_current_translator, width=12)
    test_btn.pack(side='right')

    def update_translator_display(trans_type):
        """更新翻译器显示信息 - 同步版本（用于初始化）"""
        print(f"DEBUG: update_translator_display开始，类型: {trans_type}")
        # 更新卡片标题
        translator_names = {
            "zhipuai": "🧠 智谱AI翻译器",
            "ollama": "🦙 Ollama本地模型",
            "siliconflow": "💎 硅基流动云服务",
            "intranet": "🌐 内网OpenAI服务"
        }

        # 重置测试状态
        test_status_var.set("🔍 未测试")
        test_status_label.config(foreground="black")
        print("DEBUG: 测试状态重置完成")

        # 更新模型列表
        try:
            print("DEBUG: 准备设置翻译器类型")
            if translator.set_translator_type(trans_type, skip_check=True):  # 跳过网络检查以避免UI卡顿
                print("DEBUG: 翻译器类型设置成功，跳过初始模型刷新以避免卡顿")
                # 在初始化时跳过模型刷新，避免网络请求导致GUI卡顿
                model_combo['values'] = ["点击刷新获取模型"]
                model_var.set("点击刷新获取模型")
                model_combo.configure(state='readonly')
                model_status_label.config(text="⏳ 点击刷新按钮获取模型列表", foreground="gray")
                print("DEBUG: 初始化完成，跳过了模型刷新")
            else:
                print("DEBUG: 翻译器类型设置失败")
                model_combo['values'] = ["配置错误"]
                model_var.set("配置错误")
                model_combo.configure(state='disabled')
                model_status_label.config(text="❌ 翻译器配置错误", foreground="red")
        except Exception as e:
            print(f"DEBUG: update_translator_display异常: {e}")
            model_status_label.config(text=f"⚠️ 切换失败: {str(e)[:30]}...", foreground="orange")

        print("DEBUG: update_translator_display完成")

    def update_translator_display_async(trans_type):
        """异步更新翻译器显示信息 - 避免UI卡顿"""
        try:
            # 异步设置翻译器类型
            success = translator.set_translator_type(trans_type)

            def update_ui_after_switch():
                """在主线程中更新UI"""
                try:
                    if success:
                        # 异步刷新模型列表
                        def async_refresh_models():
                            try:
                                models = translator.refresh_models(trans_type)

                                def update_models_ui():
                                    if models:
                                        model_combo['values'] = models
                                        if model_var.get() not in models:
                                            model_var.set(models[0])
                                        model_combo.configure(state='readonly')
                                        model_status_label.config(text=f"✅ 找到 {len(models)} 个模型", foreground="green")
                                    else:
                                        model_combo['values'] = ["无可用模型"]
                                        model_var.set("无可用模型")
                                        model_combo.configure(state='disabled')
                                        model_status_label.config(text="❌ 未找到可用模型", foreground="red")

                                    # 重新启用所有按钮
                                    for btn in translator_buttons.values():
                                        btn.configure(state='normal')
                                    test_btn.configure(state='normal')
                                    refresh_btn.configure(state='normal')
                                    test_status_var.set("🔍 未测试")

                                root.after(0, update_models_ui)

                            except Exception as e:
                                def update_error():
                                    model_status_label.config(text=f"⚠️ 获取模型失败: {str(e)[:30]}...", foreground="orange")
                                    # 重新启用所有按钮
                                    for btn in translator_buttons.values():
                                        btn.configure(state='normal')
                                    test_btn.configure(state='normal')
                                    refresh_btn.configure(state='normal')
                                    test_status_var.set("⚠️ 模型加载失败")

                                root.after(0, update_error)

                        # 启动模型刷新线程
                        threading.Thread(target=async_refresh_models, daemon=True).start()

                    else:
                        model_combo['values'] = ["配置错误"]
                        model_var.set("配置错误")
                        model_combo.configure(state='disabled')
                        model_status_label.config(text="❌ 翻译器配置错误", foreground="red")
                        # 重新启用所有按钮
                        for btn in translator_buttons.values():
                            btn.configure(state='normal')
                        test_btn.configure(state='normal')
                        refresh_btn.configure(state='normal')
                        test_status_var.set("❌ 配置错误")

                except Exception as e:
                    model_status_label.config(text=f"⚠️ UI更新失败: {str(e)[:30]}...", foreground="orange")
                    # 重新启用所有按钮
                    for btn in translator_buttons.values():
                        btn.configure(state='normal')
                    test_btn.configure(state='normal')
                    refresh_btn.configure(state='normal')
                    test_status_var.set("⚠️ 更新失败")

            # 在主线程中更新UI
            root.after(0, update_ui_after_switch)

        except Exception as e:
            def update_error():
                model_status_label.config(text=f"⚠️ 切换失败: {str(e)[:30]}...", foreground="orange")
                # 重新启用所有按钮
                for btn in translator_buttons.values():
                    btn.configure(state='normal')
                test_btn.configure(state='normal')
                refresh_btn.configure(state='normal')
                test_status_var.set("❌ 切换失败")
                status_var.set(f"⚠️ 切换到 {trans_type} 失败")

            root.after(0, update_error)

    def check_single_translator(trans_type):
        """检查单个翻译器状态"""
        try:
            if trans_type == "zhipuai":
                result = translator._check_zhipuai_available()
            elif trans_type == "ollama":
                result = translator.check_ollama_service()
            elif trans_type == "siliconflow":
                result = translator.check_siliconflow_service()
            elif trans_type == "intranet":
                result = translator.check_intranet_service()
            else:
                result = False

            def update_status():
                if result:
                    status_var.set(f"🟢 {trans_type} 服务可用")
                else:
                    status_var.set(f"🔴 {trans_type} 服务不可用")

            root.after(0, update_status)

        except Exception as e:
            def update_error():
                status_var.set(f"⚠️ {trans_type} 检查失败")
            root.after(0, update_error)

    def on_translator_type_change():
        """当翻译器类型改变时调用（保持兼容性）"""
        translator_type = translator_type_var.get()
        update_translator_display(translator_type)
        threading.Thread(target=lambda: check_single_translator(translator_type), daemon=True).start()

    def update_model_list():
        """更新模型列表"""
        print("DEBUG: update_model_list函数开始执行")
        try:
            # 获取当前翻译器类型
            current_type = translator_type_var.get()
            print(f"DEBUG: 当前翻译器类型: {current_type}")

            # 获取当前翻译器类型的可用模型
            print("DEBUG: 正在获取可用模型...")
            available_models = translator.get_available_models(current_type)
            print(f"DEBUG: 获取到模型数量: {len(available_models) if available_models else 0}")

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
                elif current_type == "intranet":
                    current_config = translator.config.get("intranet_translator", {})

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
    print("DEBUG: 准备初始化模型列表")
    update_model_list()
    print("DEBUG: 模型列表初始化完成")

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
        elif current_type == "intranet":
            if "intranet_translator" not in translator.config:
                translator.config["intranet_translator"] = {}
            translator.config["intranet_translator"]["model"] = selected_model

        # 保存配置
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(translator.config, f, ensure_ascii=False, indent=4)

    model_combo.bind('<<ComboboxSelected>>', on_model_change)

    # 初始化当前翻译器显示
    print(f"DEBUG: 准备初始化翻译器显示，类型: {current_type}")
    update_translator_display(current_type)
    print("DEBUG: 翻译器显示初始化完成")

    # 7. 开始翻译卡片 - 最重要的按钮
    translate_card, translate_expanded = create_collapsible_card(scrollable_frame, "🚀 开始翻译", "#ffebee", True)

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

                # 设置进度回调函数
                def update_progress(progress, message):
                    """更新进度显示"""
                    def update_ui():
                        progress_var.set(progress * 100)
                        progress_text_var.set(message)
                        status_var.set(f"翻译进度: {progress:.1%}")
                    root.after(0, update_ui)

                doc_processor.set_progress_callback(update_progress)

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
                            progress_var.set(100)
                            progress_text_var.set("翻译完成")
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
                            # 重置进度条
                            progress_var.set(0)
                            progress_text_var.set("")
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
                            progress_var.set(0)
                            progress_text_var.set("翻译失败")
                            status_var.set(f"翻译出错：{error_msg}")
                            messagebox.showerror("错误", error_msg)
                            # 重置进度条
                            progress_var.set(0)
                            progress_text_var.set("")
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

    # 翻译按钮 - 放在翻译卡片中
    translate_btn = ttk.Button(translate_card, text="🚀 开始翻译", command=start_translation)
    translate_btn.pack(fill='x', pady=10)

    # 添加打开输出目录按钮
    def open_output_directory():
        """打开翻译结果输出目录"""
        try:
            import os
            import subprocess
            import platform

            # 获取输出目录路径
            output_dir = os.path.join(os.getcwd(), "输出")

            # 如果输出目录不存在，则创建它
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                status_var.set(f"📁 创建输出目录: {output_dir}")

            # 根据操作系统打开目录
            system = platform.system()
            if system == "Windows":
                os.startfile(output_dir)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", output_dir])
            else:  # Linux
                subprocess.run(["xdg-open", output_dir])

            status_var.set(f"📁 已打开输出目录: {output_dir}")

        except Exception as e:
            error_msg = f"打开输出目录失败: {str(e)}"
            status_var.set(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)

    output_dir_btn = ttk.Button(translate_card, text="📁 打开输出目录", command=open_output_directory)
    output_dir_btn.pack(fill='x', pady=(5, 10))

    # 初始化翻译按钮状态检查
    def update_translate_button_state():
        """根据当前翻译器测试状态更新翻译按钮状态"""
        try:
            current_test_status = test_status_var.get()
            if "✅" in current_test_status or "测试成功" in current_test_status:
                translate_btn.configure(state='normal')
            else:
                translate_btn.configure(state='disabled')
        except Exception as e:
            logger.error(f"更新翻译按钮状态失败: {str(e)}")

    # 定期检查并更新翻译按钮状态
    def periodic_button_check():
        update_translate_button_state()
        root.after(1000, periodic_button_check)  # 每秒检查一次

    # 启动定期检查
    root.after(1000, periodic_button_check)

    # 添加翻译提示
    translate_hint = ttk.Label(
        translate_card,
        text="💡 请确保已选择文件、设置翻译方向和检查翻译器状态",
        foreground="gray",
        font=("TkDefaultFont", 8),
        wraplength=250
    )
    translate_hint.pack(pady=(0, 5))

    # 绑定鼠标滚轮事件到画布
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # 初始检查翻译服务状态（异步进行，不阻塞UI启动）
    def initial_status_check():
        """初始状态检查"""
        try:
            current_type = translator_type_var.get()
            check_single_translator(current_type)
        except Exception as e:
            logger.error(f"初始状态检查失败: {str(e)}")
            root.after(0, lambda: status_var.set("状态检查失败，请手动检查"))

    # 延迟1秒后进行初始检查，避免阻塞UI启动
    # 暂时禁用初始状态检查，避免网络请求导致UI卡住
    # root.after(1000, lambda: threading.Thread(target=initial_status_check, daemon=True).start())

    # 设置初始状态为就绪
    status_var.set("🟢 系统就绪")
    print("DEBUG: create_ui函数即将完成")

    # 返回状态变量，供main.py使用
    print("DEBUG: create_ui函数执行完成，返回status_var")
    return status_var