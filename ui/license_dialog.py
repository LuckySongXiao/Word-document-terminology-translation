import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
from utils.license import LicenseManager
import os
import sys
import platform
import ctypes
import time

class LicenseDialog:
    def __init__(self, parent):
        try:
            # 不再创建新窗口，而是使用传入的父窗口
            self.window = parent
            self.window.title("软件授权")
            self.window.geometry("666x666")
            self.window.resizable(False, False)
            
            # 清除窗口内所有旧控件
            for widget in self.window.winfo_children():
                widget.destroy()
            
            # 设置窗口图标
            try:
                self.window.iconbitmap("logo.ico")
            except Exception as e:
                # 忽略图标设置错误
                print(f"设置图标失败: {e}")
            
            self.license_manager = LicenseManager()
            self.machine_code = self.license_manager.generate_machine_code()
            
            self.create_widgets()
            self.check_existing_license()
            
            # 添加关闭回调，确保窗口关闭时销毁
            self.window.protocol("WM_DELETE_WINDOW", self.on_close)
            
        except Exception as e:
            # 记录错误并确保显示消息给用户
            import traceback
            traceback.print_exc()
            messagebox.showerror("错误", f"初始化授权对话框时出错: {str(e)}")
    
    def on_close(self):
        """关闭窗口时的回调"""
        self.window.quit()
        self.window.destroy()
        
    # 修改关闭按钮的方法
    def close_window(self):
        self.window.quit()
        self.window.destroy()
    
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="软件授权管理", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 授权状态框架
        status_frame = ttk.LabelFrame(main_frame, text="授权状态")
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.status_var = tk.StringVar(value="正在检查授权状态...")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground="blue")
        status_label.pack(pady=10, padx=10)
        
        self.expiry_var = tk.StringVar()
        expiry_label = ttk.Label(status_frame, textvariable=self.expiry_var)
        expiry_label.pack(pady=(0, 10), padx=10)
        
        # 机器码框架
        machine_frame = ttk.LabelFrame(main_frame, text="机器码")
        machine_frame.pack(fill=tk.X, pady=(0, 20))
        
        code_frame = ttk.Frame(machine_frame)
        code_frame.pack(fill=tk.X, pady=10, padx=10)
        
        self.machine_code_var = tk.StringVar(value=self.machine_code)
        machine_entry = ttk.Entry(code_frame, textvariable=self.machine_code_var, state="readonly", width=40)
        machine_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        copy_button = ttk.Button(code_frame, text="复制", command=self.copy_machine_code)
        copy_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # 授权码框架
        license_frame = ttk.LabelFrame(main_frame, text="授权码")
        license_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.license_text = tk.Text(license_frame, height=6, width=60, wrap=tk.WORD)
        self.license_text.pack(pady=10, padx=10, fill=tk.X)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        activate_button = ttk.Button(button_frame, text="激活授权", command=self.activate_license)
        activate_button.pack(side=tk.LEFT, padx=(0, 10))
        
        close_button = ttk.Button(button_frame, text="关闭", command=self.close_window)
        close_button.pack(side=tk.LEFT)
        
        # 授权说明
        note_frame = ttk.Frame(main_frame)
        note_frame.pack(fill=tk.X, pady=(20, 0))
        
        note_label = ttk.Label(note_frame, text="授权说明", font=("Arial", 10, "bold"))
        note_label.pack(anchor=tk.W)
        
        # 修复语法错误 - 使用单一字符串
        instructions = "1. 获取机器码：复制上方的机器码\n2. 申请授权：将机器码发送给软件开发者获取授权码\n3. 激活软件：将获得的授权码粘贴到授权码框中，点击\"激活授权\"\n4. 授权激活可能需要管理员权限才能完成\n5. 授权问题请联系：739326161@qq.com"
        
        note_text = ttk.Label(note_frame, text=instructions, justify=tk.LEFT)
        note_text.pack(anchor=tk.W, pady=(5, 0))
    
    def copy_machine_code(self):
        pyperclip.copy(self.machine_code)
        messagebox.showinfo("提示", "机器码已复制到剪贴板")
    
    def check_existing_license(self):
        is_valid, message, license_data = self.license_manager.check_license()
        
        if is_valid:
            self.status_var.set(f"授权状态：已授权（{license_data['user_name']}）")
            
            # 检查是否为永久授权（通过授权时间是否非常远）
            if license_data.get("expiry_date") > time.time() + 30*365*24*3600:  # 超过30年
                self.expiry_var.set("授权类型：永久授权")
            else:
                self.expiry_var.set(message)
            
            # 尝试填充授权码
            license_code = self.license_manager.load_license()
            if license_code:
                self.license_text.delete(1.0, tk.END)
                self.license_text.insert(tk.END, license_code)
        else:
            self.status_var.set("授权状态：未授权")
            self.expiry_var.set(message if "出错" not in message else "请输入有效的授权码")
    
    def activate_license(self):
        license_code = self.license_text.get(1.0, tk.END).strip()
        
        if not license_code:
            messagebox.showwarning("警告", "请输入授权码")
            return
        
        is_valid, message, license_data = self.license_manager.verify_license(license_code)
        
        if is_valid:
            # 保存授权码到多个位置
            if self.license_manager.save_license(license_code):
                messagebox.showinfo("成功", f"授权激活成功！\n{message}")
                self.status_var.set(f"授权状态：已授权（{license_data['user_name']}）")
                self.expiry_var.set(message)
            else:
                # 尝试以管理员权限重新运行
                if messagebox.askyesno("需要管理员权限", 
                                     "授权码保存部分失败，可能需要管理员权限。\n是否尝试以管理员身份重新激活？"):
                    try:
                        # 保存授权码到临时文件，以便管理员模式使用
                        temp_license_path = os.path.join(os.environ.get('TEMP', '.'), 'temp_license.dat')
                        with open(temp_license_path, 'w', encoding='utf-8') as f:
                            f.write(license_code)
                        
                        # 使用ctypes以管理员权限重新运行程序
                        if platform.system() == "Windows":
                            ctypes.windll.shell32.ShellExecuteW(
                                None, "runas", sys.executable, f'"{os.path.abspath(sys.argv[0])}" --activate-license', None, 1
                            )
                            messagebox.showinfo("提示", "请在新打开的管理员权限窗口中完成授权激活")
                            self.window.destroy()
                        else:
                            messagebox.showwarning("提示", "非Windows系统无法自动请求管理员权限")
                    except Exception as e:
                        messagebox.showerror("错误", f"请求管理员权限失败: {str(e)}")
                else:
                    messagebox.showwarning("警告", "授权码已验证但未完全保存，某些功能可能受限")
                    self.status_var.set(f"授权状态：部分授权（{license_data['user_name']}）")
                    self.expiry_var.set(message + " (部分功能可能受限)")
        else:
            messagebox.showerror("授权失败", message) 