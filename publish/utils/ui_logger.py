import tkinter as tk
from tkinter import ttk
import logging
import os
import subprocess
from queue import Queue
from typing import Tuple
import json
import threading
from datetime import datetime
import logging.handlers
import socket
import sys
import time
import traceback
from .terminal_capture import get_terminal_capture, add_output_callback, remove_output_callback


class QueueHandler(logging.Handler):
    """队列日志处理器"""
    def __init__(self, queue):
        logging.Handler.__init__(self)
        self.queue = queue
        self.buffer = []
        self.buffer_size = 5  # 减小缓冲区大小，更快显示
        self.buffer_lock = threading.Lock()

    def emit(self, record):
        try:
            if record.levelno < self.level:
                return

            msg = self.format(record)

            # 立即将消息放入队列，不使用缓冲
            try:
                self.queue.put(msg)
            except Exception:
                pass

            # 同时使用缓冲机制作为备份
            with self.buffer_lock:
                self.buffer.append(msg)
                if len(self.buffer) >= self.buffer_size:
                    self.flush_buffer()

            # 触发UI更新（如果回调函数已设置）
            try:
                if hasattr(self, 'trigger_ui_update'):
                    self.trigger_ui_update()
            except Exception:
                pass
        except Exception:
            self.handleError(record)

    def flush_buffer(self):
        with self.buffer_lock:
            while self.buffer:
                try:
                    self.queue.put(self.buffer.pop(0))
                except Exception:
                    break


class EnhancedFileHandler(logging.Handler):
    """增强的文件日志处理器，支持实时监控和异常捕获"""
    def __init__(self):
        super().__init__()
        self.buffer = []
        self.buffer_size = 50  # 减小缓冲区大小，更频繁地写入
        self.buffer_lock = threading.Lock()
        self.exception_count = 0
        self.last_exception_time = 0
        self.log_file = 'application.log'
        self.realtime_log_file = 'realtime.log'

        # 创建实时日志文件
        try:
            with open(self.realtime_log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== 实时日志开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        except Exception:
            pass

    def emit(self, record):
        try:
            msg = self.format(record)
            current_time = time.time()

            # 检测异常
            if record.levelno >= logging.ERROR:
                self.exception_count += 1
                self.last_exception_time = current_time

            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': record.levelname,
                'message': msg,
                'module': record.module,
                'funcName': record.funcName,
                'lineno': record.lineno
            }

            # 如果是异常，添加堆栈信息
            if record.exc_info:
                log_entry['exception'] = traceback.format_exception(*record.exc_info)

            with self.buffer_lock:
                self.buffer.append(log_entry)

                # 立即写入实时日志
                self._write_realtime_log(log_entry)

                # 如果是错误或缓冲区满了，立即刷新
                if record.levelno >= logging.ERROR or len(self.buffer) >= self.buffer_size:
                    self.flush_buffer()

        except Exception:
            self.handleError(record)

    def _write_realtime_log(self, log_entry):
        """写入实时日志文件"""
        try:
            with open(self.realtime_log_file, 'a', encoding='utf-8') as f:
                timestamp = log_entry['timestamp']
                level = log_entry['level']
                message = log_entry['message']
                module = log_entry.get('module', '')
                func = log_entry.get('funcName', '')
                line = log_entry.get('lineno', '')

                # 格式化输出
                log_line = f"[{timestamp}] {level:8} {module}:{func}:{line} - {message}\n"
                f.write(log_line)
                f.flush()  # 立即刷新到磁盘

                # 如果有异常信息，也写入
                if 'exception' in log_entry:
                    f.write("异常堆栈:\n")
                    for line in log_entry['exception']:
                        f.write(f"  {line}")
                    f.write("\n")
                    f.flush()
        except Exception:
            pass  # 忽略实时日志写入错误

    def flush_buffer(self):
        with self.buffer_lock:
            if self.buffer:
                try:
                    with open(self.log_file, 'a', encoding='utf-8') as f:
                        for entry in self.buffer:
                            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                    self.buffer.clear()
                except Exception as e:
                    self.buffer.clear()
                    print(f"日志写入失败: {e}")

    def get_exception_stats(self):
        """获取异常统计信息"""
        return {
            'exception_count': self.exception_count,
            'last_exception_time': self.last_exception_time,
            'has_recent_exceptions': (time.time() - self.last_exception_time) < 300  # 5分钟内
        }


