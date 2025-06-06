import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from utils.terminology import save_terminology
import csv
import json
import os
import re
import pandas as pd
import chardet  # 添加到文件顶部的导入语句中

class TerminologyEditor:
    def __init__(self, parent, terminology):
        self.window = tk.Toplevel(parent)
        self.window.title("术语库编辑器")
        self.window.geometry("1200x800")
        self.window.minsize(1000, 600)

        # 处理术语库格式
        if "中文" in terminology:
            self.terminology = terminology["中文"]
        else:
            self.terminology = terminology

        self.current_lang = None

        # 创建主框架
        self.create_main_layout()
        # 创建工具栏
        self.create_toolbar()
        # 创建语言列表
        self.create_language_list()
        # 创建术语表格
        self.create_terminology_table()
        # 创建状态栏
        self.create_status_bar()

        # 设置样式
        self.setup_styles()

        # 初始化显示
        self.update_language_list()

        # 自动选择第一个语言
        if self.lang_listbox.size() > 0:
            self.lang_listbox.selection_set(0)
            self.on_language_select(None)

        # 设置窗口为模态
        self.window.transient(parent)
        self.window.grab_set()

        # 设置关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        """设置自定义样式，与主界面保持一致"""
        style = ttk.Style()

        # 使用与主界面相同的主题
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        # 工具栏按钮样式 - 与主界面按钮一致
        style.configure('Toolbar.TButton',
                       padding=5,
                       background='#f0f0f0')

        # 语言列表样式 - 与主界面左侧面板一致
        style.configure('LanguageList.TFrame',
                       background='#f0f0f0')

        # 表格样式 - 与主界面表格一致
        style.configure('Terminology.Treeview',
                       background='#ffffff',
                       fieldbackground='#ffffff',
                       rowheight=25)
        style.configure('Terminology.Treeview.Heading',
                       background='#e1e1e1',
                       font=('Arial', 10, 'bold'))

        # 状态栏样式 - 与主界面状态栏一致
        style.configure('Status.TLabel',
                       background='#f0f0f0',
                       padding=(5, 2))

        # 对话框样式
        style.configure('Dialog.TFrame',
                       background='#f5f5f5')

        # 标签样式
        style.configure('TLabel',
                       background='#f5f5f5')

        # 按钮样式
        style.configure('TButton',
                       padding=5)

        # 输入框样式
        style.configure('TEntry',
                       padding=5)

    def create_main_layout(self):
        """创建主布局"""
        # 设置窗口背景色与主界面一致
        self.window.configure(background='#f5f5f5')

        # 创建主容器
        self.main_container = ttk.PanedWindow(self.window, orient=tk.HORIZONTAL)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧面板
        self.left_panel = ttk.Frame(self.main_container, style='LanguageList.TFrame')
        self.main_container.add(self.left_panel, weight=1)

        # 右侧面板
        self.right_panel = ttk.Frame(self.main_container)
        self.right_panel.configure(style='TFrame')
        self.main_container.add(self.right_panel, weight=3)

    def create_toolbar(self):
        """创建工具栏"""
        toolbar = ttk.Frame(self.right_panel)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        # 搜索框
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.RIGHT, padx=5)

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=5)

        # 工具按钮
        ttk.Button(toolbar, text="添加术语", style='Toolbar.TButton',
                  command=self.add_term).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="编辑术语", style='Toolbar.TButton',
                  command=self.edit_term).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="删除术语", style='Toolbar.TButton',
                  command=self.delete_term).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        ttk.Button(toolbar, text="导入", style='Toolbar.TButton',
                  command=self.import_terminology).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="导出", style='Toolbar.TButton',
                  command=self.export_terminology).pack(side=tk.LEFT, padx=2)

    def create_language_list(self):
        """创建语言列表"""
        # 语言列表标题
        header_frame = ttk.Frame(self.left_panel)
        header_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(header_frame, text="目标语种",
                 font=('Arial', 11, 'bold')).pack(side=tk.LEFT)

        # 添加语言按钮
        ttk.Button(header_frame, text="+", width=3,
                  command=self.add_language).pack(side=tk.RIGHT)

        # 语言列表
        list_frame = ttk.Frame(self.left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 添加语言变量
        self.language_var = tk.StringVar()

        self.lang_listbox = tk.Listbox(list_frame,
                                      selectmode=tk.SINGLE,
                                      activestyle='none',
                                      font=('Arial', 10),
                                      background='#ffffff',
                                      selectbackground='#0078d7',
                                      selectforeground='#ffffff')
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                command=self.lang_listbox.yview)
        self.lang_listbox.configure(yscrollcommand=scrollbar.set)

        self.lang_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定选择事件
        self.lang_listbox.bind('<<ListboxSelect>>', self.on_language_select)

    def create_terminology_table(self):
        """创建术语表格"""
        # 表格容器
        table_frame = ttk.Frame(self.right_panel)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建表格
        columns = ('中文术语', '目标语言术语')
        self.term_tree = ttk.Treeview(table_frame, columns=columns,
                                    show='headings',
                                    style='Terminology.Treeview')

        # 配置列
        self.term_tree.column('中文术语', width=400, anchor='w')
        self.term_tree.column('目标语言术语', width=400, anchor='w')

        self.term_tree.heading('中文术语', text='中文术语')
        self.term_tree.heading('目标语言术语', text='目标语言术语')

        # 滚动条
        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL,
                               command=self.term_tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL,
                               command=self.term_tree.xview)
        self.term_tree.configure(yscrollcommand=y_scroll.set,
                               xscrollcommand=x_scroll.set)

        # 布局
        self.term_tree.grid(row=0, column=0, sticky='nsew')
        y_scroll.grid(row=0, column=1, sticky='ns')
        x_scroll.grid(row=1, column=0, sticky='ew')

        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        # 绑定事件
        self.term_tree.bind('<Double-1>', lambda e: self.edit_term())
        self.term_tree.bind('<Delete>', lambda e: self.delete_term())
        self.setup_context_menu()

        # 搜索功能
        self.search_var.trace_add("write", self.on_search_change)

    def create_status_bar(self):
        """创建状态栏"""
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(self.window, textvariable=self.status_var,
                             style='Status.TLabel', relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def setup_context_menu(self):
        """设置右键菜单"""
        self.context_menu = tk.Menu(self.term_tree, tearoff=0)
        self.context_menu.add_command(label="编辑", command=self.edit_term)
        self.context_menu.add_command(label="删除", command=self.delete_term)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="复制", command=self.copy_term)

        self.term_tree.bind("<Button-3>", self.show_context_menu)

    def add_term(self):
        """添加新术语"""
        # 获取当前选中的语言
        selected_language = self.language_var.get()
        if not selected_language:
            messagebox.showwarning("警告", "请先选择一个语言")
            return

        # 创建输入对话框
        dialog = tk.Toplevel(self.window)
        dialog.title("添加术语")
        dialog.geometry("400x240")
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.configure(background='#f5f5f5')  # 设置对话框背景色

        # 创建输入框
        dialog_frame = ttk.Frame(dialog, style='Dialog.TFrame')
        dialog_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(dialog_frame, text="中文术语:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        chinese_entry = ttk.Entry(dialog_frame, width=30)
        chinese_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog_frame, text=f"{selected_language}术语:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        foreign_entry = ttk.Entry(dialog_frame, width=30)
        foreign_entry.grid(row=1, column=1, padx=10, pady=10)

        # 确认按钮
        def confirm():
            chinese_term = chinese_entry.get().strip()
            foreign_term = foreign_entry.get().strip()

            if not chinese_term or not foreign_term:
                messagebox.showwarning("警告", "术语不能为空")
                return

            # 添加到术语库
            self.terminology[selected_language][chinese_term] = foreign_term
            # 更新显示
            self.update_term_list()
            # 关闭对话框
            dialog.destroy()

        button_frame = ttk.Frame(dialog_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="确认", command=confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)

    def edit_term(self):
        """编辑选中的术语"""
        # 获取当前选中的项
        selected_item = self.term_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一个术语")
            return

        # 获取当前选中的语言
        selected_language = self.language_var.get()
        if not selected_language:
            messagebox.showwarning("警告", "请先选择一个语言")
            return

        # 获取选中项的值
        item = self.term_tree.item(selected_item[0])
        chinese_term = item['values'][0]
        foreign_term = item['values'][1]

        # 创建编辑对话框
        dialog = tk.Toplevel(self.window)
        dialog.title("编辑术语")
        dialog.geometry("400x150")
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.configure(background='#f5f5f5')  # 设置对话框背景色

        # 创建输入框
        dialog_frame = ttk.Frame(dialog, style='Dialog.TFrame')
        dialog_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        ttk.Label(dialog_frame, text="中文术语:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        chinese_entry = ttk.Entry(dialog_frame, width=30)
        chinese_entry.insert(0, chinese_term)
        chinese_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog_frame, text=f"{selected_language}术语:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        foreign_entry = ttk.Entry(dialog_frame, width=30)
        foreign_entry.insert(0, foreign_term)
        foreign_entry.grid(row=1, column=1, padx=10, pady=10)

        # 确认按钮
        def confirm():
            new_chinese_term = chinese_entry.get().strip()
            new_foreign_term = foreign_entry.get().strip()

            if not new_chinese_term or not new_foreign_term:
                messagebox.showwarning("警告", "术语不能为空")
                return

            # 如果中文术语改变了，需要删除旧的并添加新的
            if new_chinese_term != chinese_term:
                if chinese_term in self.terminology[selected_language]:
                    del self.terminology[selected_language][chinese_term]

            # 更新术语库
            self.terminology[selected_language][new_chinese_term] = new_foreign_term

            # 更新显示
            self.update_term_list()

            # 关闭对话框
            dialog.destroy()

        button_frame = ttk.Frame(dialog_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="确认", command=confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT)

    def delete_term(self):
        """删除选中的术语"""
        # 获取当前选中的项
        selected_item = self.term_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一个术语")
            return

        # 获取当前选中的语言
        selected_language = self.language_var.get()
        if not selected_language:
            messagebox.showwarning("警告", "请先选择一个语言")
            return

        # 获取选中项的值
        item = self.term_tree.item(selected_item[0])
        chinese_term = item['values'][0]

        # 确认删除
        if messagebox.askyesno("确认", f"确定要删除术语 '{chinese_term}' 吗?"):
            # 从术语库中删除
            if chinese_term in self.terminology[selected_language]:
                del self.terminology[selected_language][chinese_term]

            # 更新显示
            self.update_term_list()

            # 更新状态栏
            self.status_var.set(f"已删除术语: {chinese_term}")

    def copy_term(self):
        """复制选中的术语"""
        # 获取当前选中的项
        selected_item = self.term_tree.selection()
        if not selected_item:
            return

        # 获取选中项的值
        item = self.term_tree.item(selected_item[0])
        chinese_term = item['values'][0]
        foreign_term = item['values'][1]

        # 复制到剪贴板
        self.window.clipboard_clear()
        self.window.clipboard_append(f"{chinese_term}: {foreign_term}")

        # 更新状态栏
        self.status_var.set("已复制到剪贴板")

    def show_context_menu(self, event):
        """显示右键菜单"""
        # 先选中点击的项
        item = self.term_tree.identify_row(event.y)
        if item:
            self.term_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def on_language_select(self, event):
        """当选择语言时更新术语列表"""
        selection = self.lang_listbox.curselection()
        if selection:
            language = self.lang_listbox.get(selection[0])
            self.language_var.set(language)
            self.current_lang = language
            self.update_term_list()
            self.status_var.set(f"已选择语言: {language}")

    def update_language_list(self):
        """更新语言列表"""
        self.lang_listbox.delete(0, tk.END)
        for lang in self.terminology.keys():
            self.lang_listbox.insert(tk.END, lang)

    def update_term_list(self):
        """更新术语列表"""
        # 清空表格
        for item in self.term_tree.get_children():
            self.term_tree.delete(item)

        # 如果没有选择语言，则返回
        if not self.current_lang:
            return

        # 获取搜索关键词
        search_text = self.search_var.get().lower()

        # 添加术语到表格
        for chinese, foreign in self.terminology[self.current_lang].items():
            # 如果有搜索关键词，则过滤
            if search_text and search_text not in chinese.lower() and search_text not in foreign.lower():
                continue

            self.term_tree.insert('', tk.END, values=(chinese, foreign))

        # 更新状态栏
        count = len(self.term_tree.get_children())
        self.status_var.set(f"显示 {count} 个术语")

    def on_search_change(self, *args):
        """当搜索框内容变化时更新术语列表"""
        self.update_term_list()

    def add_language(self):
        """添加新语言"""
        new_lang = simpledialog.askstring("添加语言", "请输入新语言名称:", parent=self.window)
        if new_lang and new_lang.strip():
            new_lang = new_lang.strip()
            # 检查是否已存在
            if new_lang in self.terminology:
                messagebox.showwarning("警告", f"语言 '{new_lang}' 已存在")
                return

            # 添加新语言
            self.terminology[new_lang] = {}

            # 更新语言列表
            self.update_language_list()

            # 更新状态栏
            self.status_var.set(f"已添加语言: {new_lang}")

    def import_terminology(self):
        """导入术语库"""
        # 获取当前选中的语言
        selected_language = self.language_var.get()
        if not selected_language:
            messagebox.showwarning("警告", "请先选择一个语言")
            return

        # 选择文件
        file_path = filedialog.askopenfilename(
            title="选择导入文件",
            filetypes=[("CSV文件", "*.csv"), ("JSON文件", "*.json"), ("所有文件", "*.*")],
            parent=self.window
        )

        if not file_path:
            return

        try:
            # 根据文件类型导入
            if file_path.lower().endswith('.csv'):
                self.import_from_csv(file_path, selected_language)
            elif file_path.lower().endswith('.json'):
                self.import_from_json(file_path, selected_language)
            else:
                messagebox.showwarning("警告", "不支持的文件类型")
                return

            # 更新显示
            self.update_term_list()

            # 更新状态栏
            self.status_var.set(f"已从 {file_path} 导入术语")

        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {str(e)}")

    def export_terminology(self):
        """导出术语库"""
        # 获取当前选中的语言
        selected_language = self.language_var.get()
        if not selected_language:
            messagebox.showwarning("警告", "请先选择一个语言")
            return

        # 选择文件
        file_path = filedialog.asksaveasfilename(
            title="保存导出文件",
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("JSON文件", "*.json")],
            parent=self.window
        )

        if not file_path:
            return

        try:
            # 根据文件类型导出
            if file_path.lower().endswith('.csv'):
                self.export_to_csv(file_path, selected_language)
            elif file_path.lower().endswith('.json'):
                self.export_to_json(file_path, selected_language)
            else:
                messagebox.showwarning("警告", "不支持的文件类型")
                return

            # 更新状态栏
            self.status_var.set(f"已导出术语到 {file_path}")

        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def import_from_csv(self, file_path, language):
        """从CSV文件导入术语"""
        if not file_path:
            return

        try:
            # 自动检测文件编码
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                detected = chardet.detect(raw_data)
                encoding = detected['encoding']

            # 如果检测到编码可信度较低，则尝试一些常见编码
            if detected['confidence'] < 0.7:
                for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1', 'windows-1252']:
                    try:
                        pd.read_csv(file_path, encoding=enc, nrows=5)  # 尝试读取前几行测试
                        encoding = enc
                        break
                    except UnicodeDecodeError:
                        continue

            # 读取CSV文件
            df = pd.read_csv(file_path, encoding=encoding)

            # 继续处理导入逻辑
            if len(df.columns) < 2:
                messagebox.showwarning("警告", "CSV文件必须至少包含两列数据：术语和翻译")
                return

            # 将数据添加到术语库中
            for index, row in df.iterrows():
                chinese_term = str(row[0]).strip()
                foreign_term = str(row[1]).strip()
                if chinese_term and foreign_term:
                    # 清理术语中的回车符和换行符
                    clean_chinese = chinese_term.replace('\r', '').replace('\n', '')
                    clean_foreign = foreign_term.replace('\r', '').replace('\n', '')
                    self.terminology[language][clean_chinese] = clean_foreign

            # 更新表格显示
            self.update_term_list()

            # 更新状态栏
            count = len(df)
            self.status_var.set(f"已成功导入{count}条术语记录（使用{encoding}编码）")

        except Exception as e:
            # 如果自动检测失败，回退到手动选择
            messagebox.showwarning("警告", f"自动检测编码失败: {str(e)}\n请手动选择文件编码")

            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1', 'iso-8859-1', 'windows-1252']
            encoding = simpledialog.askstring("选择文件编码", "请选择CSV文件的编码格式:",
                                             parent=self.window)

            if encoding:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    # 执行与上面相同的导入逻辑
                    # ...省略相同代码...
                except Exception as e:
                    messagebox.showerror("错误", f"导入CSV文件时发生错误: {str(e)}")

    def import_from_json(self, file_path, language):
        """从JSON文件导入术语"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # 尝试不同的格式
            if isinstance(data, dict):
                # 如果是直接的键值对
                if all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
                    for chinese, foreign in data.items():
                        # 清理术语中的回车符和换行符
                        clean_chinese = chinese.replace('\r', '').replace('\n', '')
                        clean_foreign = foreign.replace('\r', '').replace('\n', '')
                        self.terminology[language][clean_chinese] = clean_foreign
                # 如果是嵌套的格式
                elif language in data:
                    for chinese, foreign in data[language].items():
                        # 清理术语中的回车符和换行符
                        clean_chinese = chinese.replace('\r', '').replace('\n', '')
                        clean_foreign = foreign.replace('\r', '').replace('\n', '')
                        self.terminology[language][clean_chinese] = clean_foreign
                # 如果有"中文"这一层
                elif "中文" in data and language in data["中文"]:
                    for chinese, foreign in data["中文"][language].items():
                        # 清理术语中的回车符和换行符
                        clean_chinese = chinese.replace('\r', '').replace('\n', '')
                        clean_foreign = foreign.replace('\r', '').replace('\n', '')
                        self.terminology[language][clean_chinese] = clean_foreign

    def export_to_csv(self, file_path, language):
        """导出术语到CSV文件"""
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)

            # 根据语言设置CSV标题
            if language == "英语":
                writer.writerow(["中文术语", "英语术语"])
            elif language == "日语":
                writer.writerow(["中文术语", "日语术语"])
            elif language == "韩语":
                writer.writerow(["中文术语", "韩语术语"])
            elif language == "德语":
                writer.writerow(["中文术语", "德语术语"])
            elif language == "法语":
                writer.writerow(["中文术语", "法语术语"])
            elif language == "西班牙语":
                writer.writerow(["中文术语", "西班牙语术语"])
            else:
                writer.writerow(["中文术语", f"{language}术语"])

            # 写入术语数据
            for chinese, foreign in self.terminology[language].items():
                # 清理术语中的回车符和换行符
                clean_chinese = chinese.replace('\r', '').replace('\n', '')
                clean_foreign = foreign.replace('\r', '').replace('\n', '')
                writer.writerow([clean_chinese, clean_foreign])

    def export_to_json(self, file_path, language):
        """导出术语到JSON文件"""
        # 清理术语数据中的回车符和换行符
        clean_terminology = {}
        for chinese, foreign in self.terminology[language].items():
            clean_chinese = chinese.replace('\r', '').replace('\n', '')
            clean_foreign = foreign.replace('\r', '').replace('\n', '')
            clean_terminology[clean_chinese] = clean_foreign

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(clean_terminology, f, ensure_ascii=False, indent=2)

    def on_close(self):
        """关闭窗口时保存术语库"""
        try:
            save_terminology(self.terminology)
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"保存术语库失败: {str(e)}")

def create_terminology_editor(parent, terminology):
    editor = TerminologyEditor(parent, terminology)
    return editor.window