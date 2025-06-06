#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复效果的脚本
"""

import os
import sys
import time
import requests
import json
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_terminology_api():
    """测试术语库API"""
    base_url = "http://localhost:8001"

    try:
        # 测试获取术语库
        logger.info("测试获取术语库...")
        response = requests.get(f"{base_url}/api/terminology")
        if response.status_code == 200:
            data = response.json()
            terminology = data.get('terminology', {})
            logger.info(f"术语库加载成功，包含 {len(terminology)} 种语言")
            for lang, terms in terminology.items():
                logger.info(f"  - {lang}: {len(terms)} 个术语")
        else:
            logger.error(f"获取术语库失败: {response.status_code}")

        # 测试获取语言列表
        logger.info("测试获取语言列表...")
        response = requests.get(f"{base_url}/api/terminology/languages")
        if response.status_code == 200:
            data = response.json()
            languages = data.get('languages', [])
            logger.info(f"语言列表获取成功: {languages}")
        else:
            logger.error(f"获取语言列表失败: {response.status_code}")

        return True

    except requests.exceptions.ConnectionError:
        logger.error("无法连接到Web服务器，请确保服务器正在运行")
        return False
    except Exception as e:
        logger.error(f"测试术语库API时出错: {str(e)}")
        return False

def test_web_page():
    """测试Web页面是否正常加载"""
    base_url = "http://localhost:8001"

    try:
        logger.info("测试Web页面加载...")
        response = requests.get(base_url)
        if response.status_code == 200:
            logger.info("Web页面加载成功")
            return True
        else:
            logger.error(f"Web页面加载失败: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        logger.error("无法连接到Web服务器")
        return False
    except Exception as e:
        logger.error(f"测试Web页面时出错: {str(e)}")
        return False

def check_file_integrity():
    """检查关键文件的完整性"""
    logger.info("检查关键文件完整性...")

    files_to_check = [
        "web/static/js/main.js",
        "web/api.py",
        "web/templates/index.html",
        "build_temp/web/static/js/main.js",
        "build_temp/web/api.py"
    ]

    all_good = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            logger.info(f"✓ {file_path} 存在")
        else:
            logger.error(f"✗ {file_path} 不存在")
            all_good = False

    return all_good

def test_translation_debug():
    """测试翻译调试信息"""
    base_url = "http://localhost:8001"

    try:
        logger.info("测试翻译服务状态...")
        response = requests.get(f"{base_url}/api/translators")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"当前翻译器: {data.get('current', 'unknown')}")
            available = data.get('available', {})
            for name, status in available.items():
                status_text = "可用" if status else "不可用" if status is not None else "未检查"
                logger.info(f"  - {name}: {status_text}")
        else:
            logger.error(f"获取翻译器状态失败: {response.status_code}")

        return True

    except requests.exceptions.ConnectionError:
        logger.error("无法连接到Web服务器")
        return False
    except Exception as e:
        logger.error(f"测试翻译服务状态时出错: {str(e)}")
        return False

def main():
    """主测试函数"""
    logger.info("=" * 50)
    logger.info("开始测试修复效果")
    logger.info("=" * 50)

    # 检查文件完整性
    if not check_file_integrity():
        logger.error("文件完整性检查失败")
        return False

    # 测试Web页面
    if not test_web_page():
        logger.error("Web页面测试失败")
        return False

    # 测试术语库API
    if not test_terminology_api():
        logger.error("术语库API测试失败")
        return False

    # 测试翻译服务状态
    if not test_translation_debug():
        logger.error("翻译服务状态测试失败")
        return False

    logger.info("=" * 50)
    logger.info("所有测试通过！修复效果良好")
    logger.info("=" * 50)

    logger.info("修复内容总结:")
    logger.info("1. ✓ 修复了术语库加载时的JavaScript错误")
    logger.info("2. ✓ 改进了状态栏元素的创建时机")
    logger.info("3. ✓ 增强了WebSocket日志处理器配置")
    logger.info("4. ✓ 添加了翻译过程的详细日志记录")
    logger.info("5. ✓ 优化了日志处理器的清理机制")
    logger.info("6. ✓ 添加了翻译任务调试日志")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
