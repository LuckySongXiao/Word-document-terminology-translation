#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译检测器测试脚本
用于验证翻译检测器的功能是否正常工作
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.translation_detector import TranslationDetector

def test_translation_detector():
    """测试翻译检测器的各种功能"""
    detector = TranslationDetector()
    
    print("=" * 60)
    print("翻译检测器功能测试")
    print("=" * 60)
    
    # 测试用例
    test_cases = [
        # 应该跳过的内容
        ("123", "纯数字"),
        ("45.67%", "百分比"),
        ("ABC123", "代码"),
        ("https://www.example.com", "URL"),
        ("user@example.com", "邮箱"),
        ("2023-12-25", "日期"),
        ("", "空文本"),
        ("   ", "空白文本"),
        
        # 双语内容（应该跳过）
        ("这是中文内容\nThis is English content", "中英文分行"),
        ("产品名称(Product Name)", "中英文括号对照"),
        ("【原文】这是原文\n【译文】This is translation", "翻译标记格式"),
        ("中文：这是中文\n英文：This is English", "中英文标记格式"),
        
        # 应该翻译的内容
        ("这是一段需要翻译的中文内容", "纯中文内容"),
        ("This is English content that needs translation", "纯英文内容"),
        ("这是一个较长的段落，包含了多个句子。它应该被翻译成目标语言。", "长中文段落"),
        ("人工智能技术在现代社会中发挥着重要作用", "技术相关中文"),
        
        # 边界情况
        ("AI", "短英文缩写"),
        ("人工智能", "短中文词汇"),
        ("123 这是混合内容", "数字+中文"),
        ("Product 产品", "英文+中文"),
    ]
    
    print("\n1. 基本跳过检测测试 (中文→英文)")
    print("-" * 40)
    for text, description in test_cases:
        should_skip, reason = detector.should_skip_translation(text, "zh", "en")
        status = "跳过" if should_skip else "翻译"
        print(f"[{status}] {description}: {text[:30]}...")
        if should_skip:
            print(f"    原因: {reason}")
        print()
    
    print("\n2. 反向翻译检测测试 (英文→中文)")
    print("-" * 40)
    english_cases = [
        ("This is pure English text", "纯英文内容"),
        ("这是中文\nThis is English", "中英文混合"),
        ("English text with 中文 mixed", "英中混合"),
        ("Product (产品)", "英中括号对照"),
    ]
    
    for text, description in english_cases:
        should_skip, reason = detector.should_skip_translation(text, "en", "zh")
        status = "跳过" if should_skip else "翻译"
        print(f"[{status}] {description}: {text[:30]}...")
        if should_skip:
            print(f"    原因: {reason}")
        print()
    
    print("\n3. 提取未翻译内容测试")
    print("-" * 40)
    mixed_content = """这是第一段中文内容，需要翻译。

【原文】这是已经标记的原文
【译文】This is the marked translation

这是第二段中文内容，也需要翻译。

产品名称(Product Name)

这是第三段中文内容。

123

这是第四段中文内容。"""
    
    untranslated_parts = detector.extract_untranslated_content(mixed_content, "zh", "en")
    print("原始内容包含多个段落，其中一些已翻译，一些未翻译")
    print(f"检测到 {len(untranslated_parts)} 个需要翻译的段落:")
    for i, part in enumerate(untranslated_parts, 1):
        print(f"  {i}. {part[:50]}...")
    
    print("\n4. 完整翻译检测测试")
    print("-" * 40)
    complete_cases = [
        ("【原文】中文内容【译文】English content", "完整双语标记"),
        ("这是纯中文内容", "纯中文内容"),
        ("This is pure English", "纯英文内容"),
        ("123", "纯数字"),
    ]
    
    for text, description in complete_cases:
        is_complete = detector.is_translation_complete(text, "zh", "en")
        status = "已完成" if is_complete else "未完成"
        print(f"[{status}] {description}: {text[:30]}...")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_translation_detector()
