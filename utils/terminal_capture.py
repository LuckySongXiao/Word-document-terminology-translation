#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终端输出捕获模块
用于将所有终端输出（print、日志等）重定向到PC端GUI和WEB端的日志显示区域
"""

import sys
import io
import threading
import logging
import time
from datetime import datetime
from queue import Queue, Empty
from typing import Optional, Callable, List
import traceback


class TerminalCapture:
    """终端输出捕获器"""
    
    def __init__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.captured_output = io.StringIO()
        self.output_queue = Queue()
        self.callbacks = []  # 输出回调函数列表
        self.is_capturing = False
        self.capture_thread = None
        self.lock = threading.Lock()
        
        # 创建自定义的输出流
        self.custom_stdout = self.CustomStream(self, 'stdout')
        self.custom_stderr = self.CustomStream(self, 'stderr')
        
    class CustomStream:
        """自定义输出流"""
        
        def __init__(self, capture_instance, stream_type):
            self.capture = capture_instance
            self.stream_type = stream_type
            self.original_stream = getattr(sys, stream_type)
            
        def write(self, text):
            # 写入原始流（保持终端输出）
            try:
                self.original_stream.write(text)
                self.original_stream.flush()
            except Exception:
                pass
                
            # 发送到捕获器
            if text.strip():  # 只处理非空内容
                self.capture._handle_output(text, self.stream_type)
                
        def flush(self):
            try:
                self.original_stream.flush()
            except Exception:
                pass
                
        def __getattr__(self, name):
            return getattr(self.original_stream, name)
    
    def _handle_output(self, text: str, stream_type: str):
        """处理输出内容"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 确定日志级别
            level = 'INFO'
            if stream_type == 'stderr' or any(keyword in text.upper() for keyword in ['ERROR', 'EXCEPTION', 'TRACEBACK']):
                level = 'ERROR'
            elif any(keyword in text.upper() for keyword in ['WARNING', 'WARN']):
                level = 'WARNING'
            elif any(keyword in text.upper() for keyword in ['DEBUG']):
                level = 'DEBUG'
                
            # 创建日志条目
            log_entry = {
                'timestamp': timestamp,
                'level': level,
                'message': text.strip(),
                'stream': stream_type,
                'raw': text
            }
            
            # 放入队列
            try:
                self.output_queue.put(log_entry, timeout=0.1)
            except Exception:
                pass
                
            # 调用回调函数
            with self.lock:
                for callback in self.callbacks:
                    try:
                        callback(log_entry)
                    except Exception:
                        pass
                        
        except Exception:
            pass
    
    def add_callback(self, callback: Callable):
        """添加输出回调函数"""
        with self.lock:
            if callback not in self.callbacks:
                self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """移除输出回调函数"""
        with self.lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
    
    def start_capture(self):
        """开始捕获终端输出"""
        if not self.is_capturing:
            self.is_capturing = True
            
            # 替换标准输出流
            sys.stdout = self.custom_stdout
            sys.stderr = self.custom_stderr
            
            # 启动处理线程
            self.capture_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.capture_thread.start()
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO - 终端输出捕获已启动")
    
    def stop_capture(self):
        """停止捕获终端输出"""
        if self.is_capturing:
            self.is_capturing = False
            
            # 恢复原始输出流
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO - 终端输出捕获已停止")
    
    def _process_queue(self):
        """处理输出队列"""
        while self.is_capturing:
            try:
                # 批量处理队列中的消息
                messages = []
                try:
                    # 获取第一条消息（阻塞等待）
                    message = self.output_queue.get(timeout=1.0)
                    messages.append(message)
                    
                    # 获取更多消息（非阻塞）
                    while len(messages) < 10:  # 限制批量大小
                        try:
                            message = self.output_queue.get_nowait()
                            messages.append(message)
                        except Empty:
                            break
                            
                except Empty:
                    continue
                    
                # 处理消息批次
                if messages:
                    self._process_message_batch(messages)
                    
            except Exception:
                time.sleep(0.1)
    
    def _process_message_batch(self, messages: List[dict]):
        """处理消息批次"""
        try:
            # 这里可以添加批量处理逻辑
            # 目前主要通过回调函数处理
            pass
        except Exception:
            pass
    
    def get_recent_output(self, count: int = 100) -> List[dict]:
        """获取最近的输出"""
        messages = []
        try:
            while len(messages) < count:
                try:
                    message = self.output_queue.get_nowait()
                    messages.append(message)
                except Empty:
                    break
        except Exception:
            pass
        return messages


class TerminalLogger:
    """终端日志记录器"""
    
    def __init__(self, capture_instance: TerminalCapture):
        self.capture = capture_instance
        self.logger = logging.getLogger('terminal_capture')
        self.logger.setLevel(logging.INFO)
        
        # 创建自定义处理器
        self.handler = self.TerminalHandler(capture_instance)
        self.handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        
        self.logger.addHandler(self.handler)
    
    class TerminalHandler(logging.Handler):
        """自定义日志处理器"""
        
        def __init__(self, capture_instance):
            super().__init__()
            self.capture = capture_instance
            
        def emit(self, record):
            try:
                msg = self.format(record)
                # 通过捕获器处理日志
                self.capture._handle_output(msg, 'log')
            except Exception:
                self.handleError(record)


# 全局终端捕获实例
_global_capture = None


def get_terminal_capture() -> TerminalCapture:
    """获取全局终端捕获实例"""
    global _global_capture
    if _global_capture is None:
        _global_capture = TerminalCapture()
    return _global_capture


def start_terminal_capture():
    """启动全局终端捕获"""
    capture = get_terminal_capture()
    capture.start_capture()
    return capture


def stop_terminal_capture():
    """停止全局终端捕获"""
    global _global_capture
    if _global_capture:
        _global_capture.stop_capture()


def add_output_callback(callback: Callable):
    """添加输出回调函数"""
    capture = get_terminal_capture()
    capture.add_callback(callback)


def remove_output_callback(callback: Callable):
    """移除输出回调函数"""
    capture = get_terminal_capture()
    capture.remove_callback(callback)


if __name__ == "__main__":
    # 测试代码
    def test_callback(log_entry):
        print(f"捕获到输出: {log_entry}")
    
    capture = start_terminal_capture()
    add_output_callback(test_callback)
    
    print("这是一条测试消息")
    print("这是另一条测试消息", file=sys.stderr)
    
    time.sleep(2)
    stop_terminal_capture()
