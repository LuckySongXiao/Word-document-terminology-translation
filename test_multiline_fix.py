#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多行文本翻译修复效果
"""

import os
import sys
import json
import logging
from services.document_processor import DocumentProcessor
from services.zhipuai_translator import ZhipuAITranslator
from services.ollama_translator import OllamaTranslator

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_api_config():
    """加载API配置"""
    try:
        with open('API_config/zhipu_api.json', 'r', encoding='utf-8') as f:
            zhipu_config = json.load(f)
        return zhipu_config
    except Exception as e:
        logger.error(f"加载API配置失败: {e}")
        return None

def get_translator():
    """获取翻译器"""
    # 尝试使用智谱AI
    config = load_api_config()
    if config and config.get('api_key'):
        try:
            translator = ZhipuAITranslator(config['api_key'])
            # 测试连接
            test_result = translator.translate("测试", {}, "zh", "en")
            if test_result and test_result != "测试":
                logger.info("使用智谱AI翻译器")
                return translator
        except Exception as e:
            logger.warning(f"智谱AI翻译器初始化失败: {e}")
    
    # 回退到本地Ollama
    try:
        # 从配置文件加载Ollama配置
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        ollama_config = config.get("fallback_translator", {})
        model = ollama_config.get("model", "qwen2.5:7b")
        api_url = ollama_config.get("api_url", "http://localhost:11434")
        
        translator = OllamaTranslator(
            model=model,
            api_url=api_url,
            model_list_timeout=10,
            translate_timeout=60
        )
        logger.info("使用本地Ollama翻译器")
        return translator
    except Exception as e:
        logger.error(f"Ollama翻译器初始化失败: {e}")
        return None

def test_multiline_preprocessing():
    """测试多行文本预处理功能"""
    
    translator = get_translator()
    if not translator:
        logger.error("无法初始化翻译器")
        return False
    
    # 创建文档处理器
    processor = DocumentProcessor(translator)
    processor.source_lang = "zh"
    processor.target_lang = "en"
    
    logger.info("=== 测试多行文本预处理功能 ===")
    
    # 测试用例
    test_cases = [
        {
            "name": "原始问题文本（多行）",
            "text": """备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
2、晶裂部分少子统一按照5＜x＞20μs进行分类；"""
        },
        {
            "name": "单行文本",
            "text": "这是一行简单的测试文本。"
        },
        {
            "name": "三行文本",
            "text": """第一行：这是第一条内容；
第二行：这是第二条内容；
第三行：这是第三条内容。"""
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试 {i}: {test_case['name']} ---")
        logger.info(f"原始文本: {test_case['text']}")
        
        try:
            # 测试预处理
            processed_text, is_multiline = processor._preprocess_multiline_text(test_case['text'])
            logger.info(f"预处理结果: is_multiline={is_multiline}")
            logger.info(f"处理后文本: {processed_text}")
            
            # 测试翻译
            if hasattr(translator, 'translate'):
                translation = translator.translate(processed_text, {}, "zh", "en")
            else:
                translation = translator.translate_text(processed_text, {}, "zh", "en")
            
            logger.info(f"翻译结果: {translation}")
            
            # 测试后处理
            if is_multiline:
                final_translation = processor._postprocess_multiline_translation(translation)
                logger.info(f"后处理结果: {final_translation}")
            else:
                final_translation = translation
                logger.info("单行文本，无需后处理")
            
            # 分析结果
            original_lines = [line.strip() for line in test_case['text'].split('\n') if line.strip()]
            final_lines = [line.strip() for line in final_translation.split('\n') if line.strip()]
            
            result = {
                'name': test_case['name'],
                'original_lines': len(original_lines),
                'translated_lines': len(final_lines),
                'complete': len(final_lines) >= len(original_lines),
                'is_multiline': is_multiline,
                'final_translation': final_translation
            }
            results.append(result)
            
            logger.info(f"原文行数: {len(original_lines)}, 译文行数: {len(final_lines)}")
            if result['complete']:
                logger.info("✅ 翻译完整")
            else:
                logger.warning("❌ 翻译不完整")
                
        except Exception as e:
            logger.error(f"测试失败: {e}")
            results.append({
                'name': test_case['name'],
                'error': str(e)
            })
    
    # 总结结果
    logger.info("\n=== 测试结果总结 ===")
    complete_count = 0
    multiline_complete_count = 0
    multiline_total = 0
    
    for result in results:
        if 'error' not in result:
            status = "✅ 完整" if result['complete'] else "❌ 不完整"
            logger.info(f"{result['name']}: {status} ({result['original_lines']}→{result['translated_lines']})")
            
            if result['complete']:
                complete_count += 1
            
            if result['is_multiline']:
                multiline_total += 1
                if result['complete']:
                    multiline_complete_count += 1
        else:
            logger.error(f"{result['name']}: 错误 - {result['error']}")
    
    total_tests = len([r for r in results if 'error' not in r])
    logger.info(f"\n总体成功率: {complete_count}/{total_tests} ({complete_count/total_tests*100:.1f}%)")
    
    if multiline_total > 0:
        logger.info(f"多行文本成功率: {multiline_complete_count}/{multiline_total} ({multiline_complete_count/multiline_total*100:.1f}%)")
    
    return complete_count == total_tests and multiline_complete_count == multiline_total

def test_document_translation():
    """测试完整的文档翻译流程"""
    
    logger.info("\n=== 测试完整文档翻译流程 ===")
    
    # 检查原始文档是否存在
    input_file = "单晶电阻率管控技术标准.docx"
    if not os.path.exists(input_file):
        logger.error(f"原始文档不存在: {input_file}")
        return False
    
    try:
        translator = get_translator()
        if not translator:
            logger.error("无法初始化翻译器")
            return False
        
        # 创建文档处理器
        processor = DocumentProcessor(translator)
        processor.source_lang = "zh"
        processor.target_lang = "en"
        processor.output_format = "bilingual"
        
        # 加载术语库
        terminology_file = "术语库.xlsx"
        if os.path.exists(terminology_file):
            terminology = processor.load_terminology(terminology_file)
            logger.info(f"加载术语库: {len(terminology)} 个术语")
        else:
            terminology = {}
            logger.warning("术语库文件不存在，使用空术语库")
        
        # 翻译文档
        logger.info("开始翻译文档...")
        output_path = processor.translate_document(input_file, terminology, "en")
        
        if output_path and os.path.exists(output_path):
            logger.info(f"✅ 文档翻译成功: {output_path}")
            return True
        else:
            logger.error("❌ 文档翻译失败")
            return False
            
    except Exception as e:
        logger.error(f"文档翻译测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    logger.info("开始测试多行文本翻译修复效果...")
    
    # 测试预处理功能
    preprocessing_success = test_multiline_preprocessing()
    
    # 测试完整文档翻译
    document_success = test_document_translation()
    
    logger.info("\n=== 最终测试结果 ===")
    if preprocessing_success:
        logger.info("✅ 多行文本预处理测试通过")
    else:
        logger.error("❌ 多行文本预处理测试失败")
    
    if document_success:
        logger.info("✅ 完整文档翻译测试通过")
    else:
        logger.error("❌ 完整文档翻译测试失败")
    
    if preprocessing_success and document_success:
        logger.info("🎉 所有测试通过！多行文本翻译修复成功！")
        return True
    else:
        logger.error("💥 部分测试失败，需要进一步调试")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
