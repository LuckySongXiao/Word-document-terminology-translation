import sys
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import datetime
import calendar
import pickle
import importlib

# 添加项目根目录到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 确保删除所有可能的缓存
try:
    # 删除 utils 目录下的所有 .pyc 文件和 __pycache__ 目录
    utils_dir = os.path.join(project_root, 'utils')
    cache_dir = os.path.join(utils_dir, '__pycache__')
    if os.path.exists(cache_dir):
        for file in os.listdir(cache_dir):
            os.remove(os.path.join(cache_dir, file))
        os.rmdir(cache_dir)
except:
    pass

# 清除模块缓存
if 'utils.license' in sys.modules:
    del sys.modules['utils.license']

# 导入模块
from utils.license import LicenseManager

class LicenseGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("授权码生成工具")
        self.root.geometry("800x700")  # 增加窗口高度以容纳授权历史记录
        self.root.resizable(True, True)
        
        # 设置窗口图标
        try:
            self.root.iconbitmap("logo.ico")
        except Exception as e:
            pass
            
        self.license_manager = LicenseManager()
        
        # 授权历史记录文件
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "license_history.dat")
        
        # 加载授权历史
        self.license_history = self.load_license_history()
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建授权生成和历史记录标签页
        self.generate_frame = ttk.Frame(self.notebook)
        self.history_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.generate_frame, text="生成授权")
        self.notebook.add(self.history_frame, text="授权历史")
        
        self.create_generate_widgets()
        self.create_history_widgets()
    
    def create_generate_widgets(self):
        main_frame = ttk.Frame(self.generate_frame, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="授权码生成工具", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 用户信息框架
        info_frame = ttk.LabelFrame(main_frame, text="用户信息")
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 机器码
        code_frame = ttk.Frame(info_frame)
        code_frame.pack(fill=tk.X, pady=(10, 5), padx=10)
        
        ttk.Label(code_frame, text="机器码：", width=15).pack(side=tk.LEFT)
        
        self.machine_code_var = tk.StringVar()
        machine_entry = ttk.Entry(code_frame, textvariable=self.machine_code_var, width=40)
        machine_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 添加验证按钮
        verify_button = ttk.Button(code_frame, text="验证", command=self.verify_machine_code)
        verify_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # 用户名
        name_frame = ttk.Frame(info_frame)
        name_frame.pack(fill=tk.X, pady=5, padx=10)
        
        ttk.Label(name_frame, text="用户名：", width=15).pack(side=tk.LEFT)
        
        self.name_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.name_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 公司名
        company_frame = ttk.Frame(info_frame)
        company_frame.pack(fill=tk.X, pady=5, padx=10)
        
        ttk.Label(company_frame, text="公司名：", width=15).pack(side=tk.LEFT)
        
        self.company_var = tk.StringVar()
        ttk.Entry(company_frame, textvariable=self.company_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 授权期限设置框架
        license_period_frame = ttk.LabelFrame(main_frame, text="授权期限设置")
        license_period_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 授权类型选择
        type_frame = ttk.Frame(license_period_frame)
        type_frame.pack(fill=tk.X, pady=5, padx=10)
        
        self.license_type_var = tk.StringVar(value="fixed_days")
        
        ttk.Radiobutton(type_frame, text="固定天数", variable=self.license_type_var, 
                       value="fixed_days", command=self.update_period_options).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Radiobutton(type_frame, text="截止日期", variable=self.license_type_var, 
                       value="expiry_date", command=self.update_period_options).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Radiobutton(type_frame, text="永久授权", variable=self.license_type_var, 
                       value="permanent", command=self.update_period_options).pack(side=tk.LEFT)
        
        # 天数选择框架
        self.days_frame = ttk.Frame(license_period_frame)
        self.days_frame.pack(fill=tk.X, pady=5, padx=10)
        
        ttk.Label(self.days_frame, text="预设天数：", width=15).pack(side=tk.LEFT)
        
        # 预设天数选择
        self.preset_days_var = tk.StringVar()
        self.preset_days_combo = ttk.Combobox(self.days_frame, textvariable=self.preset_days_var, 
                                             values=["30天", "90天", "180天", "365天", "730天", "自定义"])
        self.preset_days_combo.set("365天")
        self.preset_days_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.preset_days_combo.bind("<<ComboboxSelected>>", self.on_preset_days_change)
        
        # 自定义天数输入
        self.days_var = tk.StringVar(value="365")
        self.days_entry = ttk.Entry(self.days_frame, textvariable=self.days_var, width=10)
        self.days_entry.pack(side=tk.LEFT)
        ttk.Label(self.days_frame, text="天").pack(side=tk.LEFT)
        
        # 截止日期选择框架
        self.date_frame = ttk.Frame(license_period_frame)
        
        ttk.Label(self.date_frame, text="截止日期：", width=15).pack(side=tk.LEFT)
        
        # 年份选择
        current_year = datetime.datetime.now().year
        self.year_var = tk.StringVar(value=str(current_year + 1))
        year_combo = ttk.Combobox(self.date_frame, textvariable=self.year_var, 
                                 values=[str(current_year + i) for i in range(11)])
        year_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(self.date_frame, text="年").pack(side=tk.LEFT, padx=(0, 5))
        
        # 月份选择
        self.month_var = tk.StringVar(value="12")
        month_combo = ttk.Combobox(self.date_frame, textvariable=self.month_var, 
                                  values=[str(i).zfill(2) for i in range(1, 13)])
        month_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(self.date_frame, text="月").pack(side=tk.LEFT, padx=(0, 5))
        
        # 日期选择
        self.day_var = tk.StringVar(value="31")
        self.day_combo = ttk.Combobox(self.date_frame, textvariable=self.day_var, 
                                    values=[str(i).zfill(2) for i in range(1, 32)])
        self.day_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(self.date_frame, text="日").pack(side=tk.LEFT)
        
        # 永久授权提示框架
        self.permanent_frame = ttk.Frame(license_period_frame)
        ttk.Label(self.permanent_frame, text="此授权将永不过期", foreground="blue").pack(pady=10)
        
        # 初始显示固定天数选项
        self.update_period_options()
        
        # 生成结果框架
        result_frame = ttk.LabelFrame(main_frame, text="授权码")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.result_text = tk.Text(result_frame, height=6, width=60, wrap=tk.WORD)
        self.result_text.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        generate_button = ttk.Button(button_frame, text="生成授权码", command=self.generate_license)
        generate_button.pack(side=tk.LEFT, padx=(0, 10))
        
        copy_button = ttk.Button(button_frame, text="复制授权码", command=self.copy_license)
        copy_button.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_button = ttk.Button(button_frame, text="清空", command=self.clear_fields)
        clear_button.pack(side=tk.LEFT)
    
    def update_period_options(self):
        """根据授权类型显示不同的期限设置选项"""
        license_type = self.license_type_var.get()
        
        # 隐藏所有期限设置框架
        self.days_frame.pack_forget()
        self.date_frame.pack_forget()
        self.permanent_frame.pack_forget()
        
        if license_type == "fixed_days":
            self.days_frame.pack(fill=tk.X, pady=5, padx=10)
            self.on_preset_days_change(None)  # 更新天数输入框状态
        elif license_type == "expiry_date":
            self.date_frame.pack(fill=tk.X, pady=5, padx=10)
        else:  # permanent
            self.permanent_frame.pack(fill=tk.X, pady=5, padx=10)
    
    def on_preset_days_change(self, event):
        """处理预设天数选择变化"""
        selected = self.preset_days_var.get()
        
        if selected == "自定义":
            self.days_entry.configure(state="normal")
            self.days_entry.focus_set()
        else:
            # 设置对应的天数
            days_map = {"30天": "30", "90天": "90", "180天": "180", "365天": "365", "730天": "730"}
            self.days_var.set(days_map.get(selected, "365"))
            self.days_entry.configure(state="readonly")
    
    def calculate_days(self):
        """计算授权天数"""
        license_type = self.license_type_var.get()
        
        if license_type == "fixed_days":
            try:
                return int(self.days_var.get().strip())
            except ValueError:
                messagebox.showerror("错误", "授权天数必须是有效的整数")
                return 0
        elif license_type == "expiry_date":
            try:
                year = int(self.year_var.get())
                month = int(self.month_var.get())
                day = int(self.day_var.get())
                
                # 处理无效日期，如2月30日
                last_day = calendar.monthrange(year, month)[1]
                if day > last_day:
                    day = last_day
                    messagebox.showinfo("提示", f"{month}月只有{last_day}天，已自动调整。")
                
                expiry_date = datetime.datetime(year, month, day, 23, 59, 59)
                today = datetime.datetime.now()
                
                delta = expiry_date - today
                days = delta.days + 1  # 包含当天
                
                if days <= 0:
                    messagebox.showerror("错误", "截止日期必须在今天之后")
                    return 0
                
                return days
            except Exception as e:
                messagebox.showerror("错误", f"日期计算出错: {str(e)}")
                return 0
        else:  # permanent
            # 返回一个非常大的数字，相当于99年
            return 36500  # 约100年
    
    def verify_machine_code(self):
        """验证输入的机器码"""
        machine_code = self.machine_code_var.get().strip()
        
        if not machine_code:
            messagebox.showwarning("警告", "请输入机器码")
            return
        
        try:
            # 验证机器码长度
            if len(machine_code) != 32:
                messagebox.showerror("错误", "机器码格式不正确，应为32位字符")
                return False
            
            # 对于授权生成工具，我们只需要验证机器码格式是否正确
            # 不需要验证是否与当前设备匹配，因为这是用来给其他设备生成授权的工具
            messagebox.showinfo("验证成功", "机器码格式验证通过，可以继续生成授权码")
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"机器码验证失败：{str(e)}")
            return False
    
    def generate_license(self):
        """生成授权码"""
        machine_code = self.machine_code_var.get().strip()
        user_name = self.name_var.get().strip()
        company = self.company_var.get().strip()
        
        # 验证输入
        if not machine_code or not user_name or not company:
            messagebox.showerror("错误", "请填写所有字段")
            return
        
        # 先验证机器码
        if not self.verify_machine_code():
            return
        
        # 计算有效天数
        valid_days = self.calculate_days()
        if valid_days <= 0:
            return
        
        # 生成授权码
        try:
            license_code = self.license_manager.generate_license(
                machine_code, user_name, company, valid_days
            )
            
            # 显示授权码
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, license_code)
            
            # 记录授权历史
            license_type = self.license_type_var.get()
            expiry_date = datetime.datetime.now() + datetime.timedelta(days=valid_days)
            
            history_entry = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "machine_code": machine_code,
                "user_name": user_name,
                "company": company,
                "license_type": "永久授权" if license_type == "permanent" else 
                                (f"固定天数({valid_days}天)" if license_type == "fixed_days" else
                                f"截止日期({expiry_date.strftime('%Y-%m-%d')})"),
                "expiry_date": expiry_date.strftime("%Y-%m-%d") if license_type != "permanent" else "永久有效",
                "valid_days": valid_days,
                "license_code": license_code
            }
            
            self.license_history.append(history_entry)
            self.save_license_history()
            self.update_history_display()
            
            # 显示授权信息
            if license_type == "permanent":
                messagebox.showinfo("成功", f"授权码生成成功！\n授权类型: 永久授权\n已保存到授权历史")
            else:
                messagebox.showinfo("成功", 
                    f"授权码生成成功！\n有效期至: {expiry_date.strftime('%Y-%m-%d')}\n已保存到授权历史")
            
        except Exception as e:
            messagebox.showerror("错误", f"生成授权码失败: {str(e)}")
    
    def copy_license(self):
        license_code = self.result_text.get(1.0, tk.END).strip()
        if license_code:
            self.root.clipboard_clear()
            self.root.clipboard_append(license_code)
            messagebox.showinfo("提示", "授权码已复制到剪贴板")
        else:
            messagebox.showwarning("警告", "没有授权码可复制")
    
    def clear_fields(self):
        self.machine_code_var.set("")
        self.name_var.set("")
        self.company_var.set("")
        self.days_var.set("365")
        self.preset_days_var.set("365天")
        self.license_type_var.set("fixed_days")
        self.update_period_options()
        self.result_text.delete(1.0, tk.END)
    
    def create_history_widgets(self):
        """创建授权历史记录页面"""
        main_frame = ttk.Frame(self.history_frame, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="授权历史记录", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 搜索框架
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        search_button = ttk.Button(search_frame, text="搜索", command=self.search_history)
        search_button.pack(side=tk.LEFT)
        
        clear_button = ttk.Button(search_frame, text="清除", command=self.clear_search)
        clear_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # 历史记录列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建Treeview显示历史记录
        columns = (
            "时间", "用户名", "公司", "机器码", "授权类型", "到期日期"
        )
        
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题
        for col in columns:
            self.history_tree.heading(col, text=col)
            if col in ["时间", "到期日期"]:
                self.history_tree.column(col, width=120, anchor=tk.CENTER)
            elif col == "机器码":
                self.history_tree.column(col, width=140, anchor=tk.CENTER)
            elif col == "授权类型":
                self.history_tree.column(col, width=100, anchor=tk.CENTER)
            else:
                self.history_tree.column(col, width=100, anchor=tk.W)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscroll=scrollbar.set)
        
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定双击事件
        self.history_tree.bind("<Double-1>", self.show_license_details)
        
        # 操作按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        view_button = ttk.Button(button_frame, text="查看详情", command=self.view_selected_license)
        view_button.pack(side=tk.LEFT, padx=(0, 5))
        
        copy_button = ttk.Button(button_frame, text="复制授权码", command=self.copy_selected_license)
        copy_button.pack(side=tk.LEFT, padx=(0, 5))
        
        export_button = ttk.Button(button_frame, text="导出记录", command=self.export_history)
        export_button.pack(side=tk.LEFT, padx=(0, 5))
        
        delete_button = ttk.Button(button_frame, text="删除记录", command=self.delete_selected_license)
        delete_button.pack(side=tk.LEFT)
        
        # 初始化历史记录显示
        self.update_history_display()
    
    def update_history_display(self, filtered_history=None):
        """更新历史记录显示"""
        # 清空现有记录
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # 添加历史记录
        history_to_display = filtered_history or self.license_history
        
        for i, entry in enumerate(history_to_display):
            self.history_tree.insert("", tk.END, values=(
                entry["timestamp"],
                entry["user_name"],
                entry["company"],
                entry["machine_code"],
                entry["license_type"],
                entry["expiry_date"]
            ), tags=(f"entry_{i}",))
    
    def search_history(self):
        """搜索历史记录"""
        search_text = self.search_var.get().strip().lower()
        if not search_text:
            self.update_history_display()
            return
        
        # 筛选匹配的记录
        filtered_history = []
        for entry in self.license_history:
            if (search_text in entry["user_name"].lower() or
                search_text in entry["company"].lower() or
                search_text in entry["machine_code"].lower() or
                search_text in entry["timestamp"].lower() or
                search_text in entry["expiry_date"].lower() or
                search_text in entry["license_type"].lower()):
                filtered_history.append(entry)
        
        self.update_history_display(filtered_history)
    
    def clear_search(self):
        """清除搜索"""
        self.search_var.set("")
        self.update_history_display()
    
    def show_license_details(self, event):
        """双击显示授权详情"""
        self.view_selected_license()
    
    def view_selected_license(self):
        """查看选中的授权详情"""
        selected_item = self.history_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一条授权记录")
            return
        
        # 获取所选项的索引
        index = self.history_tree.index(selected_item[0])
        if 0 <= index < len(self.license_history):
            entry = self.license_history[index]
            
            # 创建详情窗口
            detail_window = tk.Toplevel(self.root)
            detail_window.title("授权详情")
            detail_window.geometry("500x450")  # 增加窗口高度以容纳机器码验证状态
            detail_window.transient(self.root)
            detail_window.grab_set()
            
            # 详情内容
            detail_frame = ttk.Frame(detail_window, padding=20)
            detail_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(detail_frame, text="授权详细信息", font=("Arial", 14, "bold")).pack(pady=(0, 20))
            
            # 添加机器码验证状态
            is_valid, message = self.license_manager.verify_machine_code(entry['machine_code'])
            machine_code_status = "有效" if is_valid else "无效"
            
            info_text = (
                f"授权时间: {entry['timestamp']}\n"
                f"用户名: {entry['user_name']}\n"
                f"公司: {entry['company']}\n"
                f"机器码: {entry['machine_code']}\n"
                f"机器码状态: {machine_code_status}\n"
                f"授权类型: {entry['license_type']}\n"
                f"到期日期: {entry['expiry_date']}\n"
            )
            
            ttk.Label(detail_frame, text=info_text, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 10))
            
            # 授权码
            ttk.Label(detail_frame, text="授权码:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
            
            license_text = tk.Text(detail_frame, height=6, width=50, wrap=tk.WORD)
            license_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
            license_text.insert(tk.END, entry["license_code"])
            license_text.configure(state="disabled")
            
            # 按钮框架
            button_frame = ttk.Frame(detail_frame)
            button_frame.pack(fill=tk.X, pady=(10, 0))
            
            copy_button = ttk.Button(button_frame, text="复制授权码", 
                                   command=lambda: self.copy_to_clipboard(entry["license_code"]))
            copy_button.pack(side=tk.LEFT, padx=(0, 10))
            
            close_button = ttk.Button(button_frame, text="关闭", command=detail_window.destroy)
            close_button.pack(side=tk.LEFT)
    
    def copy_selected_license(self):
        """复制选中的授权码"""
        selected_item = self.history_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一条授权记录")
            return
        
        # 获取所选项的索引
        index = self.history_tree.index(selected_item[0])
        if 0 <= index < len(self.license_history):
            license_code = self.license_history[index]["license_code"]
            self.copy_to_clipboard(license_code)
            messagebox.showinfo("提示", "授权码已复制到剪贴板")
    
    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
    
    def delete_selected_license(self):
        """删除选中的授权记录"""
        selected_item = self.history_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一条授权记录")
            return
        
        if messagebox.askyesno("确认", "确定要删除选中的授权记录吗？"):
            # 获取所选项的索引
            index = self.history_tree.index(selected_item[0])
            if 0 <= index < len(self.license_history):
                del self.license_history[index]
                self.save_license_history()
                self.update_history_display()
                messagebox.showinfo("提示", "授权记录已成功删除")
    
    def export_history(self):
        """导出授权历史记录"""
        # 询问保存位置
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
            title="导出授权历史"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    # 写入表头
                    f.write("授权时间,用户名,公司,机器码,授权类型,到期日期,授权码\n")
                    
                    # 写入数据
                    for entry in self.license_history:
                        f.write(f"{entry['timestamp']},{entry['user_name']},{entry['company']},"
                               f"{entry['machine_code']},{entry['license_type']},{entry['expiry_date']},"
                               f"{entry['license_code']}\n")
                
                messagebox.showinfo("成功", f"授权历史已成功导出到：\n{filename}")
            except Exception as e:
                messagebox.showerror("错误", f"导出历史记录失败: {str(e)}")
    
    def load_license_history(self):
        """加载授权历史记录"""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"加载授权历史记录失败: {str(e)}")
            return []
    
    def save_license_history(self):
        """保存授权历史记录"""
        try:
            with open(self.history_file, 'wb') as f:
                pickle.dump(self.license_history, f)
        except Exception as e:
            print(f"保存授权历史记录失败: {str(e)}")
            messagebox.showerror("错误", f"保存授权历史记录失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LicenseGeneratorApp(root)
    root.mainloop() 