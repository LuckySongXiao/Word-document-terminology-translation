#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试表格翻译遗漏问题
"""

import os
import sys
from docx import Document
import logging
from services.translation_detector import TranslationDetector

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_missing_cells():
    """调试表格4最后一行的遗漏单元格"""
    
    # 初始化翻译检测器
    detector = TranslationDetector()
    
    # 问题单元格的内容
    problem_text = """备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
2、晶裂部分少子统一按照5＜x＞20μs进行分类；"""
    
    logger.info("=== 调试遗漏的单元格内容 ===")
    logger.info(f"问题文本: {problem_text}")
    
    # 测试翻译检测器的判断
    should_skip, reason = detector.should_skip_translation(problem_text, "zh", "en")
    logger.info(f"翻译检测器判断 - 应该跳过: {should_skip}, 原因: {reason}")
    
    # 分析文本特征
    logger.info("\n=== 文本特征分析 ===")
    
    # 检查是否包含中文
    import re
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', problem_text))
    has_english = bool(re.search(r'[A-Za-z]', problem_text))
    logger.info(f"包含中文: {has_chinese}")
    logger.info(f"包含英文: {has_english}")
    
    # 检查行数
    lines = [line.strip() for line in problem_text.split('\n') if line.strip()]
    logger.info(f"行数: {len(lines)}")
    for i, line in enumerate(lines, 1):
        logger.info(f"  第{i}行: {line}")
        line_has_chinese = bool(re.search(r'[\u4e00-\u9fff]', line))
        line_has_english = bool(re.search(r'[A-Za-z]', line))
        logger.info(f"    中文: {line_has_chinese}, 英文: {line_has_english}")
    
    # 测试双行检测
    if len(lines) >= 2:
        logger.info("\n=== 双行检测测试 ===")
        for i in range(len(lines) - 1):
            line1 = lines[i]
            line2 = lines[i + 1]
            is_pair, pair_reason = detector._is_translation_pair(line1, line2, "zh", "en")
            logger.info(f"行{i+1}和行{i+2}是否为翻译对: {is_pair}, 原因: {pair_reason}")
    
    # 测试各种检测模式
    logger.info("\n=== 各种检测模式测试 ===")
    
    # 1. 检查纯数字/代码模式
    for pattern in detector.skip_patterns:
        if re.match(pattern, problem_text, re.IGNORECASE):
            logger.info(f"匹配跳过模式: {pattern}")
    
    # 2. 检查双语格式标记
    for pattern in detector.bilingual_patterns:
        if re.search(pattern, problem_text, re.IGNORECASE | re.DOTALL):
            logger.info(f"匹配双语模式: {pattern}")
    
    # 3. 检查语言分布
    source_pattern = detector._get_language_pattern("zh")
    target_pattern = detector._get_language_pattern("en")
    
    if source_pattern and target_pattern:
        source_matches = len(re.findall(source_pattern, problem_text))
        target_matches = len(re.findall(target_pattern, problem_text))
        logger.info(f"中文字符数: {source_matches}")
        logger.info(f"英文字符数: {target_matches}")
        
        # 计算语言比例
        total_chars = len(problem_text)
        chinese_ratio = source_matches / total_chars if total_chars > 0 else 0
        english_ratio = target_matches / total_chars if total_chars > 0 else 0
        logger.info(f"中文比例: {chinese_ratio:.2%}")
        logger.info(f"英文比例: {english_ratio:.2%}")
    
    # 4. 检查是否被误判为已翻译内容
    logger.info("\n=== 已翻译内容检测详细分析 ===")
    
    # 检查分行对照格式
    if len(lines) >= 2:
        consecutive_pairs = 0
        for i in range(len(lines) - 1):
            line1 = lines[i]
            line2 = lines[i + 1]

            # 检查是否为中文行后跟英文行
            line1_has_chinese = bool(re.search(source_pattern, line1))
            line1_has_english = bool(re.search(target_pattern, line1))
            line2_has_chinese = bool(re.search(source_pattern, line2))
            line2_has_english = bool(re.search(target_pattern, line2))
            
            logger.info(f"行{i+1}: 中文={line1_has_chinese}, 英文={line1_has_english}")
            logger.info(f"行{i+2}: 中文={line2_has_chinese}, 英文={line2_has_english}")
            
            if (line1_has_chinese and line2_has_english and
                not line1_has_english and not line2_has_chinese):
                consecutive_pairs += 1
                logger.info(f"检测到中英文对照: 行{i+1}->行{i+2}")
            elif (line1_has_english and line2_has_chinese and
                  not line1_has_chinese and not line2_has_english):
                consecutive_pairs += 1
                logger.info(f"检测到英中文对照: 行{i+1}->行{i+2}")

        logger.info(f"连续对照行数: {consecutive_pairs}")
        if consecutive_pairs >= 2:
            logger.warning("⚠️ 被误判为已翻译内容！")

def test_fix_translation():
    """测试修复翻译"""
    logger.info("\n=== 测试修复翻译 ===")
    
    # 模拟翻译器
    class MockTranslator:
        def translate_text(self, text, terminology, source_lang, target_lang):
            # 简单的模拟翻译
            if "备注" in text:
                return text.replace("备注：", "Note: ").replace("、", ", ").replace("；", "; ")
            return f"[Translated] {text}"
    
    translator = MockTranslator()
    
    problem_text = """备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
2、晶裂部分少子统一按照5＜x＞20μs进行分类；"""
    
    # 测试翻译
    translated = translator.translate_text(problem_text, {}, "zh", "en")
    logger.info(f"原文: {problem_text}")
    logger.info(f"译文: {translated}")

def main():
    debug_missing_cells()
    test_fix_translation()

if __name__ == "__main__":
    main()
