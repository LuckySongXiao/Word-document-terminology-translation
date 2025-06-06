import os
import logging
from typing import Any
from .document_processor import DocumentProcessor
from .pdf_processor import PDFProcessor
from .translator import TranslationService

# PPT功能已移除
PPT_SUPPORT = False

logger = logging.getLogger(__name__)

class DocumentProcessorFactory:
    """文档处理器工厂类，根据文件类型创建相应的处理器"""

    @staticmethod
    def create_processor(file_path: str, translator: TranslationService) -> Any:
        """
        根据文件类型创建相应的处理器

        Args:
            file_path: 文件路径
            translator: 翻译服务实例

        Returns:
            Any: 文档处理器实例

        Raises:
            ValueError: 如果文件类型不支持
        """
        # 获取文件扩展名（转换为小写）
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        # 根据扩展名选择处理器
        if ext == '.docx':
            logger.info(f"创建Word文档处理器，文件: {file_path}")
            return DocumentProcessor(translator)
        elif ext == '.pdf':
            logger.info(f"创建PDF文档处理器，文件: {file_path}")
            return PDFProcessor(translator)
        elif ext in ['.xlsx', '.xls']:
            logger.info(f"创建Excel文档处理器，文件: {file_path}")
            from .excel_processor import ExcelProcessor
            return ExcelProcessor(translator)
        else:
            supported_formats = ".docx, .pdf, .xlsx, .xls"
            logger.error(f"不支持的文件类型: {ext}")
            raise ValueError(f"不支持的文件类型: {ext}，目前仅支持{supported_formats}文件")
