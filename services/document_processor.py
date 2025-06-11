import os
import logging
import time
import json
import re
from docx import Document
from typing import Dict, List, Any, Tuple
from .translator import TranslationService
import pandas as pd
from datetime import datetime
from utils.term_extractor import TermExtractor
from docx2pdf import convert as docx2pdf_convert
from .translation_detector import TranslationDetector

logger = logging.getLogger(__name__)

class DocumentProcessor:
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
        self.output_format = "bilingual"  # 输出格式：双语对照模式

        # 配置日志记录器
        self.logger = logging.getLogger(__name__)
        self.web_logger = logging.getLogger('web_logger')

        # 初始化日志配置
        self.logger.info("DocumentProcessor initialized")
        self.web_logger.info("Translation service ready")
        # 数学公式正则表达式模式
        self.latex_patterns = [
            r'\$\$(.*?)\$\$',  # 行间公式 $$...$$
            r'\$(.*?)\$',      # 行内公式 $...$
            r'\\begin\{equation\}(.*?)\\end\{equation\}',  # equation环境
            r'\\begin\{align\}(.*?)\\end\{align\}',        # align环境
            r'\\begin\{eqnarray\}(.*?)\\end\{eqnarray\}'   # eqnarray环境
        ]

    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback

    def process_document(self, file_path: str, target_language: str, terminology: Dict, source_lang: str = "zh", target_lang: str = "en") -> str:
        """
        处理文档翻译

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
        self._update_progress(0.01, "开始处理文档...")

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

        # 在程序根目录下创建输出目录
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "输出")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 获取输出路径，添加时间戳避免文件名冲突
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        time_stamp = time.strftime("%Y%m%d%H%M%S")
        output_file_name = f"{file_name}_带翻译_{time_stamp}.docx"
        output_path = os.path.join(output_dir, output_file_name)

        # 更新进度：检查文件
        self._update_progress(0.05, "检查文件权限...")

        # 复制并处理文档
        try:
            # 检查文件是否可写入
            try:
                with open(file_path, 'rb') as f:
                    # 可以打开源文件
                    pass
            except PermissionError:
                logger.error(f"无法读取源文件，文件可能被占用: {file_path}")
                raise Exception(f"无法读取源文件，文件可能被占用。请确保文件未被其他程序（如Word）打开。")

            # 检查目标目录是否可写入
            try:
                test_file = os.path.join(output_dir, "__test_write__.tmp")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except (PermissionError, IOError) as e:
                logger.error(f"无法写入输出目录: {output_dir}, 错误: {str(e)}")
                raise Exception(f"无法写入输出目录，请检查权限或以管理员身份运行程序。")

            # 更新进度：复制文档
            self._update_progress(0.1, "复制文档...")
            self.web_logger.info(f"Starting to copy document: {os.path.basename(file_path)}")

            # 创建Word文档
            doc = self._copy_document(file_path, output_path)
            logger.info(f"成功复制原文档到: {output_path}")
            self.web_logger.info(f"Document copied successfully to: {os.path.basename(output_path)}")
        except Exception as e:
            logger.error(f"复制文档失败: {str(e)}")
            raise Exception(f"复制文档失败: {str(e)}")

        # 更新进度：加载术语库
        self._update_progress(0.15, "加载术语库...")

        # 获取选定语言的术语表
        target_terminology = terminology.get(target_language, {})
        logger.info(f"使用 {target_language} 术语表，包含 {len(target_terminology)} 个术语")

        # 如果术语表为空但术语库不为空，尝试使用其他方式获取术语
        if not target_terminology and terminology:
            # 检查是否有英语术语表
            if "英语" in terminology and target_language == "en":
                target_terminology = terminology["英语"]
                logger.info(f"使用英语术语表替代，包含 {len(target_terminology)} 个术语")
            # 检查是否有日语术语表
            elif "日语" in terminology and target_language == "ja":
                target_terminology = terminology["日语"]
                logger.info(f"使用日语术语表替代，包含 {len(target_terminology)} 个术语")
            # 检查是否有韩语术语表
            elif "韩语" in terminology and target_language == "ko":
                target_terminology = terminology["韩语"]
                logger.info(f"使用韩语术语表替代，包含 {len(target_terminology)} 个术语")
            # 检查是否有德语术语表
            elif "德语" in terminology and target_language == "de":
                target_terminology = terminology["德语"]
                logger.info(f"使用德语术语表替代，包含 {len(target_terminology)} 个术语")
            # 检查是否有法语术语表
            elif "法语" in terminology and target_language == "fr":
                target_terminology = terminology["法语"]
                logger.info(f"使用法语术语表替代，包含 {len(target_terminology)} 个术语")
            # 检查是否有西班牙语术语表
            elif "西班牙语" in terminology and target_language == "es":
                target_terminology = terminology["西班牙语"]
                logger.info(f"使用西班牙语术语表替代，包含 {len(target_terminology)} 个术语")
            else:
                logger.warning(f"无法找到匹配的术语表，将使用空术语表")

        # 创建一个列表来收集翻译结果
        translation_results = []

        try:
            # 更新进度：处理表格
            self._update_progress(0.2, "处理文档表格...")

            # 处理表格
            self._process_tables(doc, target_terminology, translation_results)

            # 更新进度：处理段落
            self._update_progress(0.4, "处理文档段落...")

            # 处理段落
            self._process_paragraphs(doc, target_terminology, translation_results)

            # 更新进度：保存文档
            self._update_progress(0.8, "保存文档...")

            # 保存文档
            try:
                doc.save(output_path)
                logger.info(f"文件已保存到: {output_path}")
            except PermissionError:
                new_output_path = os.path.join(output_dir, f"{file_name}_带翻译_retry_{time_stamp}.docx")
                logger.warning(f"保存文件失败，尝试使用新文件名: {new_output_path}")
                doc.save(new_output_path)
                logger.info(f"文件已保存到: {new_output_path}")
                output_path = new_output_path

            # 保存JSON结果
            json_output = os.path.join(output_dir, f"{file_name}_翻译结果_{time_stamp}.json")
            with open(json_output, 'w', encoding='utf-8') as f:
                json.dump({"status": "success", "file": output_path}, f, ensure_ascii=False, indent=2)

            # 更新进度：导出Excel
            self._update_progress(0.85, "导出翻译对照表...")

            # 翻译完成后，导出Excel文件
            if translation_results:
                self.export_to_excel(translation_results, file_path, target_language)

            # 如果需要导出PDF，则将Word文档转换为PDF
            if self.export_pdf:
                # 更新进度：导出PDF
                self._update_progress(0.9, "导出PDF文件...")

                pdf_path = self.export_to_pdf(output_path)
                logger.info(f"PDF文件已保存到: {pdf_path}")
                # 更新JSON结果，添加PDF文件路径
                with open(json_output, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                json_data["pdf_file"] = pdf_path
                with open(json_output, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)

            # 更新进度：完成
            self._update_progress(1.0, "翻译完成！")

            return output_path

        except Exception as e:
            logger.error(f"翻译过程出错: {str(e)}")
            # 更新进度：出错
            self._update_progress(-1, f"翻译出错: {str(e)}")
            raise

    def _copy_document(self, source_path: str, target_path: str) -> Document:
        """复制文档"""
        import threading

        def load_document():
            """在单独线程中加载文档"""
            try:
                self.logger.info(f"开始加载Word文档: {source_path}")
                self.web_logger.info(f"Loading Word document: {os.path.basename(source_path)}")

                # 检查文件大小
                file_size = os.path.getsize(source_path)
                self.logger.info(f"文档大小: {file_size / (1024*1024):.2f} MB")

                if file_size > 50 * 1024 * 1024:  # 50MB
                    self.logger.warning("文档较大，加载可能需要较长时间")
                    self.web_logger.info("Large document detected, loading may take longer...")

                # 加载文档
                doc = Document(source_path)
                self.logger.info("文档加载成功，开始保存副本")
                self.web_logger.info("Document loaded successfully, saving copy...")

                # 保存副本
                doc.save(target_path)
                self.logger.info(f"文档副本已保存到: {target_path}")

                # 重新加载副本以确保数据完整性
                return Document(target_path)

            except Exception as e:
                self.logger.error(f"加载文档时出错: {str(e)}")
                self.web_logger.error(f"Error loading document: {str(e)}")
                raise

        try:
            # 使用线程加载文档，避免阻塞主线程
            result = [None]
            exception = [None]

            def worker():
                try:
                    result[0] = load_document()
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()

            # 等待最多60秒
            thread.join(timeout=60)

            if thread.is_alive():
                self.logger.error("文档加载超时（60秒）")
                self.web_logger.error("Document loading timeout (60 seconds)")
                raise TimeoutError("文档加载超时，请检查文档是否被其他程序占用或文档过大")

            if exception[0]:
                raise exception[0]

            if result[0] is None:
                raise Exception("文档加载失败，未知错误")

            return result[0]

        except Exception as e:
            error_msg = str(e)
            if "PermissionError" in error_msg or "Permission denied" in error_msg:
                raise Exception("无法访问文档文件，请确保文件未被Word或其他程序打开，或以管理员身份运行程序")
            elif "TimeoutError" in error_msg or "timeout" in error_msg.lower():
                raise Exception("文档加载超时，可能是文档过大或被其他程序占用，请稍后重试")
            elif "BadZipFile" in error_msg or "zipfile" in error_msg.lower():
                raise Exception("文档文件损坏或格式不正确，请检查文件是否为有效的Word文档")
            else:
                raise Exception(f"加载文档失败: {error_msg}")

    def _should_skip_translation(self, text: str) -> bool:
        """判断是否应该跳过翻译的内容"""
        # 如果禁用了跳过已翻译内容功能，只进行基本检查
        if not self.skip_translated_content:
            if not text or not text.strip():
                return True
            # 只跳过明显的非文本内容（数字、代码等）
            should_skip, reason = self.translation_detector.should_skip_translation(text, self.source_lang, self.target_lang)
            if should_skip and any(keyword in reason for keyword in ["纯数字", "代码", "URL", "邮箱"]):
                self.logger.info(f"跳过非文本内容: {reason} - {text[:50]}...")
                return True
            return False

        # 使用新的翻译检测器
        should_skip, reason = self.translation_detector.should_skip_translation(text, self.source_lang, self.target_lang)
        if should_skip:
            self.logger.info(f"跳过翻译内容: {reason} - {text[:50]}...")
            return True

        return False

    def _process_tables(self, doc: Document, terminology: Dict, translation_results: list) -> None:
        """处理文档中的表格"""
        self.logger.info("开始处理文档表格")
        self.web_logger.info("Processing document tables...")

        # 如果启用了术语预处理，先收集所有使用的术语
        used_terminology = {}
        if self.preprocess_terms:
            self.logger.info("=== 表格术语预处理已启用，开始收集术语 ===")
            self.logger.info(f"翻译方向: {self.source_lang} -> {self.target_lang}")
            self.logger.info(f"术语库大小: {len(terminology)} 个术语")

            # 显示术语库样本
            if terminology:
                sample_terms = list(terminology.items())[:5]
                self.logger.info(f"术语库样本（前5个）: {sample_terms}")

            # 对于外语→中文翻译模式，预先将术语库键值对调并缓存
            if self.source_lang != "zh":
                self.logger.info("外语→中文翻译模式，预先对调术语库键值并缓存...")
                self.reversed_terminology = self._create_reversed_terminology(terminology)
                self.logger.info(f"对调后的术语库大小: {len(self.reversed_terminology)} 个术语")

                # 显示对调后的术语库样本
                if self.reversed_terminology:
                    reversed_sample = list(self.reversed_terminology.items())[:5]
                    self.logger.info(f"对调后术语库样本（前5个）: {reversed_sample}")
            else:
                self.reversed_terminology = None

            # 先遍历所有表格内容，收集使用的术语
            table_count = len(doc.tables)
            self.logger.info(f"开始分析 {table_count} 个表格中的术语...")

            for table_idx, table in enumerate(doc.tables, 1):
                self.web_logger.info(f"Processing table {table_idx}/{table_count}")
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            try:
                                # 根据翻译方向选择不同的术语提取方法
                                if self.source_lang == "zh":
                                    # 中文 → 外语
                                    self.logger.info(f"从中文表格单元格提取术语: {cell.text[:50]}...")
                                    cell_terms = self.term_extractor.extract_terms(cell.text, terminology)
                                    self.logger.info(f"从中文文本提取术语: {len(cell_terms)} 个")
                                else:
                                    # 外语 → 中文，使用缓存的反向术语库
                                    self.logger.info(f"从外语表格单元格提取术语: {cell.text[:50]}...")
                                    if hasattr(self, 'reversed_terminology') and self.reversed_terminology:
                                        # 使用缓存的反向术语库进行高效匹配
                                        cell_terms = self.term_extractor.extract_foreign_terms_from_reversed_dict(cell.text, self.reversed_terminology)
                                        self.logger.info(f"从外语文本提取术语（使用缓存）: {len(cell_terms)} 个")
                                    else:
                                        # 回退到原始方法
                                        cell_terms = self.term_extractor.extract_foreign_terms_by_chinese_values(cell.text, terminology)
                                        self.logger.info(f"从外语文本提取术语（原始方法）: {len(cell_terms)} 个")

                                # 显示提取到的术语
                                if cell_terms:
                                    self.logger.info(f"表格单元格提取到的术语: {list(cell_terms.items())[:3]}")

                                # 更新使用的术语词典
                                used_terminology.update(cell_terms)
                            except Exception as e:
                                self.logger.error(f"术语提取失败: {str(e)}")
                                self.web_logger.error(f"Term extraction failed: {str(e)}")

            self.logger.info(f"从表格中提取了 {len(used_terminology)} 个术语")
            self.web_logger.info(f"Extracted {len(used_terminology)} terms from tables")

        # 处理表格翻译
        if self.skip_translated_content:
            # 使用双行检测处理表格
            self._process_tables_with_line_detection(doc, terminology, used_terminology, translation_results)
        else:
            # 传统方式处理表格
            self._process_tables_traditional(doc, terminology, used_terminology, translation_results)

    def _process_tables_with_line_detection(self, doc: Document, terminology: Dict, used_terminology: Dict, translation_results: List) -> None:
        """使用双行检测处理表格翻译 - 确保逐个单元格检查，无遗漏"""
        logger.info("开始使用双行检测处理表格翻译")

        for table_idx, table in enumerate(doc.tables):
            logger.info(f"处理表格 {table_idx + 1}/{len(doc.tables)}")

            # 创建单元格处理状态跟踪
            processed_cells = set()
            processed_cell_objects = set()  # 跟踪已处理的单元格对象（用于合并单元格）
            total_cells = 0

            # 先统计总单元格数
            for row_idx, row in enumerate(table.rows):
                for cell_idx, cell in enumerate(row.cells):
                    if cell.text.strip():
                        total_cells += 1

            logger.info(f"表格 {table_idx + 1} 包含 {total_cells} 个非空单元格")

            # 逐行逐列处理，确保每个单元格都被检查
            for row_idx, row in enumerate(table.rows):
                logger.info(f"处理表格 {table_idx + 1} 第 {row_idx + 1} 行")

                cells = row.cells
                cell_idx = 0

                while cell_idx < len(cells):
                    current_cell = cells[cell_idx]
                    current_text = current_cell.text.strip()
                    cell_position = (table_idx, row_idx, cell_idx)

                    # 跳过空单元格
                    if not current_text:
                        cell_idx += 1
                        continue

                    # 检查是否已经处理过（避免重复处理）
                    if cell_position in processed_cells:
                        cell_idx += 1
                        continue

                    # 检查是否是合并单元格（通过对象ID检测）
                    cell_object_id = id(current_cell)
                    if cell_object_id in processed_cell_objects:
                        logger.info(f"跳过合并单元格 [{row_idx + 1}, {cell_idx + 1}]: 已处理过相同对象 (ID={cell_object_id})")
                        processed_cells.add(cell_position)
                        cell_idx += 1
                        continue

                    logger.info(f"检查单元格 [{row_idx + 1}, {cell_idx + 1}]: {current_text[:30]}...")

                    # 尝试与右侧单元格进行双行检测
                    translation_pair_found = False
                    if cell_idx + 1 < len(cells):
                        next_cell = cells[cell_idx + 1]
                        next_text = next_cell.text.strip()
                        next_position = (table_idx, row_idx, cell_idx + 1)

                        if next_text and next_position not in processed_cells:
                            # 双行检测：判断是否构成翻译对
                            is_translation_pair, pair_reason = self.translation_detector._is_translation_pair(
                                current_text, next_text, self.source_lang, self.target_lang
                            )

                            if is_translation_pair:
                                logger.info(f"跳过表格翻译对: {pair_reason}")
                                logger.info(f"  单元格 [{row_idx + 1}, {cell_idx + 1}]: {current_text[:30]}...")
                                logger.info(f"  单元格 [{row_idx + 1}, {cell_idx + 2}]: {next_text[:30]}...")

                                # 标记两个单元格为已处理
                                processed_cells.add(cell_position)
                                processed_cells.add(next_position)
                                translation_pair_found = True
                                cell_idx += 2  # 跳过两个单元格
                                continue

                    # 如果没有找到翻译对，检查单个单元格是否应该跳过
                    if not translation_pair_found:
                        should_skip, reason = self.translation_detector.should_skip_translation(
                            current_text, self.source_lang, self.target_lang
                        )

                        if should_skip:
                            logger.info(f"跳过表格单元格翻译: {reason} - 单元格 [{row_idx + 1}, {cell_idx + 1}]: {current_text[:30]}...")
                            processed_cells.add(cell_position)
                            cell_idx += 1
                            continue

                        # 翻译当前单元格
                        logger.info(f"翻译表格单元格 [{row_idx + 1}, {cell_idx + 1}]: {current_text[:30]}...")
                        self._translate_single_cell(current_cell, used_terminology, translation_results, terminology)
                        processed_cells.add(cell_position)
                        processed_cell_objects.add(cell_object_id)  # 记录已处理的单元格对象
                        cell_idx += 1

            # 验证是否所有单元格都被处理
            actual_processed = len(processed_cells)
            logger.info(f"表格 {table_idx + 1} 处理完成: 处理了 {actual_processed} 个单元格")

            # 如果处理的单元格数量不匹配，进行补充检查
            if actual_processed < total_cells:
                logger.warning(f"表格 {table_idx + 1} 可能有遗漏，进行补充检查...")
                self._verify_table_completeness(table, table_idx, processed_cells, used_terminology, translation_results, terminology)

    def _verify_table_completeness(self, table, table_idx: int, processed_cells: set, used_terminology: Dict, translation_results: List, terminology: Dict) -> None:
        """验证表格处理的完整性，确保没有遗漏任何单元格"""
        logger.info(f"验证表格 {table_idx + 1} 的处理完整性...")

        missed_cells = []

        for row_idx, row in enumerate(table.rows):
            for cell_idx, cell in enumerate(row.cells):
                cell_text = cell.text.strip()
                cell_position = (table_idx, row_idx, cell_idx)

                if cell_text and cell_position not in processed_cells:
                    missed_cells.append((row_idx, cell_idx, cell_text, cell))

        if missed_cells:
            logger.warning(f"发现 {len(missed_cells)} 个遗漏的单元格，正在补充处理...")

            for row_idx, cell_idx, cell_text, cell in missed_cells:
                logger.info(f"补充处理遗漏的单元格 [{row_idx + 1}, {cell_idx + 1}]: {cell_text[:30]}...")

                # 检查是否应该跳过翻译
                should_skip, reason = self.translation_detector.should_skip_translation(
                    cell_text, self.source_lang, self.target_lang
                )

                if should_skip:
                    logger.info(f"跳过遗漏单元格翻译: {reason} - 单元格 [{row_idx + 1}, {cell_idx + 1}]: {cell_text[:30]}...")
                else:
                    # 翻译遗漏的单元格
                    logger.info(f"翻译遗漏的单元格 [{row_idx + 1}, {cell_idx + 1}]: {cell_text[:30]}...")
                    self._translate_single_cell(cell, used_terminology, translation_results, terminology)
        else:
            logger.info(f"表格 {table_idx + 1} 处理完整，无遗漏单元格")

    def _process_tables_traditional(self, doc: Document, terminology: Dict, used_terminology: Dict, translation_results: List) -> None:
        """传统方式处理表格翻译（不使用双行检测）- 确保逐个单元格检查，无遗漏"""
        logger.info("开始使用传统方式处理表格翻译")

        for table_idx, table in enumerate(doc.tables):
            logger.info(f"处理表格 {table_idx + 1}/{len(doc.tables)}")

            # 统计总单元格数
            total_cells = 0
            processed_cells = 0
            processed_cell_objects = set()  # 跟踪已处理的单元格对象（用于合并单元格）

            for row_idx, row in enumerate(table.rows):
                for cell_idx, cell in enumerate(row.cells):
                    cell_text = cell.text.strip()
                    if cell_text:
                        total_cells += 1

            logger.info(f"表格 {table_idx + 1} 包含 {total_cells} 个非空单元格")

            # 逐行逐列处理每个单元格
            for row_idx, row in enumerate(table.rows):
                for cell_idx, cell in enumerate(row.cells):
                    cell_text = cell.text.strip()

                    if cell_text:
                        # 检查是否是合并单元格（通过对象ID检测）
                        cell_object_id = id(cell)
                        if cell_object_id in processed_cell_objects:
                            logger.info(f"跳过合并单元格 [{row_idx + 1}, {cell_idx + 1}]: 已处理过相同对象 (ID={cell_object_id})")
                            processed_cells += 1
                            continue

                        logger.info(f"检查单元格 [{row_idx + 1}, {cell_idx + 1}]: {cell_text[:30]}...")

                        # 检查是否应该跳过翻译
                        should_skip, reason = self.translation_detector.should_skip_translation(
                            cell_text, self.source_lang, self.target_lang
                        )

                        if should_skip:
                            logger.info(f"跳过表格单元格翻译: {reason} - 单元格 [{row_idx + 1}, {cell_idx + 1}]: {cell_text[:30]}...")
                        else:
                            logger.info(f"翻译表格单元格 [{row_idx + 1}, {cell_idx + 1}]: {cell_text[:30]}...")
                            self._translate_single_cell(cell, used_terminology, translation_results, terminology)
                            processed_cell_objects.add(cell_object_id)  # 记录已处理的单元格对象

                        processed_cells += 1

            logger.info(f"表格 {table_idx + 1} 处理完成: 检查了 {processed_cells}/{total_cells} 个单元格")

    def _translate_single_cell(self, cell, used_terminology: Dict, translation_results: List, terminology: Dict = None) -> None:
        """翻译单个表格单元格"""
        logger.info(f"正在翻译表格内容: {cell.text[:50]}...")

        # 如果是仅翻译模式，保存原文并清空单元格
        if self.output_format == "translation_only":
            original_text = cell.text
            for para in cell.paragraphs:
                para.clear()
            # 保存原始格式信息（清空后）
            original_format = self._save_format_info(cell.paragraphs)
        else:
            # 双语对照模式，保存原始格式信息
            original_format = self._save_format_info(cell.paragraphs)

        # 检查单元格中是否包含数学公式
        text, formulas = self._extract_latex_formulas(cell.text if self.output_format == "bilingual" else original_text)

        # 预处理多行文本以解决AI模型翻译不完整的问题
        text, is_multiline = self._preprocess_multiline_text(text)

        # 翻译单元格内容（不包含公式部分）
        try:
            if self.preprocess_terms:
                # 使用术语预处理方式翻译
                if self.source_lang == "zh":
                    # 中文 → 外语
                    # 检查是否有可用的术语
                    if not used_terminology:
                        # 如果没有术语，使用常规翻译
                        logger.info("未找到匹配术语，使用常规翻译（带术语库）")
                        translation = self.translator.translate_text(text, terminology, self.source_lang, self.target_lang)
                    else:
                        # 使用新的直接替换方法，避免占位符恢复问题
                        logger.info(f"使用术语预处理方式翻译，找到 {len(used_terminology)} 个匹配术语")
                        # 记录术语样本（仅记录前5个术语，避免日志过大）
                        terms_sample = list(used_terminology.items())[:5]
                        logger.info(f"术语样本（前5个）: {terms_sample}")

                        # 使用新的直接替换方法，避免占位符恢复问题
                        processed_text = self.term_extractor.replace_terms_with_target_language(text, used_terminology)
                        logger.info(f"直接替换后的文本前100个字符: {processed_text[:100]}")

                        # 翻译处理后的文本（不需要恢复占位符）
                        translation = self.translator.translate_text(processed_text, {}, self.source_lang, self.target_lang)
                        logger.info(f"最终翻译结果前100个字符: {translation[:100]}")
                else:
                    # 外语 → 中文
                    # 检查是否有可用的术语
                    if not used_terminology:
                        # 如果没有术语，使用常规翻译
                        logger.info("未找到匹配术语，使用常规翻译")
                        translation = self.translator.translate_text(text, None, self.source_lang, self.target_lang)
                    else:
                        try:
                            # 使用term_extractor的占位符系统进行术语预处理
                            # used_terminology已经是 {外语术语: 中文术语} 格式，直接使用
                            reverse_terminology = used_terminology

                            logger.info(f"使用术语预处理方式翻译，找到 {len(reverse_terminology)} 个匹配术语")
                            # 记录术语样本（仅记录前5个术语，避免日志过大）
                            terms_sample = list(reverse_terminology.items())[:5]
                            logger.info(f"术语样本（前5个）: {terms_sample}")

                            # 使用新的直接替换方法，避免占位符恢复问题
                            processed_text = self.term_extractor.replace_foreign_terms_with_target_language(text, reverse_terminology)
                            logger.info(f"直接替换后的文本前100个字符: {processed_text[:100]}")

                            # 翻译处理后的文本（不需要恢复占位符）
                            translation = self.translator.translate_text(processed_text, {}, self.source_lang, self.target_lang)
                            logger.info(f"最终翻译结果前100个字符: {translation[:100]}")
                        except Exception as e:
                            logger.error(f"外语→中文术语替换失败: {str(e)}")
                            # 如果术语替换失败，使用常规翻译
                            translation = self.translator.translate_text(text, None, self.source_lang, self.target_lang)
            else:
                # 使用常规方式翻译
                if self.source_lang == "zh":
                    # 中文 → 外语，使用术语库
                    translation = self.translator.translate_text(text, terminology, self.source_lang, self.target_lang)
                else:
                    # 外语 → 中文，不使用术语库（因为术语库是中文→外语格式）
                    translation = self.translator.translate_text(text, None, self.source_lang, self.target_lang)
        except Exception as e:
            logger.error(f"翻译单元格内容失败: {str(e)}")
            # 翻译失败时直接输出原文，不显示错误信息
            translation = text

        # 后处理多行文本翻译结果
        if is_multiline:
            translation = self._postprocess_multiline_translation(translation)

        # 将公式重新插入到翻译后的文本中
        if formulas:
            translation = self._restore_latex_formulas(translation, formulas)

        logger.info(f"表格内容翻译完成: {translation[:50]}")

        # 收集翻译结果
        translation_results.append({
            'original': cell.text if self.output_format == "bilingual" else original_text,
            'translated': translation
        })

        # 在原文后添加翻译
        self._add_translation_with_format(cell.paragraphs, translation, original_format)

    def _process_paragraphs(self, doc: Document, terminology: Dict, translation_results: list) -> None:
        """处理文档中的段落"""
        self.logger.info("开始处理文档段落")
        self.web_logger.info("Processing document paragraphs...")

        # 如果启用了术语预处理，先收集所有使用的术语
        used_terminology = {}
        if self.preprocess_terms:
            self.logger.info("=== 术语预处理已启用，开始收集段落术语 ===")
            self.logger.info(f"翻译方向: {self.source_lang} -> {self.target_lang}")
            self.logger.info(f"术语库大小: {len(terminology)} 个术语")

            # 显示术语库样本
            if terminology:
                sample_terms = list(terminology.items())[:5]
                self.logger.info(f"术语库样本（前5个）: {sample_terms}")

            # 对于外语→中文翻译模式，预先将术语库键值对调并缓存
            if self.source_lang != "zh":
                self.logger.info("外语→中文翻译模式，预先对调术语库键值并缓存...")
                self.reversed_terminology = self._create_reversed_terminology(terminology)
                self.logger.info(f"对调后的术语库大小: {len(self.reversed_terminology)} 个术语")

                # 显示对调后的术语库样本
                if self.reversed_terminology:
                    reversed_sample = list(self.reversed_terminology.items())[:5]
                    self.logger.info(f"对调后术语库样本（前5个）: {reversed_sample}")
            else:
                self.reversed_terminology = None

            # 先遍历所有段落，收集使用的术语
            para_count = len(doc.paragraphs)
            self.logger.info(f"开始分析 {para_count} 个段落中的术语...")

            for para_idx, paragraph in enumerate(doc.paragraphs, 1):
                self.web_logger.info(f"Processing paragraph {para_idx}/{para_count}")
                if paragraph.text.strip():
                    # 检查是否应该跳过翻译
                    if self._should_skip_translation(paragraph.text):
                        logger.info(f"跳过翻译段落内容（纯数字/编码）: {paragraph.text[:50]}...")
                        continue

                    try:
                        # 根据翻译方向选择不同的术语提取方法
                        if self.source_lang == "zh":
                            # 中文 → 外语
                            self.logger.info(f"从中文段落提取术语: {paragraph.text[:50]}...")
                            para_terms = self.term_extractor.extract_terms(paragraph.text, terminology)
                            self.logger.info(f"从中文段落提取术语: {len(para_terms)} 个")
                        else:
                            # 外语 → 中文，使用缓存的反向术语库
                            self.logger.info(f"从外语段落提取术语: {paragraph.text[:50]}...")
                            if self.reversed_terminology:
                                # 使用缓存的反向术语库进行高效匹配
                                para_terms = self.term_extractor.extract_foreign_terms_from_reversed_dict(paragraph.text, self.reversed_terminology)
                                self.logger.info(f"从外语段落提取术语（使用缓存）: {len(para_terms)} 个")
                            else:
                                # 回退到原始方法
                                para_terms = self.term_extractor.extract_foreign_terms_by_chinese_values(paragraph.text, terminology)
                                self.logger.info(f"从外语段落提取术语（原始方法）: {len(para_terms)} 个")

                        # 显示提取到的术语
                        if para_terms:
                            self.logger.info(f"段落提取到的术语: {list(para_terms.items())[:3]}")

                        # 更新使用的术语词典
                        used_terminology.update(para_terms)
                    except Exception as e:
                        self.logger.error(f"段落术语提取失败: {str(e)}")
                        self.web_logger.error(f"Paragraph term extraction failed: {str(e)}")

            self.logger.info(f"从段落中提取了 {len(used_terminology)} 个术语")
            self.web_logger.info(f"Extracted {len(used_terminology)} terms from paragraphs")

            # 如果有使用的术语，导出到Excel文件
            if used_terminology:
                self._export_used_terminology(used_terminology)

        # 处理段落翻译
        if self.skip_translated_content:
            # 使用双行检测处理段落
            self._process_paragraphs_with_line_detection(doc, terminology, used_terminology, translation_results)
        else:
            # 传统方式处理段落
            self._process_paragraphs_traditional(doc, terminology, used_terminology, translation_results)

    def _process_paragraphs_with_line_detection(self, doc: Document, terminology: Dict, used_terminology: Dict, translation_results: List) -> None:
        """使用双行检测处理段落翻译"""
        paragraphs = doc.paragraphs
        total_paragraphs = len(paragraphs)
        processed_count = 0

        i = 0
        while i < len(paragraphs):
            current_para = paragraphs[i]
            current_text = current_para.text.strip()

            if not current_text:
                i += 1
                processed_count += 1
                continue

            # 更新进度
            progress = (processed_count / total_paragraphs) * 0.6 + 0.4  # 段落处理从40%开始
            self._update_progress(progress, f"双行检测处理段落 {processed_count+1}/{total_paragraphs}")

            # 检查是否有下一个段落进行双行检测
            if i + 1 < len(paragraphs):
                next_para = paragraphs[i + 1]
                next_text = next_para.text.strip()

                if next_text:
                    # 双行检测：判断是否构成翻译对
                    is_translation_pair, pair_reason = self.translation_detector._is_translation_pair(
                        current_text, next_text, self.source_lang, self.target_lang
                    )

                    if is_translation_pair:
                        logger.info(f"跳过翻译对: {pair_reason}")
                        logger.info(f"  第一行: {current_text[:50]}...")
                        logger.info(f"  第二行: {next_text[:50]}...")
                        i += 2  # 跳过两个段落
                        processed_count += 2
                        continue

            # 检查单行是否应该跳过
            should_skip, reason = self.translation_detector.should_skip_translation(
                current_text, self.source_lang, self.target_lang
            )

            if should_skip:
                logger.info(f"跳过段落翻译: {reason} - {current_text[:50]}...")
                i += 1
                processed_count += 1
                continue

            # 翻译当前段落
            self._translate_single_paragraph(current_para, used_terminology, translation_results, terminology)

            i += 1
            processed_count += 1

    def _process_paragraphs_traditional(self, doc: Document, terminology: Dict, used_terminology: Dict, translation_results: List) -> None:
        """传统方式处理段落翻译（不使用双行检测）"""
        for i, paragraph in enumerate(doc.paragraphs):
            if paragraph.text.strip():
                # 更新进度
                progress = (i / len(doc.paragraphs)) * 0.6 + 0.4  # 段落处理从40%开始
                self._update_progress(progress, f"处理段落 {i+1}/{len(doc.paragraphs)}")

                self._translate_single_paragraph(paragraph, used_terminology, translation_results, terminology)

    def _translate_single_paragraph(self, paragraph, used_terminology: Dict, translation_results: List, terminology: Dict = None) -> None:
        """翻译单个段落"""
        logger.info(f"正在翻译段落: {paragraph.text[:50]}...")

        # 如果是仅翻译模式，清空原文段落
        if self.output_format == "translation_only":
            original_text = paragraph.text
            paragraph.clear()
            # 保存原始格式信息
            original_format = self._save_format_info([paragraph])
        else:
            # 双语对照模式，保存原始格式信息
            original_format = self._save_format_info([paragraph])

        # 检查段落中是否包含数学公式
        text, formulas = self._extract_latex_formulas(paragraph.text if self.output_format == "bilingual" else original_text)

        # 预处理多行文本以解决AI模型翻译不完整的问题
        text, is_multiline = self._preprocess_multiline_text(text)

        # 翻译段落内容（不包含公式部分）
        try:
            if self.preprocess_terms:
                # 使用术语预处理方式翻译
                if self.is_cn_to_foreign:
                    # 中文 → 外语
                    # 检查是否有可用的术语
                    if not used_terminology:
                        # 如果没有术语，使用常规翻译
                        logger.info("未找到匹配术语，使用常规翻译（带术语库）")
                        translation = self.translator.translate_text(text, terminology, self.source_lang, self.target_lang)
                    else:
                        # 使用新的直接替换方法，避免占位符恢复问题
                        logger.info(f"使用直接术语替换方法，找到 {len(used_terminology)} 个匹配术语")
                        # 记录术语样本（仅记录前5个术语，避免日志过大）
                        terms_sample = list(used_terminology.items())[:5]
                        logger.info(f"术语样本（前5个）: {terms_sample}")

                        # 直接替换术语为目标语言
                        processed_text = self.term_extractor.replace_terms_with_target_language(text, used_terminology)
                        logger.info(f"直接替换后的文本前100个字符: {processed_text[:100]}")

                        # 翻译处理后的文本（不需要恢复占位符）
                        translation = self.translator.translate_text(processed_text, {}, self.source_lang, self.target_lang)
                        logger.info(f"最终翻译结果前100个字符: {translation[:100]}")
                else:
                    # 外语 → 中文
                    # 检查是否有可用的术语
                    if not used_terminology:
                        # 如果没有术语，使用常规翻译
                        logger.info("未找到匹配术语，使用常规翻译")
                        translation = self.translator.translate_text(text, None, self.source_lang, self.target_lang)
                    else:
                        # 使用新的直接替换方法，避免占位符恢复问题
                        # used_terminology已经是 {外语术语: 中文术语} 格式，直接使用
                        reverse_terminology = used_terminology

                        logger.info(f"使用直接术语替换方法，找到 {len(reverse_terminology)} 个匹配术语")
                        # 记录术语样本（仅记录前5个术语，避免日志过大）
                        terms_sample = list(reverse_terminology.items())[:5]
                        logger.info(f"术语样本（前5个）: {terms_sample}")

                        # 直接替换外语术语为中文术语
                        processed_text = self.term_extractor.replace_foreign_terms_with_target_language(text, reverse_terminology)
                        logger.info(f"直接替换后的文本前100个字符: {processed_text[:100]}")

                        # 翻译处理后的文本（不需要恢复占位符）
                        translation = self.translator.translate_text(processed_text, {}, self.source_lang, self.target_lang)
                        logger.info(f"最终翻译结果前100个字符: {translation[:100]}")
            else:
                # 使用常规方式翻译
                if self.is_cn_to_foreign:
                    # 中文 → 外语，使用术语库
                    translation = self.translator.translate_text(text, terminology, self.source_lang, self.target_lang)
                else:
                    # 外语 → 中文，不使用术语库（因为术语库是中文→外语格式）
                    translation = self.translator.translate_text(text, None, self.source_lang, self.target_lang)
        except Exception as e:
            logger.error(f"翻译段落内容失败: {str(e)}")
            # 翻译失败时直接输出原文，不显示错误信息
            translation = text

        # 后处理多行文本翻译结果
        if is_multiline:
            translation = self._postprocess_multiline_translation(translation)

        # 将公式重新插入到翻译后的文本中
        if formulas:
            translation = self._restore_latex_formulas(translation, formulas)

        logger.info(f"段落翻译完成: {translation[:50]}")

        # 收集翻译结果
        translation_results.append({
            'original': paragraph.text if self.output_format == "bilingual" else original_text,
            'translated': translation
        })

        # 在原文后添加翻译
        self._add_translation_with_format([paragraph], translation, original_format)
        time.sleep(0.1)  # 添加小延迟，避免API请求过快

    def _extract_latex_formulas(self, text: str) -> Tuple[str, List[Tuple[str, str]]]:
        """
        提取文本中的LaTeX公式，并用占位符替换

        Args:
            text: 原始文本

        Returns:
            Tuple[str, List[Tuple[str, str]]]: 替换后的文本和公式列表(占位符, 公式)
        """
        formulas = []
        processed_text = text

        # 遍历所有公式模式
        for i, pattern in enumerate(self.latex_patterns):
            # 查找所有匹配的公式
            matches = re.findall(pattern, processed_text, re.DOTALL)

            # 替换每个公式为占位符
            for j, match in enumerate(matches):
                # 获取完整的公式文本
                if pattern.startswith(r'\$\$'):
                    full_formula = f"$${match}$$"
                elif pattern.startswith(r'\$'):
                    full_formula = f"${match}$"
                elif 'equation' in pattern:
                    full_formula = f"\\begin{{equation}}{match}\\end{{equation}}"
                elif 'align' in pattern:
                    full_formula = f"\\begin{{align}}{match}\\end{{align}}"
                elif 'eqnarray' in pattern:
                    full_formula = f"\\begin{{eqnarray}}{match}\\end{{eqnarray}}"
                else:
                    full_formula = match

                # 创建唯一的占位符
                placeholder = f"[LATEX_FORMULA_{i}_{j}]"

                # 保存公式和占位符
                formulas.append((placeholder, full_formula))

                # 替换文本中的公式为占位符
                processed_text = processed_text.replace(full_formula, placeholder, 1)

        return processed_text, formulas

    def _restore_latex_formulas(self, text: str, formulas: List[Tuple[str, str]]) -> str:
        """
        将占位符替换回LaTeX公式

        Args:
            text: 包含占位符的文本
            formulas: 公式列表(占位符, 公式)

        Returns:
            str: 恢复公式后的文本
        """
        result = text

        # 替换所有占位符为原始公式
        for placeholder, formula in formulas:
            result = result.replace(placeholder, formula)

        return result

    def export_to_pdf(self, docx_path: str) -> str:
        """
        将Word文档转换为PDF

        Args:
            docx_path: Word文档路径

        Returns:
            str: PDF文件路径
        """
        try:
            logger.info(f"正在将Word文档转换为PDF: {docx_path}")

            # 构建PDF文件路径（与Word文档同名，但扩展名为.pdf）
            pdf_path = os.path.splitext(docx_path)[0] + ".pdf"

            # 使用docx2pdf转换
            docx2pdf_convert(docx_path, pdf_path)

            logger.info(f"PDF文件已保存到: {pdf_path}")
            return pdf_path
        except Exception as e:
            logger.error(f"转换PDF失败: {str(e)}")
            raise Exception(f"转换PDF失败: {str(e)}")

    def _save_format_info(self, paragraphs: List[Any]) -> List[Dict]:
        """保存段落格式信息"""
        format_info = []
        for paragraph in paragraphs:
            para_format = {
                'style_name': paragraph.style.name,
                'runs': []
            }
            for run in paragraph.runs:
                run_format = {
                    'bold': run.bold,
                    'italic': run.italic,
                    'underline': run.underline,
                    'font_size': run.font.size,
                    'font_name': run.font.name
                }
                para_format['runs'].append(run_format)
            format_info.append(para_format)
        return format_info

    def _add_translation_with_format(self, paragraphs: List[Any], translation: str, original_format: List[Dict]) -> None:
        """添加带格式的翻译文本"""
        for paragraph in paragraphs:
            # 根据输出格式决定如何添加翻译
            if self.output_format == "bilingual" and paragraph.text.strip():
                # 双语对照模式：在原文后添加翻译
                paragraph.add_run('\n')  # 添加换行
                run = paragraph.add_run(translation)
            else:
                # 仅翻译模式：直接添加翻译（不添加换行）
                run = paragraph.add_run(translation)

            # 设置翻译文本字体
            run.font.name = 'Calibri'

            # 保持与原文相同的格式
            if original_format and original_format[0]['runs']:
                first_run = original_format[0]['runs'][0]
                run.bold = first_run['bold']
                run.italic = first_run['italic']
                run.underline = first_run['underline']
                if first_run['font_size']:
                    run.font.size = first_run['font_size']

    def export_to_excel(self, translation_results, original_file_path, target_language):
        """将翻译结果导出为Excel文件"""
        try:
            logger.info(f"正在导出翻译数据到Excel，共 {len(translation_results)} 条记录...")

            # 创建DataFrame
            df = pd.DataFrame({
                '原文': [item['original'] for item in translation_results],
                f'{target_language}翻译': [item['translated'] for item in translation_results]
            })

            # 生成保存路径
            file_name = os.path.basename(original_file_path)
            base_name = os.path.splitext(file_name)[0]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

            # 使用与主文档相同的输出目录
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "输出")

            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)

            # 构建Excel文件路径
            excel_path = os.path.join(output_dir, f"{base_name}_翻译对照表_{timestamp}.xlsx")

            # 保存到Excel
            df.to_excel(excel_path, index=False, engine='openpyxl')

            logger.info(f"翻译对照表已保存至: {excel_path}")
            return excel_path
        except Exception as e:
            logger.error(f"导出Excel文件时出错: {str(e)}")
            return None

    def _export_used_terminology(self, used_terminology: Dict[str, str]) -> str:
        """导出使用的术语到Excel文件，包含使用统计信息"""
        try:
            logger.info(f"正在导出使用的术语到Excel，共 {len(used_terminology)} 个术语...")

            # 根据翻译方向创建不同的列名
            if self.source_lang == "zh":
                # 中文 → 外语
                source_column = '中文术语'
                target_column = '目标语术语'
            else:
                # 外语 → 中文
                source_column = '外语术语'
                target_column = '中文术语'

            # 获取术语使用统计信息
            usage_stats = self.term_extractor.get_terminology_usage_stats()

            # 如果有统计信息，使用更详细的导出格式
            if usage_stats:
                # 创建包含使用次数的DataFrame
                data = []
                for term, term_info in usage_stats.items():
                    data.append({
                        source_column: term_info['source'],
                        target_column: term_info['target'],
                        '使用次数': term_info['count']
                    })

                # 如果没有统计数据，使用基本的术语列表
                if not data:
                    for source, target in used_terminology.items():
                        data.append({
                            source_column: source,
                            target_column: target,
                            '使用次数': 'N/A'
                        })

                # 创建DataFrame
                df = pd.DataFrame(data)

                # 按使用次数降序排序
                if '使用次数' in df.columns and any(isinstance(x, int) for x in df['使用次数']):
                    df = df.sort_values(by='使用次数', ascending=False)
            else:
                # 创建基本的DataFrame（无使用次数）
                df = pd.DataFrame({
                    source_column: list(used_terminology.keys()),
                    target_column: list(used_terminology.values())
                })

            # 生成保存路径
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

            # 使用与主文档相同的输出目录
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "输出")

            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)

            # 构建Excel文件路径
            excel_path = os.path.join(output_dir, f"使用的术语_{timestamp}.xlsx")

            # 保存到Excel
            df.to_excel(excel_path, index=False, engine='openpyxl')

            logger.info(f"使用的术语表已保存至: {excel_path}")
            return excel_path
        except Exception as e:
            logger.error(f"导出术语Excel文件时出错: {str(e)}")
            return None

    def _create_reversed_terminology(self, terminology: Dict[str, str]) -> Dict[str, str]:
        """
        创建反向术语库（外语术语: 中文术语）

        Args:
            terminology: 原始术语库 {中文术语: 外语术语}

        Returns:
            Dict[str, str]: 反向术语库 {外语术语: 中文术语}
        """
        reversed_terminology = {}

        for cn_term, foreign_term in terminology.items():
            # 确保外语术语不为空
            if foreign_term and foreign_term.strip():
                # 如果有多个中文术语对应同一个外语术语，选择最长的中文术语
                if foreign_term in reversed_terminology:
                    existing_cn_term = reversed_terminology[foreign_term]
                    if len(cn_term) > len(existing_cn_term):
                        reversed_terminology[foreign_term] = cn_term
                        self.logger.debug(f"术语冲突，选择更长的中文术语: {foreign_term} -> {cn_term} (替换 {existing_cn_term})")
                else:
                    reversed_terminology[foreign_term] = cn_term

        self.logger.info(f"成功创建反向术语库，原始术语库: {len(terminology)} 个，反向术语库: {len(reversed_terminology)} 个")
        return reversed_terminology

    def _update_progress(self, progress: float, message: str = ""):
        """更新进度"""
        # 记录进度到日志
        if progress >= 0:
            logger.info(f"进度: {progress*100:.1f}% - {message}")
            self.web_logger.info(f"Progress: {progress*100:.1f}% - {message}")
        else:
            logger.error(f"进度: 错误 - {message}")
            self.web_logger.error(f"Progress: Error - {message}")

        if self.progress_callback:
            import asyncio
            import threading

            def safe_callback():
                """安全的回调函数执行"""
                try:
                    # 尝试异步调用回调函数
                    if asyncio.iscoroutinefunction(self.progress_callback):
                        # 检查是否已有事件循环在运行
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # 如果当前事件循环正在运行，创建一个任务而不是新的事件循环
                                asyncio.create_task(self.progress_callback(progress, message))
                            else:
                                # 如果当前事件循环不在运行，使用它来运行协程
                                loop.run_until_complete(self.progress_callback(progress, message))
                        except RuntimeError:
                            # 如果没有事件循环，创建一个新的
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(self.progress_callback(progress, message))
                            finally:
                                loop.close()
                    else:
                        # 同步回调函数
                        self.progress_callback(progress, message)
                except Exception as e:
                    logger.error(f"更新进度失败: {str(e)}")

            # 在单独线程中执行回调，避免阻塞主线程
            try:
                callback_thread = threading.Thread(target=safe_callback)
                callback_thread.daemon = True
                callback_thread.start()

                # 等待最多1秒，避免进度更新阻塞太久
                callback_thread.join(timeout=1.0)

                if callback_thread.is_alive():
                    logger.warning("进度回调执行超时，跳过此次更新")

            except Exception as e:
                logger.error(f"执行进度回调时出错: {str(e)}")

    def _translate_with_retry(self, text: str, terminology: Dict = None) -> str:
        """带重试机制的翻译"""
        if not text.strip():
            return text

        # 增加自适应重试延迟
        retry_delay = self.retry_delay
        max_retry_delay = 30  # 最大重试延迟30秒

        for attempt in range(self.retry_count):
            try:
                # 使用翻译服务进行翻译
                translation = self.translator.translate_text(text, terminology, self.source_lang, self.target_lang)

                # 检查翻译结果是否为空或异常短
                if not translation or (len(translation) < len(text) * 0.1 and len(text) > 50):
                    logger.warning(f"翻译结果异常短 (尝试 {attempt+1}/{self.retry_count}): 原文长度 {len(text)}，译文长度 {len(translation or '')}")
                    if attempt < self.retry_count - 1:
                        logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        # 增加重试延迟（指数退避）
                        retry_delay = min(retry_delay * 1.5, max_retry_delay)
                        continue

                # 检查翻译结果是否包含错误信息
                error_indicators = ["翻译失败", "translation failed", "error", "错误", "请求超时", "timeout"]
                if any(indicator in translation.lower() for indicator in error_indicators):
                    logger.warning(f"翻译结果包含错误信息 (尝试 {attempt+1}/{self.retry_count}): {translation[:100]}")
                    if attempt < self.retry_count - 1:
                        logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                        # 增加重试延迟（指数退避）
                        retry_delay = min(retry_delay * 1.5, max_retry_delay)
                        continue

                return translation
            except Exception as e:
                logger.warning(f"翻译失败 (尝试 {attempt+1}/{self.retry_count}): {str(e)}")
                if attempt < self.retry_count - 1:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    # 增加重试延迟（指数退避）
                    retry_delay = min(retry_delay * 1.5, max_retry_delay)
                else:
                    # 最后一次尝试失败，返回原文而不是抛出异常
                    logger.error(f"翻译失败，已重试 {self.retry_count} 次，返回原文: {str(e)}")
                    return text

    def translate_paragraph(self, text: str, target_language: str, terminology: Dict) -> str:
        """翻译段落文本"""
        if not text.strip():
            return text

        try:
            # 根据术语库开关决定是否使用术语库
            if self.use_terminology:
                # 获取目标语言的术语库
                terms_dict = terminology.get(target_language, {})

                # 如果目标语言不在术语库中，尝试使用语言代码映射
                if not terms_dict and target_language in ['en', 'ja', 'ko', 'fr', 'de', 'es', 'ru']:
                    # 映射语言代码到术语库中的语言名称
                    language_map = {
                        'en': '英语',
                        'ja': '日语',
                        'ko': '韩语',
                        'fr': '法语',
                        'de': '德语',
                        'es': '西班牙语',
                        'ru': '俄语'
                    }
                    mapped_language = language_map.get(target_language)
                    if mapped_language and mapped_language in terminology:
                        terms_dict = terminology.get(mapped_language, {})
                        logger.info(f"使用映射后的语言名称 '{mapped_language}' 获取术语库")

                # 记录术语库大小
                logger.info(f"使用{target_language}术语库，包含 {len(terms_dict)} 个术语")

                # 记录术语预处理状态
                logger.info(f"术语预处理功能状态: {'启用' if self.preprocess_terms else '禁用'}")
                logger.info(f"翻译方向: {'中文→外语' if self.is_cn_to_foreign else '外语→中文'}")

                # 如果术语库为空，直接使用常规翻译
                if not terms_dict:
                    logger.warning(f"术语库为空，使用常规翻译")
                    return self._translate_with_retry(text, None)

                # 如果启用了术语预处理
                if self.preprocess_terms:
                    try:
                        # 记录术语库内容（仅记录前5个术语，避免日志过大）
                        terms_sample = list(terms_dict.items())[:5]
                        logger.info(f"术语库样本（前5个）: {terms_sample}")

                        # 根据翻译方向选择不同的术语处理方法
                        if self.is_cn_to_foreign:
                            # 中文 → 外语
                            logger.info(f"使用中文→外语术语预处理流程")

                            # 提取文本中使用的术语
                            logger.info(f"开始从中文文本中提取术语，文本前50个字符: {text[:50]}")
                            used_terms = self.term_extractor.extract_terms(text, terms_dict)
                            logger.info(f"从中文文本中提取了 {len(used_terms)} 个术语")

                            # 记录提取到的术语（仅记录前5个，避免日志过大）
                            if used_terms:
                                terms_sample = list(used_terms.items())[:5]
                                logger.info(f"提取到的术语样本（前5个）: {terms_sample}")
                            else:
                                logger.warning("未从文本中提取到任何术语")

                            # 如果没有找到术语，使用常规翻译
                            if not used_terms:
                                logger.info("未找到匹配术语，使用常规翻译（带术语库）")
                                return self._translate_with_retry(text, terms_dict)

                            # 直接使用翻译器的内置术语处理功能
                            logger.info(f"使用翻译器内置术语处理功能，找到 {len(used_terms)} 个匹配术语")
                            # 记录术语样本（仅记录前5个术语，避免日志过大）
                            terms_sample = list(used_terms.items())[:5]
                            logger.info(f"术语样本（前5个）: {terms_sample}")

                            result = self._translate_with_retry(text, used_terms)
                            logger.info(f"最终翻译结果: {result[:100]}...")
                            return result
                        else:
                            # 外语 → 中文
                            logger.info(f"使用外语→中文术语预处理流程")

                            try:
                                # 提取文本中使用的术语，优先使用缓存的反向术语库
                                logger.info(f"开始从外语文本中提取术语，文本前50个字符: {text[:50]}")

                                # 检查是否有缓存的反向术语库
                                if hasattr(self, 'reversed_terminology') and self.reversed_terminology:
                                    # 使用缓存的反向术语库进行高效匹配
                                    logger.info("使用缓存的反向术语库进行术语提取")
                                    used_terms = self.term_extractor.extract_foreign_terms_from_reversed_dict(text, self.reversed_terminology)
                                    logger.info(f"从外语文本中提取了 {len(used_terms)} 个术语（使用缓存）")
                                else:
                                    # 回退到原始方法，但先创建反向术语库缓存
                                    logger.info("缓存不可用，创建反向术语库并使用")
                                    self.reversed_terminology = self._create_reversed_terminology(terms_dict)
                                    if self.reversed_terminology:
                                        used_terms = self.term_extractor.extract_foreign_terms_from_reversed_dict(text, self.reversed_terminology)
                                        logger.info(f"从外语文本中提取了 {len(used_terms)} 个术语（新建缓存）")
                                    else:
                                        # 最后的回退方案
                                        used_terms = self.term_extractor.extract_foreign_terms_by_chinese_values(text, terms_dict)
                                        logger.info(f"从外语文本中提取了 {len(used_terms)} 个术语（原始方法）")

                                # 记录提取到的术语（仅记录前5个，避免日志过大）
                                if used_terms:
                                    terms_sample = list(used_terms.items())[:5]
                                    logger.info(f"提取到的术语样本（前5个）: {terms_sample}")
                                else:
                                    logger.warning("未从外语文本中提取到任何术语")

                                # 如果没有找到术语，使用常规翻译
                                if not used_terms:
                                    logger.info("未找到匹配术语，使用常规翻译（不带术语库）")
                                    return self._translate_with_retry(text, None)

                                # 使用term_extractor的占位符系统进行术语预处理
                                # used_terms已经是 {外语术语: 中文术语} 格式，直接使用
                                reverse_terminology = used_terms

                                logger.info(f"使用术语预处理方式翻译，找到 {len(reverse_terminology)} 个匹配术语")
                                # 记录术语样本（仅记录前5个术语，避免日志过大）
                                terms_sample = list(reverse_terminology.items())[:5]
                                logger.info(f"术语样本（前5个）: {terms_sample}")

                                processed_text = self.term_extractor.replace_foreign_terms_with_placeholders(text, reverse_terminology)
                                logger.info(f"已将术语替换为占位符: {processed_text[:100]}...")

                                # 翻译处理后的文本（不使用术语库，因为已经预处理了）
                                logger.info("开始翻译含占位符的文本...")
                                translated_with_placeholders = self._translate_with_retry(processed_text, None)
                                logger.info(f"带占位符的翻译结果: {translated_with_placeholders[:100]}...")

                                # 将占位符替换回中文术语
                                logger.info("开始将占位符替换回中文术语...")
                                result = self.term_extractor.restore_placeholders_with_chinese_terms(translated_with_placeholders)
                                logger.info(f"最终翻译结果（替换回术语）: {result[:100]}...")
                                return result
                            except Exception as e:
                                logger.error(f"外语→中文术语处理失败: {str(e)}")
                                logger.error(f"错误详情: {str(e.__class__.__name__)}: {str(e)}")
                                # 如果术语处理失败，使用常规翻译
                                logger.info("术语处理失败，回退到常规翻译（不带术语库）")
                                return self._translate_with_retry(text, None)
                    except Exception as e:
                        logger.error(f"术语预处理失败: {str(e)}")
                        # 如果术语预处理失败，回退到常规翻译
                        logger.info("术语预处理失败，回退到常规翻译（带术语库）")
                        return self._translate_with_retry(text, terms_dict)
                else:
                    # 使用常规方式翻译
                    logger.info("使用常规方式翻译（带术语库）")
                    return self._translate_with_retry(text, terms_dict)
            else:
                # 不使用术语库的翻译
                logger.info("不使用术语库进行翻译")
                return self._translate_with_retry(text, None)

        except Exception as e:
            logger.error(f"翻译失败: {str(e)}")
            # 返回错误信息而不是抛出异常，这样可以继续处理其他段落
            return f"翻译失败: {str(e)}"

    def _preprocess_multiline_text(self, text: str) -> Tuple[str, bool]:
        """
        预处理多行文本以解决AI模型翻译不完整的问题

        Args:
            text: 原始文本

        Returns:
            Tuple[str, bool]: (处理后的文本, 是否为多行文本)
        """
        # 检查是否为多行文本
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        if len(lines) <= 1:
            # 单行或空文本，不需要预处理
            return text, False

        logger.info(f"检测到多行文本，行数: {len(lines)}")
        logger.info(f"原始多行文本: {text[:100]}...")

        # 将多行文本合并为单行，使用分号分隔
        # 这样可以确保AI模型翻译所有内容
        merged_text = '; '.join(lines)

        logger.info(f"合并后的单行文本: {merged_text[:100]}...")

        return merged_text, True

    def _postprocess_multiline_translation(self, translation: str) -> str:
        """
        后处理多行文本的翻译结果

        Args:
            translation: 翻译结果

        Returns:
            str: 格式化后的翻译结果
        """
        logger.info(f"后处理多行翻译结果: {translation[:100]}...")

        # 尝试将翻译结果重新分行
        # 查找可能的分隔符
        separators = ['; ', ';', '. ', '.']

        for separator in separators:
            if separator in translation:
                # 按分隔符分割
                parts = [part.strip() for part in translation.split(separator) if part.strip()]

                if len(parts) > 1:
                    # 重新组织为多行格式
                    formatted_translation = '\n'.join(parts)
                    logger.info(f"成功分行，行数: {len(parts)}")
                    logger.info(f"格式化后的翻译: {formatted_translation[:100]}...")
                    return formatted_translation

        # 如果无法分行，返回原始翻译
        logger.info("无法分行，返回原始翻译")
        return translation