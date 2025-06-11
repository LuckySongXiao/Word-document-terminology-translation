#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOC文件处理测试脚本
"""

import os
import sys
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.doc_processor import DOCProcessor
from services.translator import TranslationService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_doc_processing():
    """测试DOC文件处理功能"""

    # 直接指定测试文件
    test_file = "uploads/单晶电阻率管控技术标准.doc"

    if not os.path.exists(test_file):
        print(f"测试文件不存在: {test_file}")
        return

    print(f"测试文件: {test_file}")
    print(f"文件大小: {os.path.getsize(test_file)} 字节")
    
    try:
        # 创建一个简单的模拟翻译器
        class MockTranslator:
            def translate(self, text, terminology=None, source_lang="zh", target_lang="en"):
                return f"[TRANSLATED] {text}"

        translator = MockTranslator()

        # 创建DOC处理器
        processor = DOCProcessor(translator)
        
        # 测试文件转换
        print("\n开始测试DOC文件内容提取...")
        content = processor._convert_doc_to_text(test_file)
        
        if content:
            print(f"成功提取内容，长度: {len(content)} 字符")
            print(f"内容预览: {content[:200]}...")
        else:
            print("未能提取到内容")
            
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_doc_processing()
