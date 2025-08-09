"""
修复版本的main_window.py
使用简化的日志系统，避免GUI阻塞
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .terminology_editor import create_terminology_editor
from services.document_processor import DocumentProcessor
from services.pdf_processor import PDFProcessor
from services.document_factory import DocumentProcessorFactory
from services.translator import TranslationService
from services.ollama_translator import OllamaTranslator
from utils.simple_ui_logger import setup_simple_ui_logger_horizontal
import threading
import os
import time
import logging

# Excel处理器支持
EXCEL_SUPPORT = True

logger = logging.getLogger(__name__)

def create_ui_fixed(root, terminology, translator=None):
    """
    创建修复版本的主窗口界面
    
    Args:
        root: 主窗口
        terminology: 术语表
        translator: 翻译服务实例
    """
    print("DEBUG: create_ui_fixed函数开始执行")
    root.title("多格式文档翻译助手 - 修复版")
    root.geometry("1200x800")
    
    # 确保窗口能够正确显示
    root.state('normal')
    root.deiconify()
    root.update()
    print("DEBUG: 窗口标题和大小设置完成")
    
    # 如果没有传入翻译服务实例，则创建默认实例
    print("DEBUG: 检查翻译服务实例")
    if translator is None:
        from services.translator import TranslationService
        translator = TranslationService()
    print("DEBUG: 翻译服务实例准备完成")
    
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
    
    # 在右侧面板设置简化的UI日志
    log_text, message_queue, ui_logger = setup_simple_ui_logger_horizontal(right_panel)
    
    # 创建简化的控制面板
    def create_simple_card(parent, title, bg_color="#f0f0f0"):
        """创建简化的卡片式容器"""
        card_frame = tk.Frame(parent, bg=bg_color, relief="raised", bd=1)
        card_frame.pack(pady=5, padx=5, fill='x')
        
        # 标题
        title_label = tk.Label(card_frame, text=title, font=("TkDefaultFont", 10, "bold"),
                              bg=bg_color, fg="#333333")
        title_label.pack(pady=5)
        
        # 内容区域
        content_frame = tk.Frame(card_frame, bg="white", relief="flat")
        content_frame.pack(fill='x', padx=5, pady=(0, 5))
        
        return content_frame
    
    # 1. 状态信息卡片
    status_card = create_simple_card(scrollable_frame, "📊 系统状态", "#e3f2fd")
    
    status_var = tk.StringVar(value="🟢 系统就绪")
    status_label = ttk.Label(status_card, textvariable=status_var, font=("TkDefaultFont", 9))
    status_label.pack(pady=5)
    
    # 进度显示
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(status_card, variable=progress_var, maximum=100)
    progress_bar.pack(pady=5, padx=5, fill='x')
    
    progress_text_var = tk.StringVar(value="")
    progress_label = ttk.Label(status_card, textvariable=progress_text_var, 
                              foreground="blue", font=("TkDefaultFont", 8))
    progress_label.pack(pady=2)
    
    # 2. 文件选择卡片
    file_card = create_simple_card(scrollable_frame, "📁 文档管理", "#f3e5f5")
    
    file_path_var = tk.StringVar()
    file_entry = ttk.Entry(file_card, textvariable=file_path_var, state='readonly')
    file_entry.pack(fill='x', pady=2, padx=5)
    
    def select_file():
        filetypes = [
            ("Word文档", "*.docx"),
            ("PDF文档", "*.pdf"),
            ("Excel文档", "*.xlsx;*.xls"),
            ("所有文件", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="选择要翻译的文档",
            filetypes=filetypes
        )
        if filename:
            file_path_var.set(filename)
            file_size = os.path.getsize(filename) / 1024
            status_var.set(f"📄 已选择文档 ({file_size:.1f} KB)")
            if ui_logger:
                ui_logger.add_message(f"已选择文件: {os.path.basename(filename)}")
    
    file_btn_frame = ttk.Frame(file_card)
    file_btn_frame.pack(fill='x', pady=2, padx=5)
    
    ttk.Button(file_btn_frame, text="🔍 选择文件", command=select_file).pack(side='left', padx=(0, 5))
    
    def clear_file():
        file_path_var.set("")
        status_var.set("🟢 系统就绪")
    
    ttk.Button(file_btn_frame, text="🗑️ 清除", command=clear_file).pack(side='left')
    
    # 3. 翻译设置卡片
    translation_card = create_simple_card(scrollable_frame, "🌐 翻译配置", "#e8f5e8")
    
    # 翻译方向
    direction_var = tk.StringVar(value="zh_to_en")
    
    ttk.Radiobutton(translation_card, text="🇨🇳 中文 → 外语", 
                   value="zh_to_en", variable=direction_var).pack(anchor='w', pady=2, padx=5)
    ttk.Radiobutton(translation_card, text="🌍 外语 → 中文", 
                   value="en_to_zh", variable=direction_var).pack(anchor='w', pady=2, padx=5)
    
    # 语言选择
    ttk.Label(translation_card, text="目标语言:").pack(anchor='w', pady=(10,0), padx=5)
    lang_var = tk.StringVar()
    lang_combo = ttk.Combobox(translation_card, textvariable=lang_var, state='readonly')
    lang_combo['values'] = list(terminology.keys())
    lang_combo.set('英语')
    lang_combo.pack(fill='x', pady=5, padx=5)
    
    # 4. 术语库设置卡片
    terminology_card = create_simple_card(scrollable_frame, "📚 术语库管理", "#fff3e0")
    
    def open_terminology_editor():
        try:
            create_terminology_editor(root, terminology)
            if ui_logger:
                ui_logger.add_message("术语库编辑器已打开")
        except Exception as e:
            messagebox.showerror("错误", f"打开术语库编辑器失败: {str(e)}")
            if ui_logger:
                ui_logger.add_message(f"打开术语库编辑器失败: {str(e)}")
    
    ttk.Button(terminology_card, text="📝 打开术语库编辑器", 
              command=open_terminology_editor).pack(fill='x', pady=5, padx=5)
    
    use_terminology_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(terminology_card, text="✅ 使用术语库进行翻译", 
                   variable=use_terminology_var).pack(anchor='w', pady=2, padx=5)
    
    # 5. 输出设置卡片
    output_card = create_simple_card(scrollable_frame, "📄 输出配置", "#f1f8e9")
    
    export_pdf_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(output_card, text="📑 同时导出PDF文件", 
                   variable=export_pdf_var).pack(anchor='w', pady=2, padx=5)
    
    output_format_var = tk.StringVar(value="bilingual")
    ttk.Radiobutton(output_card, text="📋 双语对照显示", 
                   value="bilingual", variable=output_format_var).pack(anchor='w', pady=2, padx=5)
    ttk.Radiobutton(output_card, text="📝 仅显示翻译结果", 
                   value="translation_only", variable=output_format_var).pack(anchor='w', pady=2, padx=5)
    
    # 6. 翻译器设置卡片
    translator_card = create_simple_card(scrollable_frame, "🤖 AI翻译引擎", "#e1f5fe")
    
    current_type = translator.get_current_translator_type()
    translator_type_var = tk.StringVar(value=current_type)
    
    # 简化的翻译器选择
    translator_types = ["智谱AI", "Ollama", "硅基流动", "内网OpenAI"]
    for i, trans_type in enumerate(translator_types):
        ttk.Radiobutton(translator_card, text=f"🤖 {trans_type}", 
                       value=trans_type.lower().replace("ai", "ai"), 
                       variable=translator_type_var).pack(anchor='w', pady=1, padx=5)
    
    # 7. 开始翻译卡片
    translate_card = create_simple_card(scrollable_frame, "🚀 开始翻译", "#ffebee")
    
    def start_translation():
        file_path = file_path_var.get()
        if not file_path:
            messagebox.showwarning("警告", "请先选择要翻译的文件！")
            return
        
        selected_lang = lang_var.get()
        status_var.set("正在翻译中...")
        
        if ui_logger:
            ui_logger.add_message(f"开始翻译: {os.path.basename(file_path)}")
            ui_logger.add_message(f"目标语言: {selected_lang}")
        
        def translation_task():
            try:
                # 创建文档处理器
                doc_processor = DocumentProcessorFactory.create_processor(file_path, translator)
                
                # 设置选项
                doc_processor.use_terminology = use_terminology_var.get()
                doc_processor.export_pdf = export_pdf_var.get()
                doc_processor.output_format = output_format_var.get()
                
                # 设置进度回调
                def update_progress(progress, message):
                    def update_ui():
                        progress_var.set(progress * 100)
                        progress_text_var.set(message)
                        status_var.set(f"翻译进度: {progress:.1%}")
                        if ui_logger:
                            ui_logger.add_message(f"进度: {message} ({progress:.1%})")
                    root.after(0, update_ui)
                
                doc_processor.set_progress_callback(update_progress)
                
                # 执行翻译
                output_path = doc_processor.process_document(
                    file_path, selected_lang, terminology
                )
                
                def show_success():
                    progress_var.set(100)
                    progress_text_var.set("翻译完成")
                    status_var.set("翻译完成！")
                    
                    if ui_logger:
                        ui_logger.add_message(f"翻译完成: {output_path}")
                    
                    messagebox.showinfo("完成", f"文档已翻译完成！\n保存位置：{output_path}")
                    progress_var.set(0)
                    progress_text_var.set("")
                
                root.after(0, show_success)
                
            except Exception as e:
                def show_error():
                    progress_var.set(0)
                    progress_text_var.set("翻译失败")
                    status_var.set(f"翻译出错：{str(e)}")
                    
                    if ui_logger:
                        ui_logger.add_message(f"翻译失败: {str(e)}")
                    
                    messagebox.showerror("错误", str(e))
                    progress_var.set(0)
                    progress_text_var.set("")
                
                root.after(0, show_error)
        
        threading.Thread(target=translation_task, daemon=True).start()
    
    ttk.Button(translate_card, text="🚀 开始翻译", command=start_translation).pack(fill='x', pady=10, padx=5)
    
    # 打开输出目录按钮
    def open_output_directory():
        try:
            import subprocess
            import platform
            
            output_dir = os.path.join(os.getcwd(), "输出")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            system = platform.system()
            if system == "Windows":
                os.startfile(output_dir)
            elif system == "Darwin":
                subprocess.run(["open", output_dir])
            else:
                subprocess.run(["xdg-open", output_dir])
            
            status_var.set(f"📁 已打开输出目录")
            if ui_logger:
                ui_logger.add_message(f"已打开输出目录: {output_dir}")
                
        except Exception as e:
            error_msg = f"打开输出目录失败: {str(e)}"
            status_var.set(f"❌ {error_msg}")
            messagebox.showerror("错误", error_msg)
    
    ttk.Button(translate_card, text="📁 打开输出目录", 
              command=open_output_directory).pack(fill='x', pady=(5, 10), padx=5)
    
    # 绑定鼠标滚轮事件
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    # 设置初始状态
    status_var.set("🟢 系统就绪")
    if ui_logger:
        ui_logger.add_message("修复版GUI初始化完成")
        ui_logger.add_message("系统就绪，等待用户操作")
    
    print("DEBUG: create_ui_fixed函数执行完成")
    return status_var
