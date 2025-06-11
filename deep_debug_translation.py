#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度调试翻译过程中的问题
"""

import os
import sys
import logging
from services.translation_detector import TranslationDetector

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def deep_debug_problematic_content():
    """深度调试问题内容"""
    
    detector = TranslationDetector()
    
    # 完整的单元格内容（包含两条备注）
    full_content = """备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
2、晶裂部分少子统一按照5＜x＞20μs进行分类；"""
    
    # 单独的第1条内容
    first_note = "备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；"
    
    # 单独的第2条内容
    second_note = "2、晶裂部分少子统一按照5＜x＞20μs进行分类；"
    
    logger.info("=== 深度调试翻译检测逻辑 ===")
    
    # 测试完整内容
    logger.info("\n--- 测试完整内容 ---")
    logger.info(f"完整内容: {full_content}")
    should_skip_full, reason_full = detector.should_skip_translation(full_content, "zh", "en")
    logger.info(f"完整内容检测结果: 跳过={should_skip_full}, 原因={reason_full}")
    
    # 测试第1条内容
    logger.info("\n--- 测试第1条内容 ---")
    logger.info(f"第1条内容: {first_note}")
    should_skip_1, reason_1 = detector.should_skip_translation(first_note, "zh", "en")
    logger.info(f"第1条内容检测结果: 跳过={should_skip_1}, 原因={reason_1}")
    
    # 测试第2条内容
    logger.info("\n--- 测试第2条内容 ---")
    logger.info(f"第2条内容: {second_note}")
    should_skip_2, reason_2 = detector.should_skip_translation(second_note, "zh", "en")
    logger.info(f"第2条内容检测结果: 跳过={should_skip_2}, 原因={reason_2}")
    
    # 分析为什么第1条被跳过
    logger.info("\n=== 分析第1条内容被跳过的原因 ===")
    
    # 检查各种跳过条件
    import re
    
    # 1. 检查纯数字/代码模式
    logger.info("1. 检查纯数字/代码模式:")
    for pattern in detector.skip_patterns:
        if re.match(pattern, first_note, re.IGNORECASE):
            logger.info(f"   匹配跳过模式: {pattern}")
        else:
            logger.debug(f"   不匹配模式: {pattern}")
    
    # 2. 检查双语格式标记
    logger.info("2. 检查双语格式标记:")
    for pattern in detector.bilingual_patterns:
        if re.search(pattern, first_note, re.IGNORECASE | re.DOTALL):
            logger.info(f"   匹配双语模式: {pattern}")
        else:
            logger.debug(f"   不匹配双语模式: {pattern}")
    
    # 3. 检查语言检测
    logger.info("3. 检查语言检测:")
    source_pattern = detector._get_language_pattern("zh")
    target_pattern = detector._get_language_pattern("en")
    
    if source_pattern and target_pattern:
        source_matches = len(re.findall(source_pattern, first_note))
        target_matches = len(re.findall(target_pattern, first_note))
        logger.info(f"   中文字符数: {source_matches}")
        logger.info(f"   英文字符数: {target_matches}")
        
        # 计算语言比例
        total_chars = len(first_note)
        chinese_ratio = source_matches / total_chars if total_chars > 0 else 0
        english_ratio = target_matches / total_chars if total_chars > 0 else 0
        logger.info(f"   中文比例: {chinese_ratio:.2%}")
        logger.info(f"   英文比例: {english_ratio:.2%}")
        
        # 检查是否被误判为目标语言内容
        if english_ratio > 0.3:
            logger.warning(f"   ⚠️ 英文比例过高，可能被误判为目标语言内容")
    
    # 4. 检查混合语言检测
    logger.info("4. 检查混合语言检测:")
    is_mixed, mixed_reason = detector._check_mixed_languages(first_note, "zh", "en")
    logger.info(f"   混合语言检测: {is_mixed}, 原因: {mixed_reason}")
    
    # 5. 模拟翻译过程中的分段处理
    logger.info("\n=== 模拟翻译过程中的分段处理 ===")
    
    # 检查是否在翻译过程中被分段处理
    lines = [line.strip() for line in full_content.split('\n') if line.strip()]
    logger.info(f"分段结果: {len(lines)} 行")
    for i, line in enumerate(lines, 1):
        logger.info(f"  第{i}行: {line}")
        line_should_skip, line_reason = detector.should_skip_translation(line, "zh", "en")
        logger.info(f"    检测结果: 跳过={line_should_skip}, 原因={line_reason}")
    
    # 6. 检查是否存在翻译器内部的分段逻辑
    logger.info("\n=== 检查可能的翻译器内部分段逻辑 ===")
    
    # 模拟按句号分段
    sentences = [s.strip() for s in full_content.replace('；', '。').split('。') if s.strip()]
    logger.info(f"按句号分段结果: {len(sentences)} 句")
    for i, sentence in enumerate(sentences, 1):
        if sentence:
            logger.info(f"  第{i}句: {sentence}")
            sent_should_skip, sent_reason = detector.should_skip_translation(sentence, "zh", "en")
            logger.info(f"    检测结果: 跳过={sent_should_skip}, 原因={sent_reason}")
    
    # 7. 检查是否存在特殊字符干扰
    logger.info("\n=== 检查特殊字符干扰 ===")
    
    # 检查第1条内容中的特殊字符
    special_chars = ['：', '、', '；', '，']
    for char in special_chars:
        if char in first_note:
            logger.info(f"   包含特殊字符: '{char}'")
            # 测试去除特殊字符后的检测结果
            clean_content = first_note.replace(char, ' ')
            clean_should_skip, clean_reason = detector.should_skip_translation(clean_content, "zh", "en")
            logger.info(f"   去除'{char}'后检测结果: 跳过={clean_should_skip}, 原因={clean_reason}")

def test_translation_flow_simulation():
    """模拟翻译流程"""
    logger.info("\n=== 模拟翻译流程 ===")
    
    # 模拟表格单元格处理流程
    cell_content = """备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
2、晶裂部分少子统一按照5＜x＞20μs进行分类；"""
    
    logger.info(f"原始单元格内容: {cell_content}")
    
    # 模拟可能的预处理步骤
    logger.info("\n--- 模拟预处理步骤 ---")
    
    # 1. 按行分割
    lines = cell_content.split('\n')
    logger.info(f"按行分割: {len(lines)} 行")
    
    # 2. 逐行处理
    detector = TranslationDetector()
    for i, line in enumerate(lines):
        line = line.strip()
        if line:
            logger.info(f"处理第{i+1}行: {line}")
            should_skip, reason = detector.should_skip_translation(line, "zh", "en")
            logger.info(f"  检测结果: 跳过={should_skip}, 原因={reason}")
            
            if not should_skip:
                logger.info(f"  ✅ 第{i+1}行需要翻译")
            else:
                logger.warning(f"  ❌ 第{i+1}行被跳过: {reason}")

def main():
    logger.info("开始深度调试翻译问题...")
    
    deep_debug_problematic_content()
    test_translation_flow_simulation()
    
    logger.info("\n=== 调试完成 ===")

if __name__ == "__main__":
    main()
