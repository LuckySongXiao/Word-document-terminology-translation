#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速修复端口冲突和Web资源路径问题
"""

import os
import sys
import shutil
from pathlib import Path

def fix_launcher_port_check():
    """修复启动器的端口检查逻辑"""
    print("修复启动器端口检查逻辑...")
    
    launcher_files = [
        "launcher.py",
        "build_temp/launcher.py"
    ]
    
    for file_path in launcher_files:
        if not Path(file_path).exists():
            continue
            
        print(f"修复文件: {file_path}")
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复端口检查函数
        old_port_check = '''    def is_port_in_use(self, port):
        """检查端口是否被占用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return False
            except OSError:
                return True'''
        
        new_port_check = '''    def is_port_in_use(self, port):
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
        return False'''
        
        if old_port_check in content:
            content = content.replace(old_port_check, new_port_check)
            print(f"  ✓ 已修复端口检查函数")
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

def fix_web_resources():
    """修复Web资源路径查找"""
    print("修复Web资源路径查找...")
    
    api_files = [
        "web/api.py",
        "build_temp/web/api.py"
    ]
    
    for file_path in api_files:
        if not Path(file_path).exists():
            continue
            
        print(f"修复文件: {file_path}")
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经包含新的资源查找逻辑
        if 'def find_web_resources():' in content and 'hasattr(sys, \'_MEIPASS\')' in content:
            print(f"  ✓ {file_path} 已包含修复的资源查找逻辑")
            continue
        
        # 如果是build_temp版本，需要替换简单的路径设置
        if 'build_temp' in file_path:
            old_logic = '''if getattr(sys, 'frozen', False):
    # 打包环境
    base_dir = Path(sys.executable).parent / "_internal"
else:
    # 源码环境
    base_dir = Path(__file__).parent.parent'''
            
            new_logic = '''def find_web_resources():
    """查找web资源目录"""
    possible_paths = []

    if getattr(sys, 'frozen', False):
        # 打包环境 - 尝试多个可能的路径
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller单文件模式
            meipass_dir = Path(sys._MEIPASS)
            possible_paths.extend([
                meipass_dir,
                meipass_dir / "web",
            ])
        
        # 可执行文件目录
        exe_dir = Path(sys.executable).parent
        possible_paths.extend([
            exe_dir / "_internal" / "web",
            exe_dir / "web",
            exe_dir / "_internal",
            exe_dir,
        ])
    else:
        # 源码环境
        current_dir = Path(__file__).parent.parent
        possible_paths.append(current_dir)

    # 查找包含web目录的路径
    for base_path in possible_paths:
        web_dir = base_path / "web"
        static_dir = web_dir / "static"
        templates_dir = web_dir / "templates"

        print(f"检查路径: {base_path}")
        print(f"  web目录: {web_dir} (存在: {web_dir.exists()})")
        print(f"  static目录: {static_dir} (存在: {static_dir.exists()})")
        print(f"  templates目录: {templates_dir} (存在: {templates_dir.exists()})")

        # 检查是否有必要的文件
        if templates_dir.exists() and (templates_dir / "index.html").exists():
            print(f"找到有效的web资源目录: {base_path}")
            return base_path

    # 如果都没找到，尝试使用PyInstaller的临时目录
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass_fallback = Path(sys._MEIPASS)
        print(f"未找到有效的web资源目录，使用PyInstaller临时目录: {meipass_fallback}")
        return meipass_fallback
    
    # 最后的后备选项
    fallback_dir = Path(__file__).parent.parent
    print(f"未找到有效的web资源目录，使用源码目录作为后备: {fallback_dir}")
    return fallback_dir

base_dir = find_web_resources()'''
            
            if old_logic in content:
                content = content.replace(old_logic, new_logic)
                print(f"  ✓ 已修复Web资源查找逻辑")
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

def create_emergency_launcher():
    """创建紧急启动器，绕过端口冲突问题"""
    print("创建紧急启动器...")
    
    emergency_launcher = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急启动器 - 绕过端口冲突问题
"""

import socket
import time
import webbrowser
import subprocess
import sys
from pathlib import Path

def find_available_port(start_port=8000, max_port=8020):
    """查找可用端口"""
    for port in range(start_port, max_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', port))
                print(f"找到可用端口: {port}")
                return port
        except OSError:
            print(f"端口 {port} 被占用")
            continue
    
    raise Exception(f"无法找到可用端口 ({start_port}-{max_port-1})")

def main():
    """主函数"""
    print("=" * 50)
    print("紧急启动器 - 多格式文档翻译助手")
    print("=" * 50)
    
    try:
        # 查找可用端口
        port = find_available_port()
        
        # 启动Web服务器
        print(f"启动Web服务器，端口: {port}")
        
        # 构建启动命令
        cmd = [sys.executable, "web_server.py", "--host", "0.0.0.0", "--port", str(port)]
        
        print(f"执行命令: {' '.join(cmd)}")
        
        # 启动服务器
        process = subprocess.Popen(cmd)
        
        # 等待服务器启动
        print("等待服务器启动...")
        time.sleep(3)
        
        # 打开浏览器
        url = f"http://localhost:{port}"
        print(f"打开浏览器: {url}")
        webbrowser.open(url)
        
        print("服务器已启动，按Ctrl+C停止")
        
        # 等待进程结束
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\\n正在停止服务器...")
            process.terminate()
            process.wait()
            print("服务器已停止")
    
    except Exception as e:
        print(f"启动失败: {e}")
        input("按回车键退出...")

if __name__ == "__main__":
    main()
'''
    
    with open("emergency_launcher.py", 'w', encoding='utf-8') as f:
        f.write(emergency_launcher)
    
    print("✓ 紧急启动器已创建: emergency_launcher.py")

def main():
    """主修复函数"""
    print("=" * 60)
    print("快速修复端口冲突和Web资源路径问题")
    print("=" * 60)
    
    try:
        # 修复启动器端口检查
        fix_launcher_port_check()
        
        # 修复Web资源路径
        fix_web_resources()
        
        # 创建紧急启动器
        create_emergency_launcher()
        
        print()
        print("=" * 60)
        print("修复完成！")
        print("=" * 60)
        print()
        print("修复内容:")
        print("1. ✓ 修复了启动器的端口检查逻辑")
        print("2. ✓ 修复了Web资源路径查找问题")
        print("3. ✓ 创建了紧急启动器")
        print()
        print("使用方法:")
        print("1. 重新运行封装后的启动器")
        print("2. 如果仍有问题，使用紧急启动器: python emergency_launcher.py")
        print()
        
    except Exception as e:
        print(f"修复过程中出现错误: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    input("按回车键退出...")
    sys.exit(0 if success else 1)
