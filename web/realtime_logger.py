#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web端实时日志监控模块
"""

import os
import json
import time
import threading
from datetime import datetime
import logging

class RealtimeLogMonitor:
    """实时日志监控器"""

    def __init__(self):
        self.realtime_log_file = 'realtime.log'
        self.last_position = 0
        self.log_buffer = []
        self.max_buffer_size = 1000
        self.lock = threading.Lock()
        self.monitoring = False
        self.monitor_thread = None

    def start_monitoring(self):
        """开始监控日志文件"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logging.info("实时日志监控已启动")

    def stop_monitoring(self):
        """停止监控日志文件"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        logging.info("实时日志监控已停止")

    def _monitor_loop(self):
        """监控循环"""
        while self.monitoring:
            try:
                self._read_new_logs()
                time.sleep(0.5)  # 每0.5秒检查一次
            except Exception as e:
                logging.error(f"日志监控出错: {e}")
                time.sleep(1)

    def _read_new_logs(self):
        """读取新的日志内容"""
        try:
            if not os.path.exists(self.realtime_log_file):
                return

            with open(self.realtime_log_file, 'r', encoding='utf-8') as f:
                # 移动到上次读取的位置
                f.seek(self.last_position)
                new_content = f.read()

                if new_content:
                    # 更新位置
                    self.last_position = f.tell()

                    # 处理新内容
                    lines = new_content.strip().split('\n')
                    for line in lines:
                        if line.strip():
                            self._add_log_entry(line)

        except Exception as e:
            logging.error(f"读取实时日志失败: {e}")

    def _add_log_entry(self, line):
        """添加日志条目"""
        try:
            # 解析日志行
            log_entry = self._parse_log_line(line)

            with self.lock:
                self.log_buffer.append(log_entry)

                # 保持缓冲区大小
                if len(self.log_buffer) > self.max_buffer_size:
                    self.log_buffer.pop(0)

        except Exception as e:
            logging.error(f"添加日志条目失败: {e}")

    def _parse_log_line(self, line):
        """解析日志行"""
        try:
            # 尝试解析标准格式: [timestamp] LEVEL module:func:line - message
            if line.startswith('[') and ']' in line:
                parts = line.split(']', 1)
                if len(parts) == 2:
                    timestamp_str = parts[0][1:]  # 移除开头的 [
                    rest = parts[1].strip()

                    # 解析级别和消息
                    if ' ' in rest:
                        level_and_location = rest.split(' - ', 1)
                        if len(level_and_location) == 2:
                            level_part = level_and_location[0].strip()
                            message = level_and_location[1]

                            # 解析级别和位置
                            level_parts = level_part.split(' ')
                            if len(level_parts) >= 2:
                                level = level_parts[0]
                                location = ' '.join(level_parts[1:])
                            else:
                                level = level_part
                                location = ''

                            return {
                                'timestamp': timestamp_str,
                                'level': level,
                                'location': location,
                                'message': message,
                                'raw': line
                            }

            # 如果解析失败，返回原始行
            return {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'location': '',
                'message': line,
                'raw': line
            }

        except Exception:
            # 解析失败时返回基本信息
            return {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'location': '',
                'message': line,
                'raw': line
            }

    def get_recent_logs(self, count=100):
        """获取最近的日志"""
        with self.lock:
            return self.log_buffer[-count:] if count > 0 else self.log_buffer[:]

    def get_logs_since(self, since_timestamp):
        """获取指定时间戳之后的日志"""
        try:
            since_time = datetime.fromisoformat(since_timestamp)
            with self.lock:
                filtered_logs = []
                for log in self.log_buffer:
                    try:
                        log_time = datetime.fromisoformat(log['timestamp'])
                        if log_time > since_time:
                            filtered_logs.append(log)
                    except Exception:
                        # 如果时间戳解析失败，包含这条日志
                        filtered_logs.append(log)
                return filtered_logs
        except Exception as e:
            logging.error(f"获取指定时间后的日志失败: {e}")
            return self.get_recent_logs(50)

    def get_exception_stats(self):
        """获取异常统计"""
        with self.lock:
            error_count = sum(1 for log in self.log_buffer if log['level'] == 'ERROR')
            warning_count = sum(1 for log in self.log_buffer if log['level'] == 'WARNING')

            # 查找最近的错误
            recent_errors = [log for log in self.log_buffer if log['level'] == 'ERROR']
            last_error_time = None
            if recent_errors:
                try:
                    last_error_time = recent_errors[-1]['timestamp']
                except Exception:
                    pass

            return {
                'error_count': error_count,
                'warning_count': warning_count,
                'last_error_time': last_error_time,
                'total_logs': len(self.log_buffer)
            }

    def clear_logs(self):
        """清空日志缓冲区"""
        with self.lock:
            self.log_buffer.clear()
        logging.info("日志缓冲区已清空")

# 全局实例
realtime_monitor = RealtimeLogMonitor()

# 启动监控
def start_realtime_monitoring():
    """启动实时监控"""
    realtime_monitor.start_monitoring()

def stop_realtime_monitoring():
    """停止实时监控"""
    realtime_monitor.stop_monitoring()