def setup_ui_logger(root: tk.Tk) -> Tuple[tk.Text, Queue]:
    """设置UI日志处理器"""
    # 创建日志显示区域
    log_frame = ttk.Frame(root)
    log_frame.pack(pady=10, padx=20, fill='both', expand=True)

    # 创建文本框和滚动条
    log_text = tk.Text(log_frame, wrap=tk.WORD, height=15)
    scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_text.configure(yscrollcommand=scrollbar.set)

    # 使用grid布局管理器
    log_text.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    # 配置grid权重
    log_frame.grid_columnconfigure(0, weight=1)
    log_frame.grid_rowconfigure(0, weight=1)

    # 创建消息队列
    message_queue = Queue()



    # 存储增强处理器的引用，供外部访问
    root_logger.enhanced_handler = enhanced_file_handler

    # 为文件路径添加点击事件
    def open_file_location(event):
        try:
            # 检查文本控件是否仍然存在
            if not log_text.winfo_exists():
                return

            index = log_text.index(f"@{event.x},{event.y}")
            line_start = log_text.index(f"{index} linestart")
            line_end = log_text.index(f"{index} lineend")
            line = log_text.get(line_start, line_end)

            if ": " in line:
                path = line[line.find(": ") + 2:].strip()
                if os.path.exists(path):
                    dir_path = os.path.dirname(path)
                    # 根据操作系统选择打开方式
                    if os.name == 'nt':  # Windows
                        os.startfile(dir_path)
                    elif os.name == 'posix':  # Linux
                        subprocess.Popen(['xdg-open', dir_path])
                    else:  # Mac
                        subprocess.Popen(['open', dir_path])
        except Exception as e:
            # 使用print而不是logger，避免可能的递归
            print(f"打开文件位置失败: {str(e)}")

    # 配置文件路径点击事件和样式
    log_text.tag_configure("path", foreground="blue", underline=1)
    log_text.tag_bind("path", "<Double-Button-1>", open_file_location)

    # 鼠标悬停时改变光标样式
    def on_enter(event):
        try:
            # 使用更安全的方式设置光标
            if log_text.winfo_exists():
                log_text["cursor"] = "hand2"
        except Exception as e:
            # 避免记录错误，以防引起更多递归
            pass

    def on_leave(event):
        try:
            # 使用更安全的方式重置光标
            if log_text.winfo_exists():
                log_text["cursor"] = ""
        except Exception as e:
            # 避免记录错误，以防引起更多递归
            pass

    # 使用try-except包装标签绑定，避免可能的错误
    try:
        log_text.tag_bind("path", "<Enter>", on_enter)
        log_text.tag_bind("path", "<Leave>", on_leave)
    except Exception as e:
        # 避免记录错误，以防引起更多递归
        pass

    # 添加异常监控状态显示
    status_frame = ttk.Frame(root)
    status_frame.pack(fill='x', padx=20, pady=5)

    exception_status_var = tk.StringVar(value="系统状态: 正常")
    exception_status_label = ttk.Label(status_frame, textvariable=exception_status_var)
    exception_status_label.pack(side='left')

    # 添加实时日志文件按钮
    def open_realtime_log():
        try:
            realtime_log_path = os.path.abspath('realtime.log')
            if os.path.exists(realtime_log_path):
                if os.name == 'nt':  # Windows
                    os.startfile(realtime_log_path)
                elif os.name == 'posix':  # Linux
                    subprocess.Popen(['xdg-open', realtime_log_path])
                else:  # Mac
                    subprocess.Popen(['open', realtime_log_path])
            else:
                tk.messagebox.showwarning("警告", "实时日志文件不存在")
        except Exception as e:
            tk.messagebox.showerror("错误", f"无法打开实时日志文件: {e}")

    realtime_log_btn = ttk.Button(status_frame, text="查看实时日志", command=open_realtime_log)
    realtime_log_btn.pack(side='right', padx=5)

    # 更新UI的函数
    def update_ui():
        try:
            # 检查文本控件是否仍然存在
            if not log_text.winfo_exists():
                return

            # 更新异常状态
            try:
                if hasattr(root_logger, 'enhanced_handler'):
                    stats = root_logger.enhanced_handler.get_exception_stats()
                    if stats['has_recent_exceptions']:
                        exception_status_var.set(f"系统状态: 检测到异常 (共{stats['exception_count']}个)")
                        exception_status_label.config(foreground='red')
                    else:
                        exception_status_var.set("系统状态: 正常")
                        exception_status_label.config(foreground='green')
            except Exception:
                pass

            # 处理队列中的消息
            messages_to_process = []
            try:
                while not message_queue.empty():
                    try:
                        msg = message_queue.get_nowait()
                        if msg:
                            messages_to_process.append(msg)
                    except:
                        break
            except Exception:
                pass

            # 批量处理消息，减少UI更新次数
            if messages_to_process:
                # 启用文本框编辑
                log_text.config(state=tk.NORMAL)

                for msg in messages_to_process:
                    try:
                        # 根据日志级别设置颜色
                        color = 'black'
                        if 'ERROR' in msg:
                            color = 'red'
                        elif 'WARNING' in msg:
                            color = 'orange'
                        elif 'INFO' in msg:
                            color = 'blue'

                        # 插入消息
                        start_index = log_text.index(tk.END)
                        log_text.insert(tk.END, msg + '\n')
                        end_index = log_text.index(tk.END)

                        # 设置颜色
                        if color != 'black':
                            log_text.tag_add(f"color_{color}", start_index, end_index)
                            log_text.tag_config(f"color_{color}", foreground=color)

                        # 如果消息中包含文件路径，添加点击事件
                        if "已保存到:" in msg or "文件已保存到:" in msg:
                            start = msg.find(": ") + 2
                            end = msg.find("\n") if "\n" in msg else len(msg)

                            # 为路径添加标签
                            last_line = log_text.get("end-2c linestart", "end-1c")
                            start_index = f"end-{len(last_line)+1}c linestart+{start}c"
                            end_index = f"end-{len(last_line)+1}c linestart+{end}c"
                            log_text.tag_add("path", start_index, end_index)
                    except Exception:
                        # 忽略单条消息处理错误
                        continue

                # 禁用文本框编辑
                log_text.config(state=tk.DISABLED)

                # 滚动到最新消息
                try:
                    log_text.see(tk.END)
                except:
                    pass

        except Exception:
            # 忽略所有错误，避免中断程序
            pass

    # 定期更新UI
    def periodic_update():
        update_ui()
        root.after(1000, periodic_update)  # 每秒更新一次

    # 启动定期更新
    root.after(1000, periodic_update)

    # 现在update_ui已经定义，可以设置QueueHandler的UI更新回调
    def trigger_ui_update():
        try:
            if root.winfo_exists():
                root.after_idle(update_ui)
        except Exception:
            pass

    # 更新QueueHandler的UI触发函数
    queue_handler.trigger_ui_update = trigger_ui_update

    # 设置终端捕获回调函数
    def terminal_output_callback(log_entry):
        """处理终端输出的回调函数"""
        try:
            # 格式化消息
            timestamp = log_entry.get('timestamp', '')
            level = log_entry.get('level', 'INFO')
            message = log_entry.get('message', '')

            # 创建格式化的日志消息
            formatted_message = f"[{timestamp}] {level} - {message}"

            # 添加到消息队列
            message_queue.put(formatted_message)

            # 触发UI更新
            trigger_ui_update()

        except Exception:
            pass

    # 启动终端捕获并添加回调
    try:
        terminal_capture = get_terminal_capture()
        terminal_capture.start_capture()
        add_output_callback(terminal_output_callback)

        # 存储回调函数引用，以便后续清理
        root.terminal_callback = terminal_output_callback

    except Exception as e:
        print(f"启动终端捕获失败: {e}")

    # 添加初始化日志消息
    try:
        # 直接向队列添加初始化消息
        message_queue.put("系统日志初始化完成")
        message_queue.put("欢迎使用多格式文档翻译助手")
        message_queue.put("终端信息将在此处实时显示")
        message_queue.put("终端输出捕获已启动，所有print输出将在此显示")

        # 立即触发一次UI更新
        root.after(100, update_ui)
    except Exception as e:
        print(f"初始化日志消息失败: {e}")

    return log_text, message_queue


