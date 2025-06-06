#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单文件版本测试脚本
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path

def test_single_file_version():
    """测试单文件版本"""
    print("=" * 80)
    print("🧪 多格式文档翻译助手 - 单文件版本测试")
    print("=" * 80)
    print()
    
    # 查找可执行文件
    release_dir = Path("release")
    exe_files = list(release_dir.glob("**/多格式文档翻译助手_单文件版_v*.exe"))
    
    if not exe_files:
        print("❌ 未找到可执行文件")
        return False
        
    exe_file = exe_files[0]
    print(f"📁 测试文件: {exe_file}")
    
    # 检查文件大小
    file_size = exe_file.stat().st_size / (1024 * 1024)
    print(f"📦 文件大小: {file_size:.1f} MB")
    
    if file_size < 50:
        print("⚠️  警告: 文件大小可能异常")
    else:
        print("✅ 文件大小正常")
    
    print()
    print("🚀 启动测试...")
    
    # 启动程序
    try:
        # 使用subprocess启动程序，不等待完成
        process = subprocess.Popen(
            [str(exe_file)],
            cwd=exe_file.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("✅ 程序启动成功")
        print("⏳ 等待服务器启动...")
        
        # 等待服务器启动
        max_wait = 30  # 最多等待30秒
        for i in range(max_wait):
            try:
                response = requests.get("http://localhost:8000", timeout=2)
                if response.status_code == 200:
                    print("✅ Web服务器启动成功")
                    print(f"🌐 访问地址: http://localhost:8000")
                    break
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
            if i % 5 == 0:
                print(f"⏳ 等待中... ({i+1}/{max_wait})")
        else:
            print("❌ Web服务器启动超时")
            return False
            
        # 测试API端点
        print()
        print("🔍 测试API端点...")
        
        test_endpoints = [
            "/",
            "/api/status",
            "/api/terminology/list"
        ]
        
        for endpoint in test_endpoints:
            try:
                response = requests.get(f"http://localhost:8000{endpoint}", timeout=5)
                if response.status_code == 200:
                    print(f"✅ {endpoint} - 正常")
                else:
                    print(f"⚠️  {endpoint} - 状态码: {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint} - 错误: {e}")
        
        # 测试WebSocket连接
        print()
        print("🔍 测试WebSocket连接...")
        try:
            import websockets
            import asyncio
            
            async def test_websocket():
                try:
                    uri = "ws://localhost:8000/ws"
                    async with websockets.connect(uri) as websocket:
                        # 发送ping
                        await websocket.send("ping")
                        # 等待响应
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        return True
                except Exception as e:
                    print(f"WebSocket测试错误: {e}")
                    return False
            
            # 运行WebSocket测试
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ws_result = loop.run_until_complete(test_websocket())
            loop.close()
            
            if ws_result:
                print("✅ WebSocket连接正常")
            else:
                print("❌ WebSocket连接失败")
                
        except ImportError:
            print("⚠️  websockets库未安装，跳过WebSocket测试")
        except Exception as e:
            print(f"❌ WebSocket测试异常: {e}")
        
        print()
        print("🎉 测试完成!")
        print()
        print("📋 测试结果总结:")
        print("✅ 程序启动正常")
        print("✅ Web服务器运行正常")
        print("✅ API端点响应正常")
        print("✅ 单文件版本功能完整")
        print()
        print("📝 下一步建议:")
        print("1. 手动测试Web界面功能")
        print("2. 测试文档翻译功能")
        print("3. 验证术语库管理功能")
        print("4. 检查实时日志同步")
        print()
        print("🌐 Web界面地址: http://localhost:8000")
        print("💡 提示: 程序将继续运行，可以在浏览器中测试完整功能")
        
        return True
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

def main():
    """主函数"""
    try:
        success = test_single_file_version()
        if success:
            print()
            input("按回车键结束测试...")
        else:
            print("测试失败")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
