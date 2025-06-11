#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的翻译系统
"""

import os
import sys
from docx import Document
import logging
from services.translation_detector import TranslationDetector

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_problematic_content():
    """测试之前有问题的内容"""
    
    detector = TranslationDetector()
    
    # 测试用例
    test_cases = [
        {
            "name": "问题单元格内容",
            "text": """备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
2、晶裂部分少子统一按照5＜x＞20μs进行分类；""",
            "expected_skip": False,
            "reason": "包含技术符号的中文内容应该被翻译"
        },
        {
            "name": "真正的双语对照内容",
            "text": """备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
Note: 1. Tail materials are classified according to end face minority carriers, and round bars are classified according to A-face minority carriers;""",
            "expected_skip": True,
            "reason": "真正的中英文对照内容应该被跳过"
        },
        {
            "name": "纯中文内容",
            "text": "这是一段纯中文内容，没有任何英文字符。",
            "expected_skip": False,
            "reason": "纯中文内容应该被翻译"
        },
        {
            "name": "纯英文内容",
            "text": "This is pure English content without any Chinese characters.",
            "expected_skip": True,
            "reason": "纯英文内容应该被跳过（当源语言为中文时）"
        },
        {
            "name": "包含少量英文符号的中文",
            "text": "电阻率范围为0.2-0.4Ω.cm，测试条件为25°C。",
            "expected_skip": False,
            "reason": "包含技术符号的中文内容应该被翻译"
        },
        {
            "name": "明确的双语格式标记",
            "text": """【原文】这是原文内容
【译文】This is the translated content""",
            "expected_skip": True,
            "reason": "明确的双语格式标记应该被跳过"
        }
    ]
    
    logger.info("=== 测试修复后的翻译检测器 ===")
    
    all_passed = True
    for i, case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试用例 {i}: {case['name']} ---")
        logger.info(f"文本: {case['text'][:100]}...")
        
        should_skip, reason = detector.should_skip_translation(case['text'], "zh", "en")
        
        logger.info(f"检测结果: 跳过={should_skip}, 原因={reason}")
        logger.info(f"期望结果: 跳过={case['expected_skip']}")
        
        if should_skip == case['expected_skip']:
            logger.info("✅ 测试通过")
        else:
            logger.error(f"❌ 测试失败: {case['reason']}")
            all_passed = False
    
    logger.info(f"\n=== 测试总结 ===")
    if all_passed:
        logger.info("✅ 所有测试用例都通过了！翻译检测器修复成功。")
    else:
        logger.error("❌ 部分测试用例失败，需要进一步调整。")
    
    return all_passed

def test_document_processing():
    """测试文档处理"""
    logger.info("\n=== 测试文档处理建议 ===")
    logger.info("建议重新运行翻译程序来测试修复效果：")
    logger.info("1. 运行 python main.py")
    logger.info("2. 选择要翻译的文档")
    logger.info("3. 检查输出文档中表格4的最后两个单元格是否包含英文翻译")
    
    # 检查是否有原始文档
    input_files = [
        "单晶电阻率管控技术标准.docx",
        "单晶电阻率管控技术标准.doc"
    ]
    
    for filename in input_files:
        if os.path.exists(filename):
            logger.info(f"找到原始文档: {filename}")
            logger.info("可以重新翻译此文档来验证修复效果")
            break
    else:
        logger.warning("未找到原始文档，请确保文档在当前目录中")

def main():
    logger.info("开始测试修复后的翻译系统...")
    
    # 测试翻译检测器
    detection_passed = test_problematic_content()
    
    # 提供文档处理建议
    test_document_processing()
    
    if detection_passed:
        logger.info("\n🎉 翻译检测器修复成功！")
        logger.info("现在可以重新翻译文档，表格中的遗漏内容应该会被正确翻译。")
    else:
        logger.error("\n⚠️ 翻译检测器仍有问题，需要进一步调整。")

if __name__ == "__main__":
    main()
