"""
简化版UI日志系统
避免复杂的日志处理导致GUI阻塞
"""

import tkinter as tk
from tkinter import ttk
import logging
import threading
from queue import Queue, Empty
from datetime import datetime


class SimpleUILogger:
    """简化的UI日志器"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.message_queue = Queue()
        self.log_text = None
        self.update_thread = None
        self.running = False
        
        self.setup_ui()
        self.setup_logging()
        self.start_update_thread()
    
    def setup_ui(self):
        """设置UI组件"""
        # 创建日志显示区域
        log_frame = ttk.LabelFrame(self.parent_frame, text="📋 系统日志")
        log_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 创建文本框和滚动条
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(
            text_frame,
            height=20,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 添加清除按钮
        button_frame = ttk.Frame(log_frame)
        button_frame.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(button_frame, text="🗑️ 清除日志", 
                  command=self.clear_log).pack(side='right')
    
    def setup_logging(self):
        """设置日志处理"""
        # 创建简单的日志处理器
        handler = SimpleQueueHandler(self.message_queue)
        handler.setLevel(logging.INFO)
        
        # 设置格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # 添加到根日志器
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    
    def start_update_thread(self):
        """启动更新线程"""
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
    
    def _update_loop(self):
        """更新循环"""
        while self.running:
            try:
                # 从队列中获取消息
                try:
                    message = self.message_queue.get(timeout=0.1)
                    self._add_message_to_ui(message)
                except Empty:
                    continue
                except Exception as e:
                    print(f"日志更新错误: {e}")
                    
            except Exception as e:
                print(f"日志更新循环错误: {e}")
                break
    
    def _add_message_to_ui(self, message):
        """在UI中添加消息"""
        try:
            if self.log_text and self.log_text.winfo_exists():
                def update_ui():
                    try:
                        self.log_text.config(state=tk.NORMAL)
                        self.log_text.insert(tk.END, message + "\n")
                        self.log_text.see(tk.END)
                        self.log_text.config(state=tk.DISABLED)
                        
                        # 限制日志行数，避免内存占用过多
                        lines = self.log_text.get("1.0", tk.END).split('\n')
                        if len(lines) > 1000:
                            self.log_text.config(state=tk.NORMAL)
                            self.log_text.delete("1.0", "100.0")
                            self.log_text.config(state=tk.DISABLED)
                            
                    except Exception as e:
                        print(f"UI更新错误: {e}")
                
                # 在主线程中更新UI
                self.parent_frame.after(0, update_ui)
                
        except Exception as e:
            print(f"添加消息到UI错误: {e}")
    
    def clear_log(self):
        """清除日志"""
        try:
            if self.log_text:
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete("1.0", tk.END)
                self.log_text.config(state=tk.DISABLED)
        except Exception as e:
            print(f"清除日志错误: {e}")
    
    def add_message(self, message):
        """添加消息"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            self.message_queue.put(formatted_message)
        except Exception as e:
            print(f"添加消息错误: {e}")
    
    def stop(self):
        """停止日志器"""
        self.running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)


class SimpleQueueHandler(logging.Handler):
    """简化的队列处理器"""
    
    def __init__(self, queue):
        super().__init__()
        self.queue = queue
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.queue.put(msg)
        except Exception:
            # 忽略日志错误，避免影响主程序
            pass


def setup_simple_ui_logger(parent_frame):
    """设置简化的UI日志器"""
    try:
        logger = SimpleUILogger(parent_frame)
        return logger.log_text, logger.message_queue, logger
    except Exception as e:
        print(f"设置简化UI日志器失败: {e}")
        # 返回基本的文本框
        log_text = tk.Text(parent_frame, height=20, font=("Consolas", 9))
        log_text.pack(fill='both', expand=True)
        return log_text, Queue(), None


def setup_simple_ui_logger_horizontal(parent_frame):
    """设置简化的水平布局UI日志器"""
    return setup_simple_ui_logger(parent_frame)
