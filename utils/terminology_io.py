"""
术语库导入导出标准化工具

确保所有导入导出操作都使用一致的格式和结构
"""

import csv
import json
import logging
import os
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import chardet

logger = logging.getLogger(__name__)

class TerminologyIO:
    """术语库导入导出工具"""
    
    def __init__(self):
        """初始化工具"""
        self.supported_languages = ["英语", "日语", "韩语", "德语", "法语", "西班牙语"]
        self.language_codes = {
            "英语": "en",
            "日语": "ja", 
            "韩语": "ko",
            "德语": "de",
            "法语": "fr",
            "西班牙语": "es"
        }
    
    def export_to_csv(self, terminology: Dict[str, str], language: str, file_path: str) -> bool:
        """
        导出术语到CSV文件
        
        Args:
            terminology: 术语字典 {中文术语: 外语术语}
            language: 语言名称（如"英语"）
            file_path: 输出文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                
                # 写入标题行
                writer.writerow(["中文术语", f"{language}术语"])
                
                # 写入术语数据
                for chinese_term, foreign_term in terminology.items():
                    # 清理术语中的回车符和换行符
                    clean_chinese = self._clean_text(chinese_term)
                    clean_foreign = self._clean_text(foreign_term)
                    writer.writerow([clean_chinese, clean_foreign])
            
            logger.info(f"成功导出 {len(terminology)} 个术语到 {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出CSV文件失败: {str(e)}")
            return False
    
    def import_from_csv(self, file_path: str) -> Tuple[bool, Dict[str, str], str]:
        """
        从CSV文件导入术语
        
        Args:
            file_path: CSV文件路径
            
        Returns:
            Tuple[bool, Dict[str, str], str]: (是否成功, 术语字典, 错误信息)
        """
        try:
            # 自动检测文件编码
            encoding = self._detect_encoding(file_path)
            
            terms = {}
            with open(file_path, 'r', encoding=encoding) as f:
                reader = csv.reader(f)
                
                # 跳过标题行
                header = next(reader, None)
                if not header or len(header) < 2:
                    return False, {}, "CSV文件格式错误：缺少标题行或列数不足"
                
                # 读取术语数据
                for row_num, row in enumerate(reader, start=2):
                    if len(row) >= 2:
                        chinese_term = self._clean_text(row[0])
                        foreign_term = self._clean_text(row[1])
                        
                        if chinese_term and foreign_term:
                            terms[chinese_term] = foreign_term
                        elif chinese_term or foreign_term:
                            logger.warning(f"第{row_num}行数据不完整: {row}")
            
            if not terms:
                return False, {}, "未能从文件中解析出有效的术语"
            
            logger.info(f"成功从 {file_path} 导入 {len(terms)} 个术语")
            return True, terms, ""
            
        except Exception as e:
            error_msg = f"导入CSV文件失败: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg
    
    def export_to_json(self, terminology: Dict[str, str], file_path: str) -> bool:
        """
        导出术语到JSON文件
        
        Args:
            terminology: 术语字典
            file_path: 输出文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            # 清理术语数据
            clean_terminology = {}
            for chinese_term, foreign_term in terminology.items():
                clean_chinese = self._clean_text(chinese_term)
                clean_foreign = self._clean_text(foreign_term)
                if clean_chinese and clean_foreign:
                    clean_terminology[clean_chinese] = clean_foreign
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(clean_terminology, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功导出 {len(clean_terminology)} 个术语到 {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出JSON文件失败: {str(e)}")
            return False
    
    def import_from_json(self, file_path: str) -> Tuple[bool, Dict[str, str], str]:
        """
        从JSON文件导入术语
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            Tuple[bool, Dict[str, str], str]: (是否成功, 术语字典, 错误信息)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                return False, {}, "JSON文件格式错误：根对象必须是字典"
            
            terms = {}
            for chinese_term, foreign_term in data.items():
                clean_chinese = self._clean_text(str(chinese_term))
                clean_foreign = self._clean_text(str(foreign_term))
                
                if clean_chinese and clean_foreign:
                    terms[clean_chinese] = clean_foreign
            
            if not terms:
                return False, {}, "未能从文件中解析出有效的术语"
            
            logger.info(f"成功从 {file_path} 导入 {len(terms)} 个术语")
            return True, terms, ""
            
        except Exception as e:
            error_msg = f"导入JSON文件失败: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg
    
    def export_full_terminology(self, terminology: Dict[str, Dict[str, str]], file_path: str) -> bool:
        """
        导出完整术语库到JSON文件
        
        Args:
            terminology: 完整术语库
            file_path: 输出文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            # 清理所有术语数据
            clean_terminology = {}
            for language in self.supported_languages:
                clean_terminology[language] = {}
                if language in terminology and isinstance(terminology[language], dict):
                    for chinese_term, foreign_term in terminology[language].items():
                        clean_chinese = self._clean_text(chinese_term)
                        clean_foreign = self._clean_text(foreign_term)
                        if clean_chinese and clean_foreign:
                            clean_terminology[language][clean_chinese] = clean_foreign
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(clean_terminology, f, ensure_ascii=False, indent=2)
            
            # 统计术语数量
            total_terms = sum(len(terms) for terms in clean_terminology.values())
            logger.info(f"成功导出完整术语库到 {file_path}，共 {total_terms} 个术语")
            return True
            
        except Exception as e:
            logger.error(f"导出完整术语库失败: {str(e)}")
            return False
    
    def import_full_terminology(self, file_path: str) -> Tuple[bool, Dict[str, Dict[str, str]], str]:
        """
        从JSON文件导入完整术语库
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            Tuple[bool, Dict[str, Dict[str, str]], str]: (是否成功, 术语库, 错误信息)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                return False, {}, "JSON文件格式错误：根对象必须是字典"
            
            # 初始化术语库
            terminology = {language: {} for language in self.supported_languages}
            
            # 处理不同的文件格式
            if self._is_flat_structure(data):
                # 扁平结构，假设是英语术语
                for chinese_term, foreign_term in data.items():
                    clean_chinese = self._clean_text(str(chinese_term))
                    clean_foreign = self._clean_text(str(foreign_term))
                    if clean_chinese and clean_foreign:
                        terminology["英语"][clean_chinese] = clean_foreign
            else:
                # 分层结构
                for language in self.supported_languages:
                    if language in data and isinstance(data[language], dict):
                        for chinese_term, foreign_term in data[language].items():
                            clean_chinese = self._clean_text(str(chinese_term))
                            clean_foreign = self._clean_text(str(foreign_term))
                            if clean_chinese and clean_foreign:
                                terminology[language][clean_chinese] = clean_foreign
            
            # 统计术语数量
            total_terms = sum(len(terms) for terms in terminology.values())
            logger.info(f"成功从 {file_path} 导入完整术语库，共 {total_terms} 个术语")
            return True, terminology, ""
            
        except Exception as e:
            error_msg = f"导入完整术语库失败: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本，移除不当字符
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""
        
        # 移除回车符、换行符，并去除首尾空格
        cleaned = str(text).replace('\r', '').replace('\n', '').strip()
        return cleaned
    
    def _detect_encoding(self, file_path: str) -> str:
        """
        检测文件编码
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 编码名称
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                
                # 如果检测可信度较低，尝试常见编码
                if result['confidence'] < 0.7:
                    for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                        try:
                            with open(file_path, 'r', encoding=enc) as test_f:
                                test_f.read(1024)  # 尝试读取一部分
                            encoding = enc
                            break
                        except UnicodeDecodeError:
                            continue
                
                return encoding or 'utf-8'
                
        except Exception as e:
            logger.warning(f"检测文件编码失败: {str(e)}，使用默认编码 utf-8")
            return 'utf-8'
    
    def _is_flat_structure(self, data: Dict) -> bool:
        """
        检查是否为扁平结构
        
        Args:
            data: 数据字典
            
        Returns:
            bool: 是否为扁平结构
        """
        # 如果所有键都不是支持的语言名称，则认为是扁平结构
        for key in data.keys():
            if key in self.supported_languages:
                return False
        return True
    
    def generate_filename(self, language: str, file_type: str = "csv") -> str:
        """
        生成标准化的文件名
        
        Args:
            language: 语言名称
            file_type: 文件类型（csv或json）
            
        Returns:
            str: 文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{language}术语库_{timestamp}.{file_type}"


# 便捷函数
def export_terminology_csv(terminology: Dict[str, str], language: str, file_path: str) -> bool:
    """导出术语到CSV文件的便捷函数"""
    io_tool = TerminologyIO()
    return io_tool.export_to_csv(terminology, language, file_path)


def import_terminology_csv(file_path: str) -> Tuple[bool, Dict[str, str], str]:
    """从CSV文件导入术语的便捷函数"""
    io_tool = TerminologyIO()
    return io_tool.import_from_csv(file_path)


def export_terminology_json(terminology: Dict[str, str], file_path: str) -> bool:
    """导出术语到JSON文件的便捷函数"""
    io_tool = TerminologyIO()
    return io_tool.export_to_json(terminology, file_path)


def import_terminology_json(file_path: str) -> Tuple[bool, Dict[str, str], str]:
    """从JSON文件导入术语的便捷函数"""
    io_tool = TerminologyIO()
    return io_tool.import_from_json(file_path)
