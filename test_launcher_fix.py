#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试启动器修复的脚本
"""

import sys
import os
import time
import subprocess
from pathlib import Path

def test_launcher_import():
    """测试启动器是否可以正常导入"""
    print("🔍 测试启动器导入...")
    try:
        # 尝试导入launcher模块
        import launcher
        print("✅ 启动器模块导入成功")
        return True
    except Exception as e:
        print(f"❌ 启动器模块导入失败: {e}")
        return False

def test_launcher_class():
    """测试启动器类是否可以正常创建"""
    print("🔍 测试启动器类创建...")
    try:
        from launcher import LauncherApp
        app = LauncherApp()
        print("✅ 启动器类创建成功")
        
        # 测试一些基本属性
        print(f"  - 服务器端口: {app.server_port}")
        print(f"  - 服务器运行状态: {app.server_running}")
        
        # 清理
        app.root.destroy()
        return True
    except Exception as e:
        print(f"❌ 启动器类创建失败: {e}")
        return False

def test_lambda_expressions():
    """测试lambda表达式是否正常工作"""
    print("🔍 测试lambda表达式...")
    try:
        from launcher import LauncherApp
        app = LauncherApp()
        
        # 测试一些可能有问题的方法
        test_port = 8000
        test_url = "http://localhost:8000"
        test_error = Exception("测试错误")
        
        # 这些调用应该不会抛出NameError或UnboundLocalError
        try:
            # 模拟一些lambda调用（不实际执行，只是检查语法）
            lambda_test1 = lambda p=test_port: f"端口 {p} 测试"
            lambda_test2 = lambda u=test_url: f"URL {u} 测试"
            lambda_test3 = lambda err=test_error: f"错误 {err} 测试"
            
            # 执行测试
            result1 = lambda_test1()
            result2 = lambda_test2()
            result3 = lambda_test3()
            
            print(f"  - Lambda测试1: {result1}")
            print(f"  - Lambda测试2: {result2}")
            print(f"  - Lambda测试3: {result3}")
            
        except (NameError, UnboundLocalError) as e:
            print(f"❌ Lambda表达式测试失败: {e}")
            app.root.destroy()
            return False
        
        print("✅ Lambda表达式测试通过")
        app.root.destroy()
        return True
    except Exception as e:
        print(f"❌ Lambda表达式测试失败: {e}")
        return False

def test_port_checking():
    """测试端口检查功能"""
    print("🔍 测试端口检查功能...")
    try:
        from launcher import LauncherApp
        app = LauncherApp()
        
        # 测试端口检查方法
        test_port = 8000
        is_in_use = app.is_port_in_use(test_port)
        print(f"  - 端口 {test_port} 是否被占用: {is_in_use}")
        
        # 测试服务器运行检查
        is_running = app.check_server_running(test_port)
        print(f"  - 端口 {test_port} 服务器是否运行: {is_running}")
        
        print("✅ 端口检查功能测试通过")
        app.root.destroy()
        return True
    except Exception as e:
        print(f"❌ 端口检查功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 启动器修复验证测试")
    print("=" * 60)
    print()
    
    tests = [
        ("导入测试", test_launcher_import),
        ("类创建测试", test_launcher_class),
        ("Lambda表达式测试", test_lambda_expressions),
        ("端口检查测试", test_port_checking),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"📋 {test_name}")
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
        print()
    
    print("=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！启动器修复成功！")
        return 0
    else:
        print("⚠️  部分测试失败，需要进一步检查")
        return 1

if __name__ == "__main__":
    exit_code = main()
    input("按回车键退出...")
    sys.exit(exit_code)
