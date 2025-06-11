import os
import logging
import time
import json
import re
from typing import Dict, List, Any, Tuple
from .translator import TranslationService
import pandas as pd
from datetime import datetime
from utils.term_extractor import TermExtractor
from .translation_detector import TranslationDetector

logger = logging.getLogger(__name__)

class TXTProcessor:
    """TXT文本文件处理器"""
    
    def __init__(self, translator: TranslationService):
        self.translator = translator
        self.use_terminology = True  # 默认使用术语库
        self.preprocess_terms = True  # 是否预处理术语（默认启用）
        self.term_extractor = TermExtractor()  # 术语提取器
        self.translation_detector = TranslationDetector()  # 翻译检测器
        self.skip_translated_content = True  # 是否跳过已翻译内容（默认启用）
        self.export_pdf = False  # 是否导出PDF
        self.source_lang = "zh"  # 默认源语言为中文
        self.target_lang = "en"  # 默认目标语言为英文
        self.is_cn_to_foreign = True  # 默认翻译方向为中文→外语
        self.progress_callback = None  # 进度回调函数
        self.retry_count = 3  # 翻译失败重试次数
        self.retry_delay = 1  # 重试延迟（秒）
        self.output_format = "bilingual"  # 输出格式：bilingual（双语对照）或translation_only（仅翻译）

        # 配置日志记录器
        self.logger = logging.getLogger(__name__)
        self.web_logger = logging.getLogger('web_logger')

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback

    def _update_progress(self, progress: float, message: str):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(progress, message)
        
        # 记录进度到日志
        if progress >= 0:
            logger.info(f"进度: {progress*100:.1f}% - {message}")
        else:
            logger.error(f"进度: 错误 - {message}")

    def process_document(self, file_path: str, target_language: str, terminology: Dict, 
                        source_lang: str = "zh", target_lang: str = "en") -> str:
        """
        处理TXT文档翻译

        Args:
            file_path: 文件路径
            target_language: 目标语言名称（用于术语表查找）
            terminology: 术语词典
            source_lang: 源语言代码，默认为中文(zh)
            target_lang: 目标语言代码，默认为英文(en)

        Returns:
            str: 输出文件路径
        """
        # 更新进度：开始处理
        self._update_progress(0.01, "开始处理TXT文档...")

        # 设置翻译方向
        self.source_lang = source_lang
        self.target_lang = target_lang

        # 根据源语言和目标语言确定翻译方向
        self.is_cn_to_foreign = source_lang == "zh" or (source_lang == "auto" and target_lang != "zh")
        logger.info(f"翻译方向: {'中文→外语' if self.is_cn_to_foreign else '外语→中文'}")

        # 检查文件是否存在
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            raise Exception("文件不存在")

        # 创建输出目录
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "输出")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 生成输出文件名
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        time_stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        if self.output_format == "translation_only":
            output_path = os.path.join(output_dir, f"{file_name}_翻译_{time_stamp}.txt")
        else:
            output_path = os.path.join(output_dir, f"{file_name}_双语对照_{time_stamp}.txt")

        # 更新进度：读取文件
        self._update_progress(0.1, "读取TXT文件...")

        try:
            # 尝试不同的编码读取文件
            content = self._read_txt_file(file_path)
            
            # 更新进度：准备翻译
            self._update_progress(0.2, "准备翻译...")

            # 获取目标语言的术语库
            target_terminology = terminology.get(target_language, {}) if isinstance(terminology, dict) else {}
            
            # 翻译结果存储
            translation_results = []
            used_terminology = {}

            # 按段落分割文本
            paragraphs = self._split_into_paragraphs(content)
            total_paragraphs = len(paragraphs)
            
            logger.info(f"共找到 {total_paragraphs} 个段落需要翻译")

            # 更新进度：开始翻译
            self._update_progress(0.3, f"开始翻译 {total_paragraphs} 个段落...")

            # 翻译每个段落
            translated_paragraphs = []
            for i, paragraph in enumerate(paragraphs):
                if paragraph.strip():
                    # 更新进度
                    progress = 0.3 + (i / total_paragraphs) * 0.5
                    self._update_progress(progress, f"翻译第 {i+1}/{total_paragraphs} 个段落...")

                    # 翻译段落
                    translated_text = self._translate_paragraph(
                        paragraph, target_terminology, translation_results, used_terminology
                    )
                    
                    # 根据输出格式处理结果
                    if self.output_format == "translation_only":
                        translated_paragraphs.append(translated_text)
                    else:
                        # 双语对照格式
                        translated_paragraphs.append(f"【原文】{paragraph}")
                        translated_paragraphs.append(f"【译文】{translated_text}")
                        translated_paragraphs.append("")  # 空行分隔
                else:
                    # 保留空段落
                    translated_paragraphs.append(paragraph)

            # 更新进度：保存文件
            self._update_progress(0.8, "保存翻译后的文件...")

            # 保存翻译后的文件
            self._save_txt_file(output_path, translated_paragraphs)
            logger.info(f"文件已保存到: {output_path}")

            # 更新进度：导出结果
            self._update_progress(0.9, "导出翻译结果...")

            # 导出翻译结果到Excel
            if translation_results:
                self.export_to_excel(translation_results, file_path, target_language)

            # 如果使用了术语预处理，导出使用的术语
            if used_terminology:
                self.export_used_terminology(used_terminology, file_path)

            # 更新进度：完成
            self._update_progress(1.0, "TXT翻译完成！")

            return output_path

        except Exception as e:
            logger.error(f"处理TXT文件时出错: {str(e)}")
            raise Exception(f"处理TXT文件失败: {str(e)}")

    def _read_txt_file(self, file_path: str) -> str:
        """读取TXT文件，自动检测编码"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'ascii']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.info(f"成功使用 {encoding} 编码读取文件")
                return content
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"使用 {encoding} 编码读取文件失败: {str(e)}")
                continue
        
        # 如果所有编码都失败，尝试忽略错误
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            logger.warning("使用UTF-8编码并忽略错误读取文件")
            return content
        except Exception as e:
            raise Exception(f"无法读取文件 {file_path}: {str(e)}")

    def _save_txt_file(self, file_path: str, paragraphs: List[str]):
        """保存TXT文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(paragraphs))
            logger.info(f"TXT文件已保存: {file_path}")
        except Exception as e:
            raise Exception(f"保存TXT文件失败: {str(e)}")

    def _split_into_paragraphs(self, content: str) -> List[str]:
        """将文本分割为段落"""
        # 按双换行符分割段落
        paragraphs = re.split(r'\n\s*\n', content)
        
        # 如果没有双换行符，按单换行符分割
        if len(paragraphs) == 1:
            paragraphs = content.split('\n')
        
        return paragraphs

    def _translate_paragraph(self, text: str, terminology: Dict,
                           translation_results: List, used_terminology: Dict) -> str:
        """翻译单个段落"""
        try:
            original_text = text

            # 检查是否应该跳过翻译（已翻译内容检测）
            if self.skip_translated_content:
                should_skip, reason = self.translation_detector.should_skip_translation(
                    text, self.source_lang, self.target_lang
                )
                if should_skip:
                    logger.info(f"跳过TXT段落翻译: {reason} - {text[:50]}...")
                    return text  # 返回原文

            # 使用新的直接术语替换方法（如果启用）
            if self.preprocess_terms and terminology:
                # 直接替换术语为目标语言，避免占位符机制
                text = self._preprocess_terminology_direct(text, terminology)
                logger.info(f"直接替换术语后的文本: {text[:100]}...")

            # 翻译文本（不再需要术语库，因为已经直接替换了）
            translated_text = self.translator.translate(
                text, {}, self.source_lang, self.target_lang
            )

            # 记录翻译结果
            translation_results.append({
                "原文": original_text,
                "译文": translated_text,
                "源语言": self.source_lang,
                "目标语言": self.target_lang
            })

            return translated_text

        except Exception as e:
            logger.error(f"翻译段落失败: {str(e)}")
            # 翻译失败时返回原文
            return original_text

    def _preprocess_terminology_direct(self, text: str, terminology: Dict) -> str:
        """直接替换术语为目标语言，避免占位符机制"""
        if not terminology:
            return text

        processed_text = text

        # 按术语长度排序，优先处理长术语
        sorted_terms = sorted(terminology.items(), key=lambda x: len(x[0]), reverse=True)

        for term, translation in sorted_terms:
            if term in processed_text and translation:
                processed_text = processed_text.replace(term, translation)

        return processed_text

    def _preprocess_terminology(self, text: str, terminology: Dict) -> Tuple[str, Dict]:
        """预处理术语，使用占位符替换（保留原有方法以兼容性）"""
        used_terms = {}
        processed_text = text

        # 按术语长度排序，优先处理长术语
        sorted_terms = sorted(terminology.items(), key=lambda x: len(x[0]), reverse=True)

        for term, translation in sorted_terms:
            if term in processed_text:
                placeholder = f"__TERM_{len(used_terms)}__"
                processed_text = processed_text.replace(term, placeholder)
                used_terms[placeholder] = {"term": term, "translation": translation}

        return processed_text, used_terms

    def export_to_excel(self, translation_results: List[Dict], file_path: str, target_language: str = None):
        """将翻译结果导出到Excel文件"""
        try:
            # 创建输出目录
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "输出")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 获取文件名
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            time_stamp = datetime.now().strftime("%Y%m%d%H%M%S")

            # 根据目标语言生成文件名
            lang_suffix = f"_{target_language}" if target_language else ""
            excel_path = os.path.join(output_dir, f"{file_name}_翻译结果{lang_suffix}_{time_stamp}.xlsx")

            # 转换翻译结果为DataFrame
            df = pd.DataFrame(translation_results)

            # 保存到Excel
            df.to_excel(excel_path, index=False, engine='openpyxl')
            logger.info(f"翻译结果已导出到: {excel_path}")

        except Exception as e:
            logger.error(f"导出翻译结果到Excel失败: {str(e)}")

    def export_used_terminology(self, used_terminology: Dict, file_path: str):
        """导出使用的术语到Excel文件"""
        try:
            if not used_terminology:
                return

            # 创建输出目录
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "输出")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 获取文件名
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            time_stamp = datetime.now().strftime("%Y%m%d%H%M%S")
            excel_path = os.path.join(output_dir, f"{file_name}_使用术语_{time_stamp}.xlsx")

            # 准备术语数据
            terminology_data = []
            for placeholder, term_info in used_terminology.items():
                terminology_data.append({
                    "原术语": term_info["term"],
                    "翻译": term_info["translation"],
                    "占位符": placeholder
                })

            # 转换为DataFrame并保存
            df = pd.DataFrame(terminology_data)
            df.to_excel(excel_path, index=False, engine='openpyxl')
            logger.info(f"使用的术语已导出到: {excel_path}")

        except Exception as e:
            logger.error(f"导出使用术语失败: {str(e)}")
