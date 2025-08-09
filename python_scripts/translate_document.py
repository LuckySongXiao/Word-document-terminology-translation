#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
C#调用的Python翻译脚本
"""

import sys
import json
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from services.translator import TranslationService
    from services.document_processor import DocumentProcessor
    from services.document_factory import DocumentProcessorFactory
    from utils.terminology import load_terminology
except ImportError as e:
    print(json.dumps({
        "success": False,
        "error_message": f"导入模块失败: {str(e)}"
    }))
    sys.exit(1)

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('translation.log', encoding='utf-8'),
            logging.StreamHandler(sys.stderr)
        ]
    )

def translate_document(config):
    """翻译文档"""
    try:
        # 创建翻译服务
        translator = TranslationService(
            preferred_engine=config.get('engine', 'zhipuai'),
            preferred_model=config.get('model', 'GLM-4-Flash-250414')
        )
        
        # 创建文档处理器
        file_path = config['file_path']
        doc_processor = DocumentProcessorFactory.create_processor(file_path, translator)
        
        # 设置选项
        doc_processor.use_terminology = config.get('use_terminology', True)
        doc_processor.preprocess_terms = config.get('preprocess_terms', True)
        doc_processor.export_pdf = config.get('export_pdf', False)
        doc_processor.output_format = config.get('output_format', 'bilingual')
        
        # 加载术语表
        terminology = load_terminology()
        
        # 设置进度回调
        progress_info = {'progress': 0, 'message': ''}
        
        def progress_callback(progress, message):
            progress_info['progress'] = int(progress * 100)
            progress_info['message'] = message
            # 输出进度信息到stderr，这样不会干扰最终的JSON输出
            print(json.dumps({
                "type": "progress",
                "progress": progress_info['progress'],
                "message": message
            }), file=sys.stderr)
        
        doc_processor.set_progress_callback(progress_callback)
        
        # 执行翻译
        output_path = doc_processor.process_document(
            file_path,
            config.get('target_language', '英语'),
            terminology,
            source_lang=config.get('source_language', 'zh'),
            target_lang=config.get('target_language_code', 'en')
        )
        
        # 返回成功结果
        result = {
            "success": True,
            "output_path": output_path,
            "progress": 100,
            "status_message": "翻译完成"
        }
        
        # 如果导出了PDF，添加PDF路径
        if doc_processor.export_pdf:
            pdf_path = os.path.splitext(output_path)[0] + ".pdf"
            if os.path.exists(pdf_path):
                result["pdf_path"] = pdf_path
        
        return result
        
    except Exception as e:
        logging.error(f"翻译失败: {str(e)}")
        return {
            "success": False,
            "error_message": str(e),
            "progress": 0,
            "status_message": "翻译失败"
        }

def main():
    """主函数"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error_message": "参数错误：需要配置文件路径"
        }))
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    try:
        # 读取配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 设置日志
        setup_logging()
        
        # 执行翻译
        result = translate_document(config)
        
        # 输出结果
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error_message": f"执行失败: {str(e)}"
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()
