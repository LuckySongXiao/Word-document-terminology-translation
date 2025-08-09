#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档术语翻译助手 - Web启动器
自动启动Web版本，无需手动选择模式
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import webbrowser
import logging
import socket
import os
from pathlib import Path
import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class LauncherApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("文档术语翻译助手 - Web启动器")
        self.root.geometry("750x600")
        self.root.resizable(True, True)
        self.root.minsize(650, 500)

        # 设置图标
        try:
            icon_path = Path(__file__).parent / "logo.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass

        # 初始化状态变量
        self.web_process = None
        self.server_port = 8000
        self.server_running = False
        self.web_thread = None

        self.setup_ui()
        self.center_window()

        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 自动启动Web服务
        self.root.after(1000, self.auto_launch_web)

    def center_window(self):
        """窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_ui(self):
        """设置用户界面"""
        # 主标题
        title_frame = tk.Frame(self.root)
        title_frame.pack(pady=20)

        title_label = tk.Label(
            title_frame,
            text="文档术语翻译助手",
            font=("微软雅黑", 18, "bold"),
            fg="#2c3e50"
        )
        title_label.pack()

        subtitle_label = tk.Label(
            title_frame,
            text="Web版 - 支持Word、PDF、EXCEL、TXT等多种格式的专业翻译工具",
            font=("微软雅黑", 10),
            fg="#7f8c8d"
        )
        subtitle_label.pack(pady=(5, 0))

        # 分隔线
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill='x', padx=20, pady=15)

        # 启动信息
        info_frame = tk.Frame(self.root)
        info_frame.pack(pady=10)

        info_label = tk.Label(
            info_frame,
            text="正在自动启动Web服务器，请稍候...",
            font=("微软雅黑", 12),
            fg="#27ae60"
        )
        info_label.pack()

        desc_label = tk.Label(
            info_frame,
            text="启动完成后将自动打开浏览器，支持局域网访问",
            font=("微软雅黑", 9),
            fg="#7f8c8d"
        )
        desc_label.pack(pady=(5, 0))

        # 状态显示
        self.status_frame = tk.Frame(self.root)
        self.status_frame.pack(pady=15, padx=20, fill='x')

        self.status_label = tk.Label(
            self.status_frame,
            text="准备启动Web服务器...",
            font=("微软雅黑", 10),
            fg="#2c3e50"
        )
        self.status_label.pack()

        # 进度条
        self.progress = ttk.Progressbar(
            self.status_frame,
            mode='indeterminate'
        )

        # 控制按钮区域
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10, padx=20, fill='x')

        # 左侧按钮组
        left_buttons = tk.Frame(control_frame)
        left_buttons.pack(side='left')

        self.restart_btn = tk.Button(
            left_buttons,
            text="重启服务器",
            command=self.restart_server,
            font=("微软雅黑", 9),
            bg="#3498db",
            fg="white",
            relief="flat",
            padx=15,
            state=tk.DISABLED
        )
        self.restart_btn.pack(side='left', padx=(0, 10))

        self.stop_btn = tk.Button(
            left_buttons,
            text="停止服务器",
            command=self.stop_server,
            font=("微软雅黑", 9),
            bg="#e74c3c",
            fg="white",
            relief="flat",
            padx=15,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side='left', padx=(0, 10))

        self.browser_btn = tk.Button(
            left_buttons,
            text="打开浏览器",
            command=self.open_browser_manual,
            font=("微软雅黑", 9),
            bg="#27ae60",
            fg="white",
            relief="flat",
            padx=15,
            state=tk.DISABLED
        )
        self.browser_btn.pack(side='left', padx=(0, 10))

        # 右侧按钮组
        right_buttons = tk.Frame(control_frame)
        right_buttons.pack(side='right')

        self.clear_log_btn = tk.Button(
            right_buttons,
            text="清空日志",
            command=self.clear_logs,
            font=("微软雅黑", 9),
            bg="#95a5a6",
            fg="white",
            relief="flat",
            padx=15
        )
        self.clear_log_btn.pack(side='right')

        # 终端信息显示区域
        terminal_frame = tk.LabelFrame(self.root, text="系统日志 - 实时显示后台信息", font=("微软雅黑", 9))
        terminal_frame.pack(pady=10, padx=20, fill='both', expand=True)

        # 创建文本框和滚动条
        self.terminal_text = tk.Text(
            terminal_frame,
            height=12,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#ffffff",
            wrap=tk.WORD,
            state=tk.DISABLED
        )

        terminal_scrollbar = ttk.Scrollbar(terminal_frame, orient="vertical", command=self.terminal_text.yview)
        self.terminal_text.configure(yscrollcommand=terminal_scrollbar.set)

        self.terminal_text.pack(side="left", fill="both", expand=True)
        terminal_scrollbar.pack(side="right", fill="y")

        # 底部信息
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(side='bottom', pady=10)

        version_label = tk.Label(
            bottom_frame,
            text="版本 3.0 | 支持智谱AI、Ollama、硅基流动等多种翻译引擎",
            font=("微软雅黑", 8),
            fg="#95a5a6"
        )
        version_label.pack()

        # 初始化日志
        self.log_message("Web启动器已就绪，即将自动启动服务器...")

    def clear_logs(self):
        """清空日志"""
        self.terminal_text.config(state=tk.NORMAL)
        self.terminal_text.delete(1.0, tk.END)
        self.terminal_text.config(state=tk.DISABLED)
        self.log_message("日志已清空", "INFO")

    def restart_server(self):
        """重启服务器"""
        self.log_message("正在重启服务器...", "INFO")
        self.stop_server()
        # 等待一秒后重新启动
        self.root.after(1000, self.auto_launch_web)

    def stop_server(self):
        """停止服务器"""
        self.log_message("正在停止服务器...", "INFO")

        # 停止子进程
        if self.web_process and self.web_process.poll() is None:
            try:
                self.web_process.terminate()
                self.log_message("Web服务器进程已终止", "INFO")
            except Exception as e:
                self.log_message(f"终止进程失败: {e}", "WARNING")
                try:
                    self.web_process.kill()
                    self.log_message("Web服务器进程已强制终止", "WARNING")
                except Exception as e2:
                    self.log_message(f"强制终止进程失败: {e2}", "ERROR")

        # 更新状态
        self.server_running = False
        self.web_process = None
        self.update_button_states()
        self.update_status("服务器已停止")

    def open_browser_manual(self):
        """手动打开浏览器"""
        if self.server_running:
            url = f"http://localhost:{self.server_port}"
            try:
                webbrowser.open(url)
                self.log_message(f"浏览器已打开: {url}", "SUCCESS")
            except Exception as e:
                self.log_message(f"打开浏览器失败: {e}", "ERROR")
        else:
            self.log_message("服务器未运行，无法打开浏览器", "WARNING")

    def update_button_states(self):
        """更新按钮状态"""
        if self.server_running:
            self.restart_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.NORMAL)
            self.browser_btn.config(state=tk.NORMAL)
        else:
            self.restart_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            self.browser_btn.config(state=tk.DISABLED)

    def on_closing(self):
        """窗口关闭事件处理"""
        if messagebox.askokcancel("退出", "确定要退出启动器吗？\n这将同时停止Web服务器。"):
            self.stop_server()
            self.root.destroy()

    def log_message(self, message, level="INFO"):
        """添加日志消息到终端显示区域"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # 根据日志级别设置颜色
        color_map = {
            "INFO": "#ffffff",
            "SUCCESS": "#00ff00",
            "WARNING": "#ffff00",
            "ERROR": "#ff0000",
            "DEBUG": "#888888"
        }
        color = color_map.get(level, "#ffffff")

        # 启用文本框编辑
        self.terminal_text.config(state=tk.NORMAL)

        # 插入消息
        log_line = f"[{timestamp}] {level}: {message}\n"
        self.terminal_text.insert(tk.END, log_line)

        # 设置颜色标签
        line_start = self.terminal_text.index(f"end-2l linestart")
        line_end = self.terminal_text.index(f"end-1l lineend")
        tag_name = f"color_{level}_{timestamp}"
        self.terminal_text.tag_add(tag_name, line_start, line_end)
        self.terminal_text.tag_config(tag_name, foreground=color)

        # 自动滚动到底部
        self.terminal_text.see(tk.END)

        # 禁用文本框编辑
        self.terminal_text.config(state=tk.DISABLED)

        # 更新界面
        self.root.update()

    def update_status(self, message, show_progress=False):
        """更新状态显示"""
        self.status_label.config(text=message)
        self.log_message(message)

        if show_progress:
            self.progress.pack(pady=(10, 0), fill='x')
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.pack_forget()
        self.root.update()

    def auto_launch_web(self):
        """自动启动Web版本"""
        self.update_status("正在自动启动Web服务器...", True)
        self.log_message("开始自动启动Web服务器", "INFO")

        # 直接调用Web启动逻辑
        self.launch_web()

    def _find_web_server_script(self):
        """查找web_server.py脚本文件（仅用于源码环境）"""
        # 获取当前执行文件的目录
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe文件，直接返回None，使用内嵌模式
            self.log_message("检测到单文件打包环境，将使用内嵌Web服务器", "INFO")
            return "embedded"
        else:
            # 如果是源码运行
            app_dir = Path(__file__).parent
            possible_paths = [
                app_dir / "web_server.py",
                app_dir / "_internal" / "web_server.py",
                app_dir / "src" / "web_server.py"
            ]

            self.log_message(f"搜索目录: {app_dir}", "INFO")

            for path in possible_paths:
                self.log_message(f"检查路径: {path}", "DEBUG")
                if path.exists():
                    logger.info(f"找到web_server.py: {path}")
                    self.log_message(f"找到web_server.py: {path}", "SUCCESS")
                    return path

            logger.error("未找到web_server.py文件")
            self.log_message("未找到web_server.py文件", "ERROR")
            self.log_message(f"已检查的路径: {[str(p) for p in possible_paths]}", "ERROR")
            return None



    def launch_web(self):
        """启动Web版本"""
        self.update_status("正在启动Web版...", True)

        def run_web():
            try:
                # 检查运行环境
                if getattr(sys, 'frozen', False):
                    # 单文件打包环境，直接使用内嵌方式启动
                    self.root.after(0, lambda: self.log_message("检测到单文件打包环境，使用内嵌Web服务器", "INFO"))
                    web_server_path = "embedded"
                else:
                    # 源码环境，查找web_server.py文件
                    self.root.after(0, lambda: self.log_message("正在查找web_server.py文件...", "INFO"))
                    web_server_path = self._find_web_server_script()
                    if not web_server_path:
                        self.root.after(0, lambda: self.log_message("未找到web_server.py文件", "ERROR"))
                        raise FileNotFoundError("未找到web_server.py文件")
                    self.root.after(0, lambda wsp=web_server_path: self.log_message(f"找到web_server.py: {wsp}", "SUCCESS"))

                self.root.after(0, lambda: self.update_status("正在检查端口..."))

                # 检查端口是否被占用
                port = 8000
                original_port = port
                while self.is_port_in_use(port) and port < 8010:
                    self.root.after(0, lambda p=port: self.log_message(f"端口 {p} 被占用，尝试下一个端口", "WARNING"))
                    port += 1

                if port != original_port:
                    self.root.after(0, lambda p=port: self.log_message(f"使用端口: {p}", "INFO"))
                else:
                    self.root.after(0, lambda p=port: self.log_message(f"端口 {p} 可用", "INFO"))

                # 设置工作目录
                if web_server_path == "embedded":
                    # 单文件版本，使用可执行文件所在目录
                    work_dir = str(Path(sys.executable).parent)
                else:
                    # 源码版本，使用web_server.py所在目录
                    work_dir = str(web_server_path.parent)

                self.root.after(0, lambda wd=work_dir: self.log_message(f"工作目录: {wd}", "INFO"))

                # 检查运行环境并选择启动方式
                self.root.after(0, lambda p=port: self.update_status(f"正在启动Web服务器 (端口:{p})..."))

                if web_server_path == "embedded":
                    # 单文件打包环境，使用内嵌方式启动Web服务器
                    self.root.after(0, lambda: self.log_message("使用内嵌方式启动Web服务器", "INFO"))
                    self._start_embedded_server(port, work_dir)
                else:
                    # 源码环境，使用子进程启动
                    self.root.after(0, lambda: self.log_message("检测到源码环境，使用子进程启动Web服务器", "INFO"))
                    self._start_subprocess_server(port, web_server_path)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"启动Web版本失败: {error_msg}")
                self.root.after(0, lambda em=error_msg: self.log_message(f"Web启动失败: {em}", "ERROR"))
                self.root.after(0, lambda em=error_msg: self.show_error(f"启动Web版失败: {em}"))

        threading.Thread(target=run_web, daemon=True).start()

    def _start_embedded_server(self, port, work_dir):
        """在打包环境中启动内嵌Web服务器"""
        try:
            # 设置工作目录
            original_cwd = os.getcwd()
            os.chdir(work_dir)
            self.root.after(0, lambda: self.log_message(f"切换工作目录到: {work_dir}", "INFO"))

            # 启动Web服务器线程
            def start_server(server_port):
                try:
                    # 导入并启动web服务器
                    import uvicorn
                    from web.api import app
                    from utils.terminology import load_terminology
                    from services.translator import TranslationService

                    self.root.after(0, lambda: self.log_message("正在初始化翻译服务...", "INFO"))

                    # 初始化翻译服务
                    try:
                        translator = TranslationService()
                        from web.api import set_translator_instance
                        set_translator_instance(translator)
                        self.root.after(0, lambda: self.log_message("翻译服务初始化成功", "SUCCESS"))
                    except Exception as e:
                        self.root.after(0, lambda err=e: self.log_message(f"翻译服务初始化失败: {err}", "WARNING"))

                    # 加载术语库
                    try:
                        terminology = load_terminology()
                        if terminology:
                            languages = list(terminology.keys())
                            self.root.after(0, lambda lang_count=len(languages): self.log_message(f"成功加载术语库，包含 {lang_count} 种语言", "SUCCESS"))
                        else:
                            self.root.after(0, lambda: self.log_message("术语库为空", "WARNING"))
                    except Exception as e:
                        self.root.after(0, lambda err=e: self.log_message(f"加载术语库失败: {err}", "WARNING"))

                    self.root.after(0, lambda p=server_port: self.log_message(f"启动Web服务器，地址: http://0.0.0.0:{p}", "INFO"))

                    # 启动uvicorn服务器 - 使用简化配置
                    self.root.after(0, lambda: self.log_message("Web服务器配置完成，正在启动...", "INFO"))

                    # 在启动前再次检查端口，确保可用
                    current_port = server_port
                    if self.is_port_in_use(current_port):
                        # 如果端口被占用，尝试下一个端口
                        original_port = current_port
                        while self.is_port_in_use(current_port) and current_port < 8020:
                            current_port += 1

                        if current_port != original_port:
                            self.root.after(0, lambda orig=original_port, curr=current_port: self.log_message(f"端口 {orig} 被占用，改用端口 {curr}", "WARNING"))

                        if current_port >= 8020:
                            raise Exception("无法找到可用端口（8000-8019都被占用）")

                    try:
                        # 方法1: 使用uvicorn.run直接启动（最简单可靠）
                        self.root.after(0, lambda: self.log_message("使用uvicorn.run启动服务器...", "INFO"))
                        uvicorn.run(
                            app,
                            host="0.0.0.0",
                            port=current_port,
                            log_level="error",
                            access_log=False,
                            loop="asyncio"
                        )
                    except Exception as e:
                        self.root.after(0, lambda err=e: self.log_message(f"uvicorn.run启动失败: {err}", "WARNING"))

                        # 方法2: 使用Server类启动
                        try:
                            self.root.after(0, lambda: self.log_message("尝试使用Server类启动...", "INFO"))
                            config = uvicorn.Config(
                                app,
                                host="0.0.0.0",
                                port=current_port,
                                log_level="error",
                                access_log=False,
                                log_config=None  # 避免日志配置冲突
                            )
                            server = uvicorn.Server(config)
                            server.run()
                        except Exception as e2:
                            self.root.after(0, lambda err=e2: self.log_message(f"Server类启动也失败: {err}", "ERROR"))
                            raise e2

                except Exception as e:
                    self.root.after(0, lambda err=e: self.log_message(f"内嵌Web服务器启动失败: {err}", "ERROR"))
                    raise
                finally:
                    # 恢复原工作目录
                    os.chdir(original_cwd)

            # 在新线程中启动Web服务器
            web_thread = threading.Thread(target=lambda: start_server(port), daemon=True)
            web_thread.start()

            # 等待服务器启动并打开浏览器
            self._wait_and_open_browser(port)

        except Exception as e:
            self.root.after(0, lambda err=e: self.log_message(f"启动内嵌服务器失败: {err}", "ERROR"))
            self.root.after(0, lambda err=e: self.show_error(f"启动Web服务器失败: {err}"))

    def _wait_and_open_browser(self, port):
        """等待服务器启动并打开浏览器"""
        def wait_and_open():
            try:
                # 等待服务器启动
                self.root.after(0, lambda: self.update_status("正在等待服务器启动..."))

                # 检查服务器是否启动成功
                max_attempts = 30  # 等待30秒
                server_started = False

                for attempt in range(max_attempts):
                    time.sleep(1)
                    self.root.after(0, lambda a=attempt: self.update_status(f"正在等待服务器启动... ({a+1}/{max_attempts})"))
                    self.root.after(0, lambda a=attempt: self.log_message(f"检查服务器状态... ({a+1}/{max_attempts})", "INFO"))

                    # 检查端口是否可访问
                    if self.check_server_running(port):
                        self.root.after(0, lambda p=port: self.log_message(f"服务器在端口 {p} 启动成功", "SUCCESS"))
                        server_started = True
                        break

                    # 在第10次尝试后，给出更详细的状态信息
                    if attempt == 9:
                        self.root.after(0, lambda: self.log_message("服务器启动时间较长，请耐心等待...", "INFO"))
                    elif attempt == 19:
                        self.root.after(0, lambda: self.log_message("服务器仍在启动中，可能需要更多时间...", "WARNING"))

                if not server_started:
                    self.root.after(0, lambda: self.log_message("服务器启动超时，但可能仍在后台运行", "WARNING"))
                    self.root.after(0, lambda: self.log_message("尝试打开浏览器，如果页面无法访问请稍后重试", "INFO"))

                self.root.after(0, lambda: self.update_status("正在打开浏览器..."))
                time.sleep(1)

                # 打开浏览器
                url = f"http://localhost:{port}"
                self.root.after(0, lambda u=url: self.log_message(f"本机访问地址: {u}", "INFO"))

                # 获取本机IP地址用于局域网访问提示
                local_ip = self.get_local_ip()
                lan_url = f"http://{local_ip}:{port}" if local_ip else ""

                if lan_url:
                    self.root.after(0, lambda lu=lan_url: self.log_message(f"局域网访问地址: {lu}", "INFO"))

                # 打开浏览器
                try:
                    webbrowser.open(url)
                    self.root.after(0, lambda u=url: self.log_message(f"浏览器已打开: {u}", "SUCCESS"))
                except Exception as e:
                    self.root.after(0, lambda err=e: self.log_message(f"自动打开浏览器失败: {err}", "WARNING"))
                    self.root.after(0, lambda u=url: self.log_message(f"请手动访问: {u}", "INFO"))

                status_msg = "Web版已启动" if server_started else "Web版启动中"
                self.root.after(0, lambda: self.log_message("Web版启动完成！", "SUCCESS"))
                self.root.after(0, lambda: self.update_status(status_msg))

                # 更新服务器状态和按钮
                if server_started:
                    self.server_running = True
                    self.server_port = port
                    self.root.after(0, self.update_button_states)

                self.root.after(0, lambda u=url, lu=lan_url, ss=server_started: self.show_success_info_no_close(u, lu, ss))

            except Exception as e:
                self.root.after(0, lambda err=e: self.log_message(f"等待服务器启动失败: {err}", "ERROR"))
                self.root.after(0, lambda err=e: self.show_error(f"启动失败: {err}"))

        threading.Thread(target=wait_and_open, daemon=True).start()

    def _start_subprocess_server(self, port, web_server_path):
        """在源码环境中使用子进程启动Web服务器"""
        try:
            # 构建启动命令
            cmd = [sys.executable, str(web_server_path), '--host', '0.0.0.0', '--port', str(port)]
            work_dir = str(Path(__file__).parent)

            self.root.after(0, lambda c=cmd: self.log_message(f"启动命令: {' '.join(c)}", "DEBUG"))
            self.root.after(0, lambda wd=work_dir: self.log_message(f"工作目录: {wd}", "DEBUG"))

            # 启动子进程
            if sys.platform == "win32":
                # 在Windows上不显示控制台窗口
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

                process = subprocess.Popen(
                    cmd,
                    cwd=work_dir,
                    startupinfo=startupinfo,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
            else:
                process = subprocess.Popen(
                    cmd,
                    cwd=work_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

            self.root.after(0, lambda pid=process.pid: self.log_message(f"Web服务器进程已启动 (PID: {pid})", "SUCCESS"))

            # 启动线程读取进程输出
            def read_output():
                try:
                    while True:
                        output = process.stdout.readline()
                        if output == '' and process.poll() is not None:
                            break
                        if output:
                            output_msg = output.strip()
                            if output_msg:  # 只显示非空消息
                                # 根据消息内容判断日志级别
                                if "ERROR" in output_msg.upper() or "FAILED" in output_msg.upper():
                                    level = "ERROR"
                                elif "WARNING" in output_msg.upper() or "WARN" in output_msg.upper():
                                    level = "WARNING"
                                elif "SUCCESS" in output_msg.upper() or "成功" in output_msg:
                                    level = "SUCCESS"
                                else:
                                    level = "INFO"
                                self.root.after(0, lambda msg=output_msg, lvl=level: self.log_message(f"服务器: {msg}", lvl))
                except Exception as e:
                    self.root.after(0, lambda err=e: self.log_message(f"读取服务器输出失败: {err}", "WARNING"))

            def read_error():
                try:
                    while True:
                        error = process.stderr.readline()
                        if error == '' and process.poll() is not None:
                            break
                        if error:
                            error_msg = error.strip()
                            if error_msg:  # 只显示非空消息
                                # 根据错误消息内容判断级别
                                if "CRITICAL" in error_msg.upper() or "FATAL" in error_msg.upper():
                                    level = "ERROR"
                                elif "WARNING" in error_msg.upper() or "WARN" in error_msg.upper():
                                    level = "WARNING"
                                else:
                                    level = "ERROR"  # 默认错误级别
                                self.root.after(0, lambda msg=error_msg, lvl=level: self.log_message(f"服务器错误: {msg}", lvl))
                except Exception as e:
                    self.root.after(0, lambda err=e: self.log_message(f"读取服务器错误输出失败: {err}", "WARNING"))

            # 启动输出读取线程
            threading.Thread(target=read_output, daemon=True).start()
            threading.Thread(target=read_error, daemon=True).start()

            # 等待服务器启动并打开浏览器
            self._wait_subprocess_and_open_browser(port, process)

        except Exception as e:
            self.root.after(0, lambda err=e: self.log_message(f"启动子进程服务器失败: {err}", "ERROR"))
            self.root.after(0, lambda err=e: self.show_error(f"启动Web服务器失败: {err}"))

    def _wait_subprocess_and_open_browser(self, port, process):
        """等待子进程服务器启动并打开浏览器"""
        def wait_and_open():
            try:
                # 等待服务器启动
                self.root.after(0, lambda: self.update_status("正在等待服务器启动..."))

                # 检查服务器是否启动成功
                max_attempts = 30  # 等待30秒
                server_started = False

                for attempt in range(max_attempts):
                    time.sleep(1)
                    self.root.after(0, lambda a=attempt: self.update_status(f"正在等待服务器启动... ({a+1}/{max_attempts})"))
                    self.root.after(0, lambda a=attempt: self.log_message(f"检查服务器状态... ({a+1}/{max_attempts})", "INFO"))

                    # 检查进程是否还在运行
                    if process.poll() is not None:
                        self.root.after(0, lambda rc=process.returncode: self.log_message(f"Web服务器进程已退出，退出码: {rc}", "ERROR"))
                        break

                    # 检查端口是否可访问
                    if self.check_server_running(port):
                        self.root.after(0, lambda p=port: self.log_message(f"服务器在端口 {p} 启动成功", "SUCCESS"))
                        server_started = True
                        break

                    # 在第10次尝试后，给出更详细的状态信息
                    if attempt == 9:
                        self.root.after(0, lambda: self.log_message("服务器启动时间较长，请耐心等待...", "INFO"))
                    elif attempt == 19:
                        self.root.after(0, lambda: self.log_message("服务器仍在启动中，可能需要更多时间...", "WARNING"))

                if not server_started:
                    if process.poll() is None:
                        self.root.after(0, lambda: self.log_message("服务器启动超时，但进程仍在运行", "WARNING"))
                        self.root.after(0, lambda: self.log_message("尝试打开浏览器，如果页面无法访问请稍后重试", "INFO"))
                    else:
                        self.root.after(0, lambda: self.log_message("服务器进程已退出，启动失败", "ERROR"))
                        raise Exception("Web服务器启动失败")

                self.root.after(0, lambda: self.update_status("正在打开浏览器..."))
                time.sleep(1)

                # 打开浏览器
                url = f"http://localhost:{port}"
                self.root.after(0, lambda u=url: self.log_message(f"本机访问地址: {u}", "INFO"))

                # 获取本机IP地址用于局域网访问提示
                local_ip = self.get_local_ip()
                lan_url = f"http://{local_ip}:{port}" if local_ip else ""

                if lan_url:
                    self.root.after(0, lambda lu=lan_url: self.log_message(f"局域网访问地址: {lu}", "INFO"))

                # 打开浏览器
                try:
                    webbrowser.open(url)
                    self.root.after(0, lambda u=url: self.log_message(f"浏览器已打开: {u}", "SUCCESS"))
                except Exception as e:
                    self.root.after(0, lambda err=e: self.log_message(f"自动打开浏览器失败: {err}", "WARNING"))
                    self.root.after(0, lambda u=url: self.log_message(f"请手动访问: {u}", "INFO"))

                status_msg = "Web版已启动" if server_started else "Web版启动中"
                self.root.after(0, lambda: self.log_message("Web版启动完成！", "SUCCESS"))
                self.root.after(0, lambda: self.update_status(status_msg))

                # 更新服务器状态和按钮
                if server_started:
                    self.server_running = True
                    self.server_port = port
                    self.web_process = process
                    self.root.after(0, self.update_button_states)

                self.root.after(0, lambda u=url, lu=lan_url, ss=server_started: self.show_success_info_no_close(u, lu, ss))

            except Exception as e:
                self.root.after(0, lambda err=e: self.log_message(f"等待子进程服务器启动失败: {err}", "ERROR"))
                self.root.after(0, lambda err=e: self.show_error(f"启动失败: {err}"))

        threading.Thread(target=wait_and_open, daemon=True).start()

    def is_port_in_use(self, port):
        """检查端口是否被占用"""
        # 检查多个地址，确保端口真正可用
        addresses = [('localhost', port), ('127.0.0.1', port), ('0.0.0.0', port)]

        for addr in addresses:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(addr)
            except OSError:
                return True
        return False

    def check_server_running(self, port):
        """检查服务器是否运行"""
        try:
            # 方法1: 使用socket连接检查（最可靠）
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)

                # 检查localhost
                try:
                    result = s.connect_ex(('localhost', port))
                    if result == 0:
                        self.root.after(0, lambda p=port: self.log_message(f"Socket检测成功: localhost:{p}", "DEBUG"))
                        return True
                except:
                    pass

                # 检查127.0.0.1
                try:
                    result2 = s.connect_ex(('127.0.0.1', port))
                    if result2 == 0:
                        self.root.after(0, lambda p=port: self.log_message(f"Socket检测成功: 127.0.0.1:{p}", "DEBUG"))
                        return True
                except:
                    pass

                # 检查0.0.0.0（通过本机IP）
                try:
                    local_ip = self.get_local_ip()
                    if local_ip:
                        result3 = s.connect_ex((local_ip, port))
                        if result3 == 0:
                            self.root.after(0, lambda ip=local_ip, p=port: self.log_message(f"Socket检测成功: {ip}:{p}", "DEBUG"))
                            return True
                except:
                    pass

            # 方法2: 使用HTTP请求检查
            try:
                import requests
                response = requests.get(f"http://localhost:{port}", timeout=2)
                if response.status_code in [200, 404, 422]:  # 422也可能是正常的FastAPI响应
                    self.root.after(0, lambda sc=response.status_code: self.log_message(f"HTTP检测成功: {sc}", "DEBUG"))
                    return True
            except requests.exceptions.RequestException as e:
                self.root.after(0, lambda err=e: self.log_message(f"HTTP检测失败: {err}", "DEBUG"))
                pass
            except ImportError:
                # 如果requests不可用，跳过HTTP检查
                pass

            return False
        except Exception as e:
            self.root.after(0, lambda err=e: self.log_message(f"端口检查异常: {err}", "DEBUG"))
            return False

    def get_local_ip(self):
        """获取本机IP地址"""
        try:
            # 连接到一个不存在的地址来获取本机IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return None

    def show_success_info_no_close(self, local_url, lan_url, server_confirmed=True):
        """显示启动成功信息（不自动关闭启动器）"""
        if server_confirmed:
            message = f"Web服务器启动成功！\n\n"
        else:
            message = f"Web服务器正在启动中...\n\n"

        message += f"本机访问地址：\n{local_url}\n\n"
        if lan_url:
            message += f"局域网访问地址：\n{lan_url}\n\n"

        if server_confirmed:
            message += "浏览器已自动打开，如未打开请手动访问上述地址。\n\n"
        else:
            message += "浏览器已打开，如果页面暂时无法访问，请稍等片刻后刷新。\n\n"

        message += "启动器将保持运行，您可以通过控制按钮管理服务器。\n"
        message += "关闭启动器窗口将同时停止Web服务器。"

        title = "启动成功" if server_confirmed else "启动中"
        messagebox.showinfo(title, message)

    def show_success_info(self, local_url, lan_url, server_confirmed=True):
        """显示启动成功信息（保留原方法以兼容）"""
        if server_confirmed:
            message = f"Web服务器启动成功！\n\n"
        else:
            message = f"Web服务器正在启动中...\n\n"

        message += f"本机访问地址：\n{local_url}\n\n"
        if lan_url:
            message += f"局域网访问地址：\n{lan_url}\n\n"

        if server_confirmed:
            message += "浏览器已自动打开，如未打开请手动访问上述地址。\n\n"
        else:
            message += "浏览器已打开，如果页面暂时无法访问，请稍等片刻后刷新。\n\n"

        message += "启动器将在5秒后自动关闭。"

        title = "启动成功" if server_confirmed else "启动中"
        messagebox.showinfo(title, message)

        # 延迟关闭启动器
        self.root.after(5000, self.root.quit)

    def show_error(self, message):
        """显示错误信息"""
        self.update_status("启动失败")
        messagebox.showerror("错误", message)

    def run(self):
        """运行启动器"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("用户中断启动器")
        except Exception as e:
            logger.error(f"启动器运行错误: {e}")
            messagebox.showerror("错误", f"启动器运行错误: {str(e)}")

def main():
    """主函数"""
    logger.info("启动文档术语翻译助手启动器")

    # 检查Python版本
    if sys.version_info < (3, 8):
        messagebox.showerror("错误", "需要Python 3.8或更高版本")
        return

    # 创建并运行启动器
    app = LauncherApp()
    app.run()

if __name__ == "__main__":
    main()
