#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试真实案例的翻译检测器
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.translation_detector import TranslationDetector

def test_real_case():
    """测试用户提供的真实案例"""
    detector = TranslationDetector()
    
    print("=" * 80)
    print("真实案例翻译检测测试")
    print("=" * 80)
    
    # 用户提供的真实案例
    real_case = """文件制订/修订申请单
Documentation/Revision Application Form
申请状态：首次发行 修订 废止  
Application state: Initial issue Revision Obsolete
文件类型：手册 程序文件 三阶文件 技术文件 图纸 外来文件 表单
Document types: Manual Procedure Work InstructionTechnical Document Drawings 
		External Document Form
分发基地:新疆其他                     
Distribution base: XJ Other"""
    
    print("测试内容:")
    print("-" * 40)
    print(real_case)
    print("-" * 40)
    
    # 测试整体检测
    should_skip, reason = detector.should_skip_translation(real_case, "zh", "en")
    print(f"\n整体检测结果:")
    print(f"是否跳过: {should_skip}")
    print(f"跳过原因: {reason}")
    
    # 按行测试
    print(f"\n按行检测结果:")
    print("-" * 40)
    lines = real_case.split('\n')
    for i, line in enumerate(lines, 1):
        if line.strip():
            should_skip_line, reason_line = detector.should_skip_translation(line.strip(), "zh", "en")
            status = "跳过" if should_skip_line else "翻译"
            print(f"第{i}行 [{status}]: {line.strip()}")
            if should_skip_line:
                print(f"    原因: {reason_line}")
    
    # 测试段落级检测
    print(f"\n段落级检测结果:")
    print("-" * 40)
    paragraphs = [p.strip() for p in real_case.split('\n\n') if p.strip()]
    for i, paragraph in enumerate(paragraphs, 1):
        should_skip_para, reason_para = detector.should_skip_translation(paragraph, "zh", "en")
        status = "跳过" if should_skip_para else "翻译"
        print(f"段落{i} [{status}]:")
        print(f"  内容: {paragraph[:100]}...")
        if should_skip_para:
            print(f"  原因: {reason_para}")
    
    # 测试提取未翻译内容
    print(f"\n提取未翻译内容:")
    print("-" * 40)
    untranslated = detector.extract_untranslated_content(real_case, "zh", "en")
    print(f"发现 {len(untranslated)} 个需要翻译的部分:")
    for i, part in enumerate(untranslated, 1):
        print(f"  {i}. {part}")
    
    # 测试其他相似案例
    print(f"\n测试其他相似案例:")
    print("-" * 40)
    
    similar_cases = [
        # 案例1：简单的中英文对照
        """产品名称
Product Name
版本号
Version Number""",
        
        # 案例2：带标点的对照
        """申请状态：首次发行
Application Status: Initial Issue
文件类型：技术文档
Document Type: Technical Document""",
        
        # 案例3：混合格式
        """标题：文档管理
Title: Document Management
描述：这是一个文档管理系统
Description: This is a document management system""",
        
        # 案例4：应该翻译的纯中文
        """这是一个需要翻译的纯中文段落，没有任何英文对照。
它包含多个句子，应该被识别为需要翻译的内容。""",
        
        # 案例5：应该翻译的纯英文
        """This is a pure English paragraph that needs translation.
It contains multiple sentences and should be identified as content that needs translation."""
    ]
    
    for i, case in enumerate(similar_cases, 1):
        print(f"\n案例 {i}:")
        should_skip_case, reason_case = detector.should_skip_translation(case, "zh", "en")
        status = "跳过" if should_skip_case else "翻译"
        print(f"[{status}] {case[:50]}...")
        if should_skip_case:
            print(f"原因: {reason_case}")

if __name__ == "__main__":
    test_real_case()