def setup_ui_logger_horizontal(parent_frame) -> Tuple[tk.Text, Queue]:
    """设置横向布局的UI日志处理器"""
    # 创建日志显示区域
    log_frame = ttk.LabelFrame(parent_frame, text="系统日志 - 实时显示")
    log_frame.pack(pady=5, padx=5, fill='both', expand=True)

    # 创建文本框和滚动条
    log_text = tk.Text(log_frame, wrap=tk.WORD, height=20, font=("Consolas", 9))
    scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_text.configure(yscrollcommand=scrollbar.set)

    # 使用grid布局管理器
    log_text.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    # 配置grid权重
    log_frame.grid_rowconfigure(0, weight=1)
    log_frame.grid_columnconfigure(0, weight=1)

    # 设置文本框样式
    log_text.config(
        bg="#1e1e1e",
        fg="#ffffff",
        insertbackground="white",
        selectbackground="#3399ff",
        selectforeground="white",
        state=tk.DISABLED
    )

    # 配置日志颜色标签
    log_text.tag_config("color_red", foreground="red")
    log_text.tag_config("color_orange", foreground="orange")
    log_text.tag_config("color_blue", foreground="lightblue")
    log_text.tag_config("color_green", foreground="lightgreen")
    log_text.tag_config("path", foreground="yellow", underline=True)

    # 创建消息队列
    message_queue = Queue()

    # 创建队列处理器
    queue_handler = QueueHandler(message_queue)
    queue_handler.setLevel(logging.INFO)
    queue_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    # 添加到根日志记录器
    root_logger = logging.getLogger()
    root_logger.addHandler(queue_handler)

    # 创建文件处理器
    try:
        file_handler = EnhancedFileHandler()
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"创建文件处理器失败: {e}")

    # UI更新函数
    def update_ui():
        try:
            messages_to_process = []

            # 批量获取消息
            while not message_queue.empty() and len(messages_to_process) < 20:
                try:
                    msg = message_queue.get_nowait()
                    if msg and msg.strip():
                        messages_to_process.append(msg)
                except Exception:
                    break

            # 批量处理消息
            if messages_to_process:
                # 启用文本框编辑
                log_text.config(state=tk.NORMAL)

                for msg in messages_to_process:
                    # 插入消息并设置颜色
                    start_index = log_text.index(tk.END)
                    log_text.insert(tk.END, msg + '\n')
                    end_index = log_text.index(tk.END)

                    # 根据日志级别设置颜色
                    color = 'white'
                    if 'ERROR' in msg:
                        color = 'red'
                    elif 'WARNING' in msg:
                        color = 'orange'
                    elif 'INFO' in msg:
                        color = 'blue'
                    elif 'SUCCESS' in msg or '成功' in msg:
                        color = 'green'

                    if color != 'white':
                        log_text.tag_add(f"color_{color}", start_index, end_index)

                # 禁用文本框编辑
                log_text.config(state=tk.DISABLED)

                # 滚动到最新消息
                try:
                    log_text.see(tk.END)
                except:
                    pass

        except Exception:
            pass

    # 定期更新UI
    def periodic_update():
        update_ui()
        parent_frame.after(1000, periodic_update)

    # 启动定期更新
    parent_frame.after(1000, periodic_update)

    # 设置UI更新回调
    def trigger_ui_update():
        try:
            parent_frame.after_idle(update_ui)
        except Exception:
            pass

    queue_handler.trigger_ui_update = trigger_ui_update

    # 设置终端捕获回调函数
    def terminal_output_callback(log_entry):
        """处理终端输出的回调函数"""
        try:
            timestamp = log_entry.get('timestamp', '')
            level = log_entry.get('level', 'INFO')
            message = log_entry.get('message', '')

            formatted_message = f"[{timestamp}] {level} - {message}"
            message_queue.put(formatted_message)
            trigger_ui_update()

        except Exception:
            pass

    # 启动终端捕获并添加回调
    try:
        terminal_capture = get_terminal_capture()
        terminal_capture.start_capture()
        add_output_callback(terminal_output_callback)

        # 存储回调函数引用
        parent_frame.terminal_callback = terminal_output_callback

    except Exception as e:
        print(f"启动终端捕获失败: {e}")

    # 添加初始化日志消息
    try:
        message_queue.put("系统日志初始化完成")
        message_queue.put("欢迎使用多格式文档翻译助手")
        message_queue.put("终端信息将在此处实时显示")
        message_queue.put("终端输出捕获已启动，所有print输出将在此显示")
        parent_frame.after(100, update_ui)
    except Exception as e:
        print(f"初始化日志消息失败: {e}")

    return log_text, message_queue