#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
功能完整的调试版本
包含术语库编辑和实际翻译功能
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import logging
import threading
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def create_full_ui(root):
    """创建功能完整的UI"""
    print("DEBUG: 开始创建功能完整的UI")
    
    root.title("多格式文档翻译助手 - 功能完整调试版")
    root.geometry("1400x900")
    
    # 创建主容器
    main_container = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 左侧面板
    left_panel = ttk.Frame(main_container)
    main_container.add(left_panel, weight=1)
    
    # 右侧面板
    right_panel = ttk.Frame(main_container)
    main_container.add(right_panel, weight=2)
    
    # 左侧内容
    ttk.Label(left_panel, text="控制面板", font=("Arial", 14, "bold")).pack(pady=10)
    
    # 文件选择
    file_frame = ttk.LabelFrame(left_panel, text="📁 文件选择")
    file_frame.pack(fill='x', padx=5, pady=5)
    
    file_var = tk.StringVar()
    file_entry = ttk.Entry(file_frame, textvariable=file_var)
    file_entry.pack(fill='x', padx=5, pady=5)
    
    def select_file():
        filename = filedialog.askopenfilename(
            title="选择文档",
            filetypes=[
                ("Word文档", "*.docx"),
                ("PDF文档", "*.pdf"),
                ("Excel文档", "*.xlsx;*.xls"),
                ("所有文件", "*.*")
            ]
        )
        if filename:
            file_var.set(filename)
            log_text.insert('end', f"📄 已选择文件: {os.path.basename(filename)}\n")
            log_text.see('end')
    
    ttk.Button(file_frame, text="🔍 选择文件", command=select_file).pack(pady=5)
    
    # 翻译设置
    settings_frame = ttk.LabelFrame(left_panel, text="🌐 翻译设置")
    settings_frame.pack(fill='x', padx=5, pady=5)
    
    # 翻译方向
    direction_frame = ttk.Frame(settings_frame)
    direction_frame.pack(fill='x', padx=5, pady=2)
    
    ttk.Label(direction_frame, text="翻译方向:").pack(anchor='w')
    direction_var = tk.StringVar(value="zh_to_en")
    
    ttk.Radiobutton(direction_frame, text="🇨🇳 中文 → 外语", 
                   value="zh_to_en", variable=direction_var).pack(anchor='w')
    ttk.Radiobutton(direction_frame, text="🌍 外语 → 中文", 
                   value="en_to_zh", variable=direction_var).pack(anchor='w')
    
    # 目标语言
    ttk.Label(settings_frame, text="目标语言:").pack(anchor='w', padx=5, pady=(10,0))
    lang_var = tk.StringVar(value="英语")
    lang_combo = ttk.Combobox(settings_frame, textvariable=lang_var, 
                             values=["英语", "日语", "韩语", "法语", "德语", "西班牙语", "意大利语", "俄语"])
    lang_combo.pack(fill='x', padx=5, pady=2)
    
    # AI引擎
    ttk.Label(settings_frame, text="AI引擎:").pack(anchor='w', padx=5, pady=(10,0))
    engine_var = tk.StringVar(value="智谱AI")
    engine_combo = ttk.Combobox(settings_frame, textvariable=engine_var,
                               values=["智谱AI", "Ollama", "硅基流动", "内网OpenAI"])
    engine_combo.pack(fill='x', padx=5, pady=2)
    
    # 术语库管理
    terminology_frame = ttk.LabelFrame(left_panel, text="📚 术语库管理")
    terminology_frame.pack(fill='x', padx=5, pady=5)
    
    def open_terminology_editor():
        try:
            # 导入术语库相关模块
            from utils.terminology import load_terminology
            from ui.terminology_editor import create_terminology_editor
            
            # 加载术语库
            terminology = load_terminology()
            
            # 打开术语库编辑器
            create_terminology_editor(root, terminology)
            
            log_text.insert('end', "📝 术语库编辑器已打开\n")
            log_text.see('end')
            
        except Exception as e:
            log_text.insert('end', f"❌ 打开术语库编辑器失败: {str(e)}\n")
            log_text.see('end')
            messagebox.showerror("错误", f"打开术语库编辑器失败: {str(e)}")
    
    ttk.Button(terminology_frame, text="📝 编辑术语库", command=open_terminology_editor).pack(fill='x', padx=5, pady=5)
    
    # 术语库选项
    use_terminology_var = tk.BooleanVar(value=True)
    use_terminology_check = ttk.Checkbutton(
        terminology_frame,
        text="✅ 使用术语库翻译",
        variable=use_terminology_var
    )
    use_terminology_check.pack(anchor='w', padx=5, pady=2)
    
    ttk.Label(terminology_frame, text="💡 关闭后使用更自然的翻译风格", 
             foreground="gray", font=("Arial", 8)).pack(anchor='w', padx=5, pady=1)
    
    # 输出设置
    output_frame = ttk.LabelFrame(left_panel, text="📄 输出设置")
    output_frame.pack(fill='x', padx=5, pady=5)
    
    export_pdf_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(output_frame, text="📑 同时导出PDF", 
                   variable=export_pdf_var).pack(anchor='w', padx=5, pady=2)
    
    output_format_var = tk.StringVar(value="bilingual")
    ttk.Radiobutton(output_frame, text="📋 双语对照", 
                   value="bilingual", variable=output_format_var).pack(anchor='w', padx=5)
    ttk.Radiobutton(output_frame, text="📝 仅翻译结果", 
                   value="translation_only", variable=output_format_var).pack(anchor='w', padx=5)
    
    # 翻译按钮
    def start_translation():
        try:
            file_path = file_var.get()
            if not file_path:
                messagebox.showwarning("警告", "请先选择要翻译的文件")
                return
            
            target_lang = lang_var.get()
            ai_engine = engine_var.get()
            use_terminology = use_terminology_var.get()
            direction = direction_var.get()
            export_pdf = export_pdf_var.get()
            output_format = output_format_var.get()
            
            log_text.insert('end', f"📄 文件: {os.path.basename(file_path)}\n")
            log_text.insert('end', f"🔄 翻译方向: {direction}\n")
            log_text.insert('end', f"🌐 目标语言: {target_lang}\n")
            log_text.insert('end', f"🤖 AI引擎: {ai_engine}\n")
            log_text.insert('end', f"📚 使用术语库: {'是' if use_terminology else '否'}\n")
            log_text.insert('end', f"📑 导出PDF: {'是' if export_pdf else '否'}\n")
            log_text.insert('end', f"📋 输出格式: {output_format}\n")
            log_text.insert('end', "🚀 开始翻译...\n")
            log_text.see('end')
            
            # 实际翻译功能
            def translation_task():
                try:
                    # 导入翻译相关模块
                    from services.translator import TranslationService
                    from services.document_factory import DocumentProcessorFactory
                    from utils.terminology import load_terminology
                    
                    # 创建翻译服务
                    translator = TranslationService()
                    
                    # 创建文档处理器
                    doc_processor = DocumentProcessorFactory.create_processor(file_path, translator)
                    
                    # 设置选项
                    doc_processor.use_terminology = use_terminology
                    doc_processor.export_pdf = export_pdf
                    doc_processor.output_format = output_format
                    
                    # 加载术语库
                    terminology = load_terminology()
                    
                    # 设置进度回调
                    def update_progress(progress, message):
                        def update_ui():
                            log_text.insert('end', f"⏳ {message} ({progress:.1%})\n")
                            log_text.see('end')
                        root.after(0, update_ui)
                    
                    doc_processor.set_progress_callback(update_progress)
                    
                    # 执行翻译
                    output_path = doc_processor.process_document(
                        file_path, target_lang, terminology,
                        source_lang="zh" if direction == "zh_to_en" else "en",
                        target_lang="en" if direction == "zh_to_en" else "zh"
                    )
                    
                    def show_success():
                        log_text.insert('end', f"✅ 翻译完成！\n")
                        log_text.insert('end', f"📁 输出文件: {output_path}\n")
                        log_text.see('end')
                        messagebox.showinfo("完成", f"翻译完成！\n输出文件: {output_path}")
                    
                    root.after(0, show_success)
                    
                except Exception as e:
                    def show_error():
                        log_text.insert('end', f"❌ 翻译失败: {str(e)}\n")
                        log_text.see('end')
                        messagebox.showerror("错误", f"翻译失败: {str(e)}")
                    
                    root.after(0, show_error)
            
            # 在后台线程中执行翻译
            threading.Thread(target=translation_task, daemon=True).start()
            
        except Exception as e:
            log_text.insert('end', f"❌ 启动翻译失败: {str(e)}\n")
            log_text.see('end')
            messagebox.showerror("错误", f"启动翻译失败: {str(e)}")
    
    ttk.Button(settings_frame, text="🚀 开始翻译", command=start_translation).pack(fill='x', padx=5, pady=10)
    
    # 打开输出目录按钮
    def open_output_dir():
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
        
        log_text.insert('end', f"📁 已打开输出目录: {output_dir}\n")
        log_text.see('end')
    
    ttk.Button(settings_frame, text="📁 打开输出目录", command=open_output_dir).pack(fill='x', padx=5, pady=5)
    
    # 右侧日志
    ttk.Label(right_panel, text="系统日志", font=("Arial", 14, "bold")).pack(pady=10)
    
    log_frame = ttk.Frame(right_panel)
    log_frame.pack(fill='both', expand=True, padx=5, pady=5)
    
    log_text = tk.Text(log_frame, height=20, font=("Consolas", 9))
    log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_text.configure(yscrollcommand=log_scrollbar.set)
    
    log_text.pack(side="left", fill="both", expand=True)
    log_scrollbar.pack(side="right", fill="y")
    
    # 添加初始日志
    log_text.insert('end', "🎉 功能完整调试版本初始化完成\n")
    log_text.insert('end', "✅ GUI界面加载成功\n")
    log_text.insert('end', "📚 术语库编辑功能已启用\n")
    log_text.insert('end', "🚀 翻译功能已启用\n")
    log_text.insert('end', "⏳ 等待用户操作...\n")
    
    print("DEBUG: 功能完整UI创建完成")
    return log_text

def main():
    """主函数"""
    print("=== 功能完整调试版本启动 ===")
    
    try:
        # 设置日志
        logger = setup_logging()
        logger.info("开始启动功能完整调试版本")
        
        print("1. 创建主窗口...")
        root = tk.Tk()
        
        print("2. 创建UI...")
        log_widget = create_full_ui(root)
        
        print("3. 配置窗口...")
        root.update_idletasks()
        
        # 窗口居中
        width = 1400
        height = 900
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        
        print("4. 显示窗口...")
        root.deiconify()
        root.lift()
        root.focus_force()
        
        print("5. 启动主循环...")
        
        # 添加状态检查
        def status_check():
            print("DEBUG: 功能完整GUI正在运行...")
            log_widget.insert('end', "🔄 GUI状态检查: 正常运行\n")
            log_widget.see('end')
            root.after(10000, status_check)
        
        root.after(2000, status_check)
        
        print("6. 调用mainloop()...")
        root.mainloop()
        print("7. mainloop()结束")
        
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
