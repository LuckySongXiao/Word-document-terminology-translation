"""
AI引擎选择对话框
在应用启动时让用户选择要使用的AI引擎
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import json
import os

logger = logging.getLogger(__name__)

class AIEngineSelector:
    def __init__(self, parent=None):
        """
        初始化AI引擎选择对话框
        
        Args:
            parent: 父窗口，如果为None则创建独立窗口
        """
        self.selected_engine = None
        self.selected_model = None
        self.result = None
        
        # 创建窗口
        if parent:
            self.window = tk.Toplevel(parent)
        else:
            self.window = tk.Tk()
            
        self.window.title("选择AI翻译引擎")
        self.window.geometry("800x650")  # 增大窗口尺寸
        self.window.resizable(False, False)
        self.window.configure(bg="#ffffff")  # 设置窗口背景色

        # 设置窗口居中
        self.center_window()

        # 设置窗口图标
        try:
            self.window.iconbitmap("logo.ico")
        except:
            pass  # 忽略图标设置错误

        # 确保窗口显示在前台
        self.window.attributes('-topmost', True)  # 设置为最顶层
        self.window.lift()  # 提升窗口
        self.window.focus_force()  # 强制获取焦点

        # 在窗口完全创建后再取消topmost属性，避免一直置顶
        self.window.after(1000, lambda: self.window.attributes('-topmost', False))
            
        # 加载配置
        self.load_config()
        
        # 创建界面
        self.create_widgets()
        
        # 设置窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

        # 设置为模态窗口（仅当有父窗口时）
        if parent:
            self.window.transient(parent)
            self.window.grab_set()
        
    def center_window(self):
        """将窗口居中显示"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
    def load_config(self):
        """加载配置文件"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            self.config = {}
            
    def create_widgets(self):
        """创建界面组件"""
        # 主标题
        title_label = tk.Label(
            self.window,
            text="🤖 选择AI翻译引擎",
            font=("微软雅黑", 18, "bold"),
            fg="#2c3e50",
            bg="#ffffff"
        )
        title_label.pack(pady=25)

        # 说明文字
        desc_label = tk.Label(
            self.window,
            text="请选择您要使用的AI翻译引擎，系统将根据您的选择进行初始化",
            font=("微软雅黑", 11),
            fg="#7f8c8d",
            bg="#ffffff",
            wraplength=500
        )
        desc_label.pack(pady=(0, 25))
        
        # 创建主要内容区域
        main_frame = tk.Frame(self.window, bg="#ffffff")
        main_frame.pack(fill="both", expand=True, padx=30, pady=10)

        # 左侧：引擎选择框架
        engine_frame = ttk.LabelFrame(main_frame, text="AI引擎选择", padding=20)
        engine_frame.pack(side="left", fill="both", expand=True, padx=(0, 15))
        
        # 引擎选择变量
        self.engine_var = tk.StringVar()
        
        # 引擎选项
        engines = [
            ("🧠 智谱AI (GLM-4)", "zhipuai", "在线AI服务，支持多种模型"),
            ("🦙 Ollama (本地)", "ollama", "本地部署，数据安全，需要本地安装"),
            ("💎 硅基流动", "siliconflow", "高性能云端AI服务"),
            ("🌐 内网OpenAI", "intranet", "企业内网OpenAI兼容服务")
        ]
        
        for name, value, desc in engines:
            # 创建单选按钮框架
            radio_frame = tk.Frame(engine_frame, relief="ridge", bd=1, bg="#f8f9fa")
            radio_frame.pack(fill="x", pady=8, padx=5)

            # 内部框架用于padding
            inner_frame = tk.Frame(radio_frame, bg="#f8f9fa")
            inner_frame.pack(fill="x", padx=15, pady=10)

            # 单选按钮
            radio = tk.Radiobutton(
                inner_frame,
                text=name,
                variable=self.engine_var,
                value=value,
                font=("微软雅黑", 12, "bold"),
                command=self.on_engine_change,
                bg="#f8f9fa",
                activebackground="#e9ecef"
            )
            radio.pack(anchor="w")

            # 描述文字
            desc_label = tk.Label(
                inner_frame,
                text=f"    {desc}",
                font=("微软雅黑", 10),
                fg="#6c757d",
                bg="#f8f9fa"
            )
            desc_label.pack(anchor="w", pady=(5, 0))
            
        # 默认选择智谱AI
        self.engine_var.set("zhipuai")

        # 右侧：模型选择和按钮区域
        right_frame = tk.Frame(main_frame, bg="#ffffff")
        right_frame.pack(side="right", fill="both", expand=True, padx=(15, 0))

        # 模型选择框架
        self.model_frame = ttk.LabelFrame(right_frame, text="模型选择", padding=20)
        self.model_frame.pack(fill="x", pady=(0, 20))

        # 模型选择说明
        model_desc = tk.Label(
            self.model_frame,
            text="选择适合您需求的AI模型：",
            font=("微软雅黑", 10),
            fg="#495057"
        )
        model_desc.pack(anchor="w", pady=(0, 10))

        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(
            self.model_frame,
            textvariable=self.model_var,
            state="readonly",
            font=("微软雅黑", 11),
            height=8
        )
        self.model_combo.pack(fill="x", pady=5)

        # 初始化模型列表
        self.on_engine_change()

        # 按钮区域（在右侧框架中）
        button_frame = tk.Frame(right_frame, bg="#f0f0f0", relief="ridge", bd=1)
        button_frame.pack(fill="x", pady=(10, 0))

        # 按钮内容框架
        button_content = tk.Frame(button_frame, bg="#f0f0f0")
        button_content.pack(fill="x", padx=20, pady=15)

        # 提示文字
        tip_label = tk.Label(
            button_content,
            text="💡 提示：选择后将初始化对应的AI服务",
            font=("微软雅黑", 9),
            fg="#6c757d",
            bg="#f0f0f0"
        )
        tip_label.pack(pady=(0, 15))

        # 按钮容器
        btn_container = tk.Frame(button_content, bg="#f0f0f0")
        btn_container.pack(fill="x")

        # 取消按钮
        cancel_btn = ttk.Button(
            btn_container,
            text="❌ 取消",
            command=self.on_cancel,
            width=15
        )
        cancel_btn.pack(side="left", padx=(0, 10))

        # 确认按钮
        confirm_btn = ttk.Button(
            btn_container,
            text="✅ 确认选择",
            command=self.on_confirm,
            width=15
        )
        confirm_btn.pack(side="right", padx=(10, 0))

        # 设置确认按钮为默认按钮（按Enter键可触发）
        self.window.bind('<Return>', lambda e: self.on_confirm())
        confirm_btn.focus_set()  # 设置焦点到确认按钮

        
    def on_engine_change(self):
        """引擎选择改变时的处理"""
        engine = self.engine_var.get()
        
        # 根据引擎类型更新模型列表
        if engine == "zhipuai":
            models = ["glm-4-flash-250414", "glm-4-flash", "glm-z1-Flash", "glm-4.1v-Thinking-Flash"]
        elif engine == "ollama":
            # 这里应该从实际安装的模型中获取，但为了简化先使用常见模型
            models = ["deepseek-r1:1.5b", "qwen3:0.6b", "gemma3:1b-it-qat", "bge-m3:latest"]
        elif engine == "siliconflow":
            models = ["deepseek-chat", "qwen-plus", "glm-4-9b-chat", "deepseek-ai/DeepSeek-V3"]
        elif engine == "intranet":
            models = ["deepseek-r1-70b", "deepseek-r1-32b", "deepseek-r1-8b", "qwen2.5-72b", "qwen2.5-32b", "qwen2.5-14b", "qwen2.5-7b", "llama3.1-70b", "llama3.1-8b"]
        else:
            models = []
            
        self.model_combo['values'] = models
        if models:
            self.model_var.set(models[0])
        else:
            self.model_var.set("")
            
    def on_confirm(self):
        """确认选择"""
        engine = self.engine_var.get()
        model = self.model_var.get()
        
        if not engine:
            messagebox.showwarning("警告", "请选择AI引擎")
            return
            
        if not model:
            messagebox.showwarning("警告", "请选择模型")
            return
            
        self.selected_engine = engine
        self.selected_model = model
        self.result = "confirm"
        self.window.destroy()
        
    def on_cancel(self):
        """取消选择"""
        self.result = "cancel"
        self.window.destroy()
        
    def on_close(self):
        """窗口关闭事件"""
        self.result = "cancel"
        self.window.destroy()
        
    def show(self):
        """显示对话框并等待用户选择"""
        self.window.wait_window()
        return self.result, self.selected_engine, self.selected_model

def show_ai_engine_selector(parent=None):
    """
    显示AI引擎选择对话框
    
    Args:
        parent: 父窗口
        
    Returns:
        tuple: (result, engine, model)
            result: "confirm" 或 "cancel"
            engine: 选择的引擎类型
            model: 选择的模型
    """
    selector = AIEngineSelector(parent)
    return selector.show()

if __name__ == "__main__":
    # 测试代码
    result, engine, model = show_ai_engine_selector()
    print(f"结果: {result}, 引擎: {engine}, 模型: {model}")
