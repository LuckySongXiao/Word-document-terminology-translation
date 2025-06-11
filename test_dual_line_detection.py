#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双行检测功能测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.translation_detector import TranslationDetector

def test_dual_line_detection():
    """测试双行检测功能"""
    detector = TranslationDetector()
    
    print("=" * 80)
    print("双行检测功能测试")
    print("=" * 80)
    
    # 测试用例
    test_cases = [
        # 案例1：您提供的真实案例
        """文件制订/修订申请单
Documentation/Revision Application Form
申请状态：首次发行 修订 废止  
Application state: Initial issue Revision Obsolete
文件类型：手册 程序文件 三阶文件 技术文件 图纸 外来文件 表单
Document types: Manual Procedure Work InstructionTechnical Document Drawings External Document Form
分发基地:新疆其他                     
Distribution base: XJ Other""",
        
        # 案例2：混合内容
        """产品名称
Product Name
这是一段需要翻译的中文内容
版本号
Version Number
这是另一段需要翻译的中文内容""",
        
        # 案例3：纯中文内容
        """这是第一段中文内容
这是第二段中文内容
这是第三段中文内容""",
        
        # 案例4：纯英文内容
        """This is the first English paragraph
This is the second English paragraph
This is the third English paragraph""",
        
        # 案例5：数字和代码混合
        """123
456
产品规格
Product Specification
ABC123
DEF456""",
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"测试案例 {i}")
        print(f"{'='*60}")
        print("原始内容:")
        print("-" * 40)
        print(test_case)
        print("-" * 40)
        
        # 使用双行检测分析
        analysis_results = detector.analyze_lines_for_translation(test_case, "zh", "en")
        
        print(f"\n双行检测分析结果:")
        print("-" * 40)
        
        for result in analysis_results:
            action_color = "🔄" if result['action'] == 'translate' else "⏭️"
            print(f"{action_color} 第{result['line_number']}行 [{result['action'].upper()}]: {result['line'][:50]}...")
            print(f"   原因: {result['reason']}")
            if 'paired_with' in result:
                print(f"   配对行: 第{result['paired_with']}行")
            print()
        
        # 统计结果
        translate_count = sum(1 for r in analysis_results if r['action'] == 'translate')
        skip_count = sum(1 for r in analysis_results if r['action'] == 'skip')
        
        print(f"统计结果:")
        print(f"  需要翻译的行数: {translate_count}")
        print(f"  跳过的行数: {skip_count}")
        print(f"  总行数: {len(analysis_results)}")
        
        # 提取需要翻译的内容
        lines_to_translate = [r['line'] for r in analysis_results if r['action'] == 'translate']
        if lines_to_translate:
            print(f"\n需要翻译的内容:")
            for j, line in enumerate(lines_to_translate, 1):
                print(f"  {j}. {line}")
        else:
            print(f"\n✅ 所有内容都被跳过，无需翻译")

def test_translation_pair_detection():
    """测试翻译对检测功能"""
    detector = TranslationDetector()
    
    print(f"\n{'='*80}")
    print("翻译对检测功能测试")
    print("=" * 80)
    
    # 测试翻译对
    translation_pairs = [
        ("文件制订/修订申请单", "Documentation/Revision Application Form"),
        ("申请状态：首次发行 修订 废止", "Application state: Initial issue Revision Obsolete"),
        ("产品名称", "Product Name"),
        ("版本号", "Version Number"),
        ("技术文档", "Technical Document"),
        ("分发基地", "Distribution base"),
        
        # 非翻译对
        ("这是中文内容", "这也是中文内容"),
        ("This is English", "This is also English"),
        ("产品名称", "完全不相关的内容"),
        ("123", "456"),
        ("短文本", "Very long English text that doesn't match"),
    ]
    
    print("翻译对检测结果:")
    print("-" * 60)
    
    for line1, line2 in translation_pairs:
        is_pair, reason = detector._is_translation_pair(line1, line2, "zh", "en")
        status = "✅ 翻译对" if is_pair else "❌ 非翻译对"
        
        print(f"{status}")
        print(f"  第一行: {line1}")
        print(f"  第二行: {line2}")
        print(f"  判断: {reason}")
        print()

if __name__ == "__main__":
    test_dual_line_detection()
    test_translation_pair_detection()
