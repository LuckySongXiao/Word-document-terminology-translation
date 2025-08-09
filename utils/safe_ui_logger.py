"""
安全的UI日志系统
解决GUI阻塞问题的根本性修复方案
"""

import tkinter as tk
from tkinter import ttk
import logging
import threading
from queue import Queue, Empty
from datetime import datetime
import time


class SafeUILogger:
    """安全的UI日志器 - 避免GUI阻塞"""
    
    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.message_queue = Queue()
        self.log_text = None
        self.is_running = False
        self.update_thread = None
        self.gui_ready = False
        
        # 创建UI组件
        self.setup_ui()
        
        # 延迟启动日志系统，确保GUI完全初始化
        self.parent_frame.after(2000, self.delayed_start)
    
    def setup_ui(self):
        """设置UI组件"""
        try:
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
                state=tk.DISABLED,
                bg="#1e1e1e",
                fg="#ffffff",
                insertbackground="white"
            )
            
            scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
            self.log_text.configure(yscrollcommand=scrollbar.set)
            
            self.log_text.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # 配置颜色标签
            self.log_text.tag_config("info", foreground="lightblue")
            self.log_text.tag_config("warning", foreground="orange")
            self.log_text.tag_config("error", foreground="red")
            self.log_text.tag_config("success", foreground="lightgreen")
            
            # 添加控制按钮
            button_frame = ttk.Frame(log_frame)
            button_frame.pack(fill='x', padx=5, pady=2)
            
            ttk.Button(button_frame, text="🗑️ 清除日志", 
                      command=self.clear_log).pack(side='right', padx=2)
            ttk.Button(button_frame, text="⏸️ 暂停", 
                      command=self.toggle_logging).pack(side='right', padx=2)
            
            print("SafeUILogger: UI组件创建完成")
            
        except Exception as e:
            print(f"SafeUILogger: UI设置失败: {e}")
    
    def delayed_start(self):
        """延迟启动日志系统"""
        try:
            print("SafeUILogger: 开始延迟启动")
            self.gui_ready = True
            self.start_logging()
            self.add_message("安全日志系统已启动", "success")
            self.add_message("GUI初始化完成", "info")
            print("SafeUILogger: 延迟启动完成")
        except Exception as e:
            print(f"SafeUILogger: 延迟启动失败: {e}")
    
    def start_logging(self):
        """启动日志系统"""
        if not self.is_running:
            self.is_running = True
            
            # 设置日志处理器
            self.setup_logging_handler()
            
            # 启动更新线程
            self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self.update_thread.start()
            
            print("SafeUILogger: 日志系统已启动")
    
    def setup_logging_handler(self):
        """设置日志处理器"""
        try:
            # 创建安全的队列处理器
            handler = SafeQueueHandler(self.message_queue)
            handler.setLevel(logging.INFO)
            
            # 设置格式
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            
            # 添加到根日志器
            root_logger = logging.getLogger()
            
            # 移除可能存在的其他处理器，避免冲突
            for existing_handler in root_logger.handlers[:]:
                if isinstance(existing_handler, SafeQueueHandler):
                    root_logger.removeHandler(existing_handler)
            
            root_logger.addHandler(handler)
            root_logger.setLevel(logging.INFO)
            
            print("SafeUILogger: 日志处理器设置完成")
            
        except Exception as e:
            print(f"SafeUILogger: 设置日志处理器失败: {e}")
    
    def _update_loop(self):
        """安全的更新循环"""
        while self.is_running:
            try:
                if not self.gui_ready:
                    time.sleep(0.1)
                    continue
                
                # 批量获取消息
                messages = []
                try:
                    # 非阻塞获取消息
                    while len(messages) < 10:
                        try:
                            message = self.message_queue.get_nowait()
                            messages.append(message)
                        except Empty:
                            break
                except Exception:
                    pass
                
                # 如果有消息，更新UI
                if messages:
                    self._safe_update_ui(messages)
                
                # 短暂休眠，避免CPU占用过高
                time.sleep(0.1)
                
            except Exception as e:
                print(f"SafeUILogger: 更新循环错误: {e}")
                time.sleep(0.5)
    
    def _safe_update_ui(self, messages):
        """安全地更新UI"""
        try:
            if not self.gui_ready or not self.log_text or not self.log_text.winfo_exists():
                return
            
            def update_ui():
                try:
                    if not self.log_text.winfo_exists():
                        return
                    
                    self.log_text.config(state=tk.NORMAL)
                    
                    for message in messages:
                        # 确定消息类型和颜色
                        tag = "info"
                        if isinstance(message, dict):
                            level = message.get('level', 'info').lower()
                            text = message.get('text', str(message))
                        else:
                            text = str(message)
                            if 'error' in text.lower():
                                tag = "error"
                            elif 'warning' in text.lower():
                                tag = "warning"
                            elif 'success' in text.lower() or '成功' in text:
                                tag = "success"
                        
                        # 插入消息
                        start_index = self.log_text.index(tk.END)
                        self.log_text.insert(tk.END, text + "\n")
                        end_index = self.log_text.index(tk.END)
                        
                        # 应用颜色标签
                        self.log_text.tag_add(tag, start_index, end_index)
                    
                    self.log_text.config(state=tk.DISABLED)
                    self.log_text.see(tk.END)
                    
                    # 限制日志行数
                    lines = self.log_text.get("1.0", tk.END).split('\n')
                    if len(lines) > 1000:
                        self.log_text.config(state=tk.NORMAL)
                        self.log_text.delete("1.0", "100.0")
                        self.log_text.config(state=tk.DISABLED)
                
                except Exception as e:
                    print(f"SafeUILogger: UI更新失败: {e}")
            
            # 在主线程中安全地更新UI
            if self.parent_frame.winfo_exists():
                self.parent_frame.after(0, update_ui)
                
        except Exception as e:
            print(f"SafeUILogger: 安全UI更新失败: {e}")
    
    def add_message(self, message, level="info"):
        """添加消息到日志"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = {
                'text': f"[{timestamp}] {message}",
                'level': level
            }
            self.message_queue.put(formatted_message)
        except Exception as e:
            print(f"SafeUILogger: 添加消息失败: {e}")
    
    def clear_log(self):
        """清除日志"""
        try:
            if self.log_text and self.log_text.winfo_exists():
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete("1.0", tk.END)
                self.log_text.config(state=tk.DISABLED)
        except Exception as e:
            print(f"SafeUILogger: 清除日志失败: {e}")
    
    def toggle_logging(self):
        """切换日志状态"""
        self.is_running = not self.is_running
        status = "已暂停" if not self.is_running else "已恢复"
        self.add_message(f"日志系统{status}", "info")
    
    def stop(self):
        """停止日志系统"""
        self.is_running = False
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.join(timeout=1.0)


class SafeQueueHandler(logging.Handler):
    """安全的队列处理器"""
    
    def __init__(self, queue):
        super().__init__()
        self.queue = queue
    
    def emit(self, record):
        try:
            msg = self.format(record)
            # 非阻塞放入队列
            try:
                self.queue.put_nowait(msg)
            except:
                # 如果队列满了，丢弃旧消息
                try:
                    self.queue.get_nowait()
                    self.queue.put_nowait(msg)
                except:
                    pass
        except Exception:
            # 忽略日志错误，避免影响主程序
            pass


def setup_safe_ui_logger_horizontal(parent_frame):
    """设置安全的水平布局UI日志器"""
    try:
        logger = SafeUILogger(parent_frame)
        return logger.log_text, logger.message_queue, logger
    except Exception as e:
        print(f"设置安全UI日志器失败: {e}")
        # 返回基本的文本框作为备选
        log_text = tk.Text(parent_frame, height=20, font=("Consolas", 9))
        log_text.pack(fill='both', expand=True)
        return log_text, Queue(), None
