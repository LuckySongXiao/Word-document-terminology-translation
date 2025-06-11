#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多行文本翻译问题
"""

import os
import sys
import json
import logging
from services.zhipuai_translator import ZhipuAITranslator

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
    config = load_api_config()
    if config and config.get('api_key'):
        try:
            translator = ZhipuAITranslator(config['api_key'])
            return translator
        except Exception as e:
            logger.error(f"智谱AI翻译器初始化失败: {e}")
            return None
    return None

def test_multiline_variations():
    """测试多行文本的不同变体"""
    
    translator = get_translator()
    if not translator:
        logger.error("无法初始化翻译器")
        return False
    
    logger.info("=== 测试多行文本翻译的不同变体 ===")
    
    # 测试用例
    test_cases = [
        {
            "name": "原始问题文本",
            "text": """备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
2、晶裂部分少子统一按照5＜x＞20μs进行分类；"""
        },
        {
            "name": "去掉备注标题",
            "text": """1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
2、晶裂部分少子统一按照5＜x＞20μs进行分类；"""
        },
        {
            "name": "改变编号格式",
            "text": """第一条：尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
第二条：晶裂部分少子统一按照5＜x＞20μs进行分类；"""
        },
        {
            "name": "使用项目符号",
            "text": """• 尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
• 晶裂部分少子统一按照5＜x＞20μs进行分类；"""
        },
        {
            "name": "普通段落",
            "text": """尾料按照端面少子进行分类，圆棒按照A面少子进行分类。
晶裂部分少子统一按照5＜x＞20μs进行分类。"""
        },
        {
            "name": "单行合并",
            "text": """备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；2、晶裂部分少子统一按照5＜x＞20μs进行分类；"""
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- 测试 {i}: {test_case['name']} ---")
        logger.info(f"原文: {test_case['text']}")
        
        try:
            translation = translator.translate(test_case['text'], {}, "zh", "en")
            logger.info(f"译文: {translation}")
            
            # 分析结果
            original_lines = [line.strip() for line in test_case['text'].split('\n') if line.strip()]
            translation_lines = [line.strip() for line in translation.split('\n') if line.strip()]
            
            result = {
                'name': test_case['name'],
                'original_lines': len(original_lines),
                'translated_lines': len(translation_lines),
                'complete': len(translation_lines) >= len(original_lines),
                'translation': translation
            }
            results.append(result)
            
            logger.info(f"原文行数: {len(original_lines)}, 译文行数: {len(translation_lines)}")
            if result['complete']:
                logger.info("✅ 翻译完整")
            else:
                logger.warning("❌ 翻译不完整")
                
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            results.append({
                'name': test_case['name'],
                'error': str(e)
            })
    
    # 总结结果
    logger.info("\n=== 测试结果总结 ===")
    complete_count = 0
    for result in results:
        if 'error' not in result:
            status = "✅ 完整" if result['complete'] else "❌ 不完整"
            logger.info(f"{result['name']}: {status} ({result['original_lines']}→{result['translated_lines']})")
            if result['complete']:
                complete_count += 1
        else:
            logger.error(f"{result['name']}: 错误 - {result['error']}")
    
    logger.info(f"\n完整翻译成功率: {complete_count}/{len([r for r in results if 'error' not in r])} ({complete_count/len([r for r in results if 'error' not in r])*100:.1f}%)")
    
    return complete_count > 0

def test_prompt_variations():
    """测试不同提示词对翻译的影响"""
    
    translator = get_translator()
    if not translator:
        logger.error("无法初始化翻译器")
        return False
    
    logger.info("\n=== 测试不同提示词的影响 ===")
    
    test_text = """备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
2、晶裂部分少子统一按照5＜x＞20μs进行分类；"""
    
    # 不同的提示词
    prompts = [
        None,  # 默认提示词
        "请逐行翻译以下内容，确保每一行都有对应的英文翻译：",
        "请完整翻译以下所有内容，包括备注和所有条目：",
        "请将以下中文文本完整翻译为英文，保持原有的格式和结构：",
        "这是技术文档的备注部分，请准确翻译每一条内容："
    ]
    
    for i, prompt in enumerate(prompts):
        logger.info(f"\n--- 提示词测试 {i+1} ---")
        if prompt:
            logger.info(f"提示词: {prompt}")
        else:
            logger.info("提示词: 默认")
        
        try:
            translation = translator.translate(test_text, {}, "zh", "en", prompt)
            logger.info(f"译文: {translation}")
            
            # 分析结果
            original_lines = [line.strip() for line in test_text.split('\n') if line.strip()]
            translation_lines = [line.strip() for line in translation.split('\n') if line.strip()]
            
            logger.info(f"原文行数: {len(original_lines)}, 译文行数: {len(translation_lines)}")
            if len(translation_lines) >= len(original_lines):
                logger.info("✅ 翻译完整")
            else:
                logger.warning("❌ 翻译不完整")
                
        except Exception as e:
            logger.error(f"翻译失败: {e}")

def main():
    logger.info("开始测试多行文本翻译问题...")
    
    # 测试不同的文本变体
    variation_success = test_multiline_variations()
    
    # 测试不同的提示词
    test_prompt_variations()
    
    logger.info("\n=== 总结 ===")
    if variation_success:
        logger.info("✅ 找到了可以完整翻译的文本格式")
    else:
        logger.error("❌ 所有文本格式都存在翻译不完整的问题")
    
    return variation_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
