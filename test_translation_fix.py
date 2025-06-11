#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试翻译修复效果
"""

import os
import sys
import json
import logging
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

def test_problematic_content():
    """测试问题内容的翻译"""
    
    translator = get_translator()
    if not translator:
        logger.error("无法初始化翻译器")
        return False
    
    # 测试内容：表格4最后单元格的完整内容
    test_content = """备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；
2、晶裂部分少子统一按照5＜x＞20μs进行分类；"""
    
    logger.info("=== 测试问题内容翻译 ===")
    logger.info(f"原始内容: {test_content}")
    
    try:
        # 使用完整参数调用翻译
        if hasattr(translator, 'translate'):
            # 直接调用翻译器的translate方法
            translation = translator.translate(test_content, {}, "zh", "en")
        else:
            # 如果没有translate方法，尝试translate_text
            translation = translator.translate_text(test_content, {}, "zh", "en")
        
        logger.info(f"翻译结果: {translation}")
        
        # 分析翻译结果
        original_lines = [line.strip() for line in test_content.split('\n') if line.strip()]
        translation_lines = [line.strip() for line in translation.split('\n') if line.strip()]
        
        logger.info(f"原文行数: {len(original_lines)}")
        logger.info(f"译文行数: {len(translation_lines)}")
        
        # 检查是否完整翻译
        if len(translation_lines) >= len(original_lines):
            logger.info("✅ 翻译完整！所有行都被翻译了")
            
            # 详细检查每行
            for i, orig_line in enumerate(original_lines):
                logger.info(f"原文第{i+1}行: {orig_line}")
                if i < len(translation_lines):
                    logger.info(f"译文第{i+1}行: {translation_lines[i]}")
                else:
                    logger.warning(f"译文缺少第{i+1}行")
        else:
            logger.warning(f"❌ 翻译不完整！原文{len(original_lines)}行，译文只有{len(translation_lines)}行")
            
            # 显示缺失的内容
            for i, orig_line in enumerate(original_lines):
                logger.info(f"原文第{i+1}行: {orig_line}")
                if i < len(translation_lines):
                    logger.info(f"译文第{i+1}行: {translation_lines[i]}")
                else:
                    logger.error(f"❌ 译文缺少第{i+1}行的翻译")
        
        return len(translation_lines) >= len(original_lines)
        
    except Exception as e:
        logger.error(f"翻译测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_individual_lines():
    """测试单独翻译每一行"""
    
    translator = get_translator()
    if not translator:
        logger.error("无法初始化翻译器")
        return False
    
    logger.info("\n=== 测试单独翻译每一行 ===")
    
    lines = [
        "备注：1、尾料按照端面少子进行分类，圆棒按照A面少子进行分类；",
        "2、晶裂部分少子统一按照5＜x＞20μs进行分类；"
    ]
    
    all_success = True
    
    for i, line in enumerate(lines, 1):
        logger.info(f"\n--- 测试第{i}行 ---")
        logger.info(f"原文: {line}")
        
        try:
            if hasattr(translator, 'translate'):
                translation = translator.translate(line, {}, "zh", "en")
            else:
                translation = translator.translate_text(line, {}, "zh", "en")
            
            logger.info(f"译文: {translation}")
            
            # 检查翻译是否成功
            if translation and translation != line and len(translation) > 5:
                logger.info(f"✅ 第{i}行翻译成功")
            else:
                logger.warning(f"❌ 第{i}行翻译可能失败")
                all_success = False
                
        except Exception as e:
            logger.error(f"第{i}行翻译失败: {e}")
            all_success = False
    
    return all_success

def main():
    logger.info("开始测试翻译修复效果...")
    
    # 测试完整内容翻译
    complete_success = test_problematic_content()
    
    # 测试单独行翻译
    individual_success = test_individual_lines()
    
    logger.info("\n=== 测试结果总结 ===")
    if complete_success:
        logger.info("✅ 完整内容翻译测试通过")
    else:
        logger.error("❌ 完整内容翻译测试失败")
    
    if individual_success:
        logger.info("✅ 单独行翻译测试通过")
    else:
        logger.error("❌ 单独行翻译测试失败")
    
    if complete_success and individual_success:
        logger.info("🎉 所有测试通过！翻译修复成功！")
        return True
    else:
        logger.error("💥 测试失败，需要进一步调试")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
