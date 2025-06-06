#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内网模式测试脚本
"""

import sys
import os
import json
import time
from pathlib import Path

def test_config_loading():
    """测试配置文件加载"""
    print("🔍 测试配置文件加载...")
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        env_config = config.get('environment', {})
        print(f"  - 内网模式: {env_config.get('intranet_mode', False)}")
        print(f"  - 离线模式: {env_config.get('offline_mode', False)}")
        print(f"  - 跳过网络检查: {env_config.get('skip_network_checks', False)}")
        
        print("✅ 配置文件加载成功")
        return True, config
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False, None

def test_environment_detection():
    """测试环境检测"""
    print("🔍 测试环境检测...")
    try:
        from services.translator import TranslationService
        
        # 创建翻译服务实例
        translator = TranslationService()
        
        # 测试内网环境检测
        is_intranet = translator._detect_intranet_environment()
        print(f"  - 检测结果: {'内网环境' if is_intranet else '外网环境'}")
        
        print("✅ 环境检测测试通过")
        return True, is_intranet
    except Exception as e:
        print(f"❌ 环境检测测试失败: {e}")
        return False, False

def test_zhipuai_check():
    """测试智谱AI连接检查"""
    print("🔍 测试智谱AI连接检查...")
    try:
        from services.translator import TranslationService
        
        # 创建翻译服务实例
        translator = TranslationService()
        
        # 测试智谱AI可用性检查（跳过网络检查）
        zhipuai_available = translator._check_zhipuai_available(skip_network_check=True)
        print(f"  - 智谱AI可用性（跳过网络检查）: {'可用' if zhipuai_available else '不可用'}")
        
        # 测试智谱AI可用性检查（不跳过网络检查）
        zhipuai_available_normal = translator._check_zhipuai_available(skip_network_check=False)
        print(f"  - 智谱AI可用性（正常检查）: {'可用' if zhipuai_available_normal else '不可用'}")
        
        print("✅ 智谱AI连接检查测试通过")
        return True
    except Exception as e:
        print(f"❌ 智谱AI连接检查测试失败: {e}")
        return False

def test_translator_initialization():
    """测试翻译器初始化"""
    print("🔍 测试翻译器初始化...")
    try:
        from services.translator import TranslationService
        
        # 创建翻译服务实例
        translator = TranslationService()
        
        print(f"  - 可用翻译器: {list(translator.translators.keys())}")
        print(f"  - 使用备用翻译器: {translator.use_fallback}")
        print(f"  - 主翻译器类型: {type(translator.primary_translator).__name__ if translator.primary_translator else 'None'}")
        
        print("✅ 翻译器初始化测试通过")
        return True
    except Exception as e:
        print(f"❌ 翻译器初始化测试失败: {e}")
        return False

def test_environment_variables():
    """测试环境变量"""
    print("🔍 测试环境变量...")
    
    env_vars = {
        'INTRANET_MODE': os.getenv('INTRANET_MODE', ''),
        'OFFLINE_MODE': os.getenv('OFFLINE_MODE', ''),
    }
    
    for var, value in env_vars.items():
        print(f"  - {var}: {value if value else '未设置'}")
    
    print("✅ 环境变量检查完成")
    return True

def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 内网模式测试")
    print("=" * 60)
    print()
    
    tests = [
        ("配置文件加载", test_config_loading),
        ("环境变量检查", test_environment_variables),
        ("环境检测", test_environment_detection),
        ("智谱AI连接检查", test_zhipuai_check),
        ("翻译器初始化", test_translator_initialization),
    ]
    
    passed = 0
    total = len(tests)
    results = {}
    
    for test_name, test_func in tests:
        print(f"📋 {test_name}")
        try:
            if test_name == "配置文件加载":
                success, config = test_func()
                results['config'] = config
            elif test_name == "环境检测":
                success, is_intranet = test_func()
                results['is_intranet'] = is_intranet
            else:
                success = test_func()
            
            if success:
                passed += 1
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
        print()
    
    print("=" * 60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    print("=" * 60)
    
    # 显示总结信息
    if 'config' in results and results['config']:
        env_config = results['config'].get('environment', {})
        print("📋 当前配置:")
        print(f"  - 内网模式: {env_config.get('intranet_mode', False)}")
        print(f"  - 离线模式: {env_config.get('offline_mode', False)}")
        print(f"  - 跳过网络检查: {env_config.get('skip_network_checks', False)}")
        print()
    
    if 'is_intranet' in results:
        print(f"🌐 环境检测结果: {'内网环境' if results['is_intranet'] else '外网环境'}")
        print()
    
    if passed == total:
        print("🎉 所有测试通过！内网模式配置正确！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查配置")
        return 1

if __name__ == "__main__":
    exit_code = main()
    input("按回车键退出...")
    sys.exit(exit_code)
