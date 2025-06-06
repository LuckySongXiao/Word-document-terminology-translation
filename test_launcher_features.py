#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试启动器新功能
"""

import time
import subprocess
import sys
import os
from pathlib import Path

def test_launcher_features():
    """测试启动器的新功能"""
    print("=" * 60)
    print("测试启动器新功能")
    print("=" * 60)
    
    print("\n✅ 新功能列表:")
    print("1. 启动后不自动关闭")
    print("2. 实时显示后台终端信息")
    print("3. 添加控制按钮:")
    print("   - 重启服务器")
    print("   - 停止服务器")
    print("   - 打开浏览器")
    print("   - 清空日志")
    print("4. 改进的日志显示和颜色")
    print("5. 窗口关闭确认对话框")
    
    print("\n📋 测试说明:")
    print("1. 启动器会自动启动Web服务器")
    print("2. 启动成功后不会自动关闭")
    print("3. 可以通过控制按钮管理服务器")
    print("4. 实时显示服务器日志信息")
    print("5. 关闭窗口时会提示确认")
    
    print("\n🚀 启动测试...")
    
    # 检查launcher.py是否存在
    launcher_path = Path("launcher.py")
    if not launcher_path.exists():
        print("❌ 错误: 未找到launcher.py文件")
        return False
    
    print("✅ 找到launcher.py文件")
    
    # 启动launcher进行测试
    print("\n正在启动launcher进行功能测试...")
    print("请在启动器界面中测试以下功能:")
    print("1. 观察启动过程日志")
    print("2. 测试控制按钮")
    print("3. 验证不自动关闭")
    print("4. 检查实时日志显示")
    
    try:
        # 启动launcher
        process = subprocess.Popen(
            [sys.executable, "launcher.py"],
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print(f"✅ 启动器已启动 (PID: {process.pid})")
        print("请在启动器窗口中测试各项功能...")
        print("测试完成后请手动关闭启动器窗口")
        
        # 等待进程结束或用户中断
        try:
            process.wait()
            print("✅ 启动器已正常退出")
        except KeyboardInterrupt:
            print("\n⚠️ 用户中断测试")
            process.terminate()
            
    except Exception as e:
        print(f"❌ 启动launcher失败: {e}")
        return False
    
    print("\n✅ 测试完成!")
    return True

def show_feature_summary():
    """显示功能改进总结"""
    print("\n" + "=" * 60)
    print("启动器功能改进总结")
    print("=" * 60)
    
    improvements = [
        "✅ 移除自动关闭功能 - 启动器保持运行",
        "✅ 实时显示后台信息 - 改进日志捕获和显示",
        "✅ 添加控制按钮 - 重启、停止、打开浏览器、清空日志",
        "✅ 改进UI布局 - 更大窗口，更好的控件布局",
        "✅ 增强日志显示 - 颜色分级，智能过滤",
        "✅ 窗口关闭确认 - 防止意外关闭",
        "✅ 状态管理 - 按钮状态根据服务器状态动态更新",
        "✅ 进程管理 - 改进子进程启动和监控"
    ]
    
    for improvement in improvements:
        print(improvement)
    
    print("\n📝 使用说明:")
    print("1. 双击启动器或运行 python launcher.py")
    print("2. 启动器会自动启动Web服务器")
    print("3. 启动成功后启动器保持运行")
    print("4. 使用控制按钮管理服务器")
    print("5. 实时查看系统日志")
    print("6. 关闭窗口时会提示确认")

if __name__ == "__main__":
    show_feature_summary()
    print("\n" + "=" * 60)
    
    choice = input("是否启动功能测试? (y/n): ").lower().strip()
    if choice in ['y', 'yes', '是']:
        test_launcher_features()
    else:
        print("测试已取消")
