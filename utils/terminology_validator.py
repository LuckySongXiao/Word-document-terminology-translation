"""
术语库结构验证和修复工具

确保术语库文件结构与系统一致，并提供修复功能
"""

import json
import logging
import os
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class TerminologyValidator:
    """术语库验证器"""
    
    def __init__(self):
        """初始化验证器"""
        self.supported_languages = ["英语", "日语", "韩语", "德语", "法语", "西班牙语"]
        self.required_structure = {
            "英语": {},
            "日语": {},
            "韩语": {},
            "德语": {},
            "法语": {},
            "西班牙语": {}
        }
    
    def validate_terminology_structure(self, terminology: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证术语库结构是否正确
        
        Args:
            terminology: 术语库数据
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查是否为字典
        if not isinstance(terminology, dict):
            errors.append("术语库必须是字典格式")
            return False, errors
        
        # 检查是否包含所有支持的语言
        for language in self.supported_languages:
            if language not in terminology:
                errors.append(f"缺少语言: {language}")
            elif not isinstance(terminology[language], dict):
                errors.append(f"语言 '{language}' 的值必须是字典格式")
        
        # 检查是否有不支持的语言
        for language in terminology.keys():
            if language not in self.supported_languages:
                errors.append(f"不支持的语言: {language}")
        
        # 检查术语格式
        for language, terms in terminology.items():
            if language in self.supported_languages and isinstance(terms, dict):
                for chinese_term, foreign_term in terms.items():
                    if not isinstance(chinese_term, str):
                        errors.append(f"语言 '{language}' 中的中文术语必须是字符串: {chinese_term}")
                    if not isinstance(foreign_term, str):
                        errors.append(f"语言 '{language}' 中的外语术语必须是字符串: {foreign_term}")
                    
                    # 检查是否包含不当的字符
                    if '\r' in chinese_term or '\n' in chinese_term:
                        errors.append(f"语言 '{language}' 中的中文术语包含回车符或换行符: {chinese_term}")
                    if '\r' in foreign_term or '\n' in foreign_term:
                        errors.append(f"语言 '{language}' 中的外语术语包含回车符或换行符: {foreign_term}")
        
        return len(errors) == 0, errors
    
    def fix_terminology_structure(self, terminology: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """
        修复术语库结构
        
        Args:
            terminology: 原始术语库数据
            
        Returns:
            Dict[str, Dict[str, str]]: 修复后的术语库
        """
        fixed_terminology = self.required_structure.copy()
        
        # 如果是旧格式（扁平结构），转换为新格式
        if self._is_flat_structure(terminology):
            logger.info("检测到扁平结构，转换为分层结构")
            # 假设扁平结构是英语术语
            fixed_terminology["英语"] = self._clean_terms(terminology)
        else:
            # 处理分层结构
            for language in self.supported_languages:
                if language in terminology and isinstance(terminology[language], dict):
                    fixed_terminology[language] = self._clean_terms(terminology[language])
                else:
                    fixed_terminology[language] = {}
        
        return fixed_terminology
    
    def _is_flat_structure(self, terminology: Dict[str, Any]) -> bool:
        """
        检查是否为扁平结构（直接的中文->外语映射）
        
        Args:
            terminology: 术语库数据
            
        Returns:
            bool: 是否为扁平结构
        """
        # 如果所有键都不是支持的语言名称，则认为是扁平结构
        for key in terminology.keys():
            if key in self.supported_languages:
                return False
        return True
    
    def _clean_terms(self, terms: Dict[str, str]) -> Dict[str, str]:
        """
        清理术语数据，移除不当字符
        
        Args:
            terms: 术语字典
            
        Returns:
            Dict[str, str]: 清理后的术语字典
        """
        cleaned_terms = {}
        
        for chinese_term, foreign_term in terms.items():
            # 确保都是字符串
            chinese_str = str(chinese_term) if chinese_term is not None else ""
            foreign_str = str(foreign_term) if foreign_term is not None else ""
            
            # 清理回车符和换行符
            clean_chinese = chinese_str.replace('\r', '').replace('\n', '').strip()
            clean_foreign = foreign_str.replace('\r', '').replace('\n', '').strip()
            
            # 只保留非空术语
            if clean_chinese and clean_foreign:
                cleaned_terms[clean_chinese] = clean_foreign
        
        return cleaned_terms
    
    def validate_and_fix_file(self, file_path: str) -> bool:
        """
        验证并修复术语库文件
        
        Args:
            file_path: 术语库文件路径
            
        Returns:
            bool: 是否成功修复
        """
        try:
            # 读取原文件
            if not os.path.exists(file_path):
                logger.warning(f"术语库文件不存在: {file_path}")
                # 创建默认结构
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.required_structure, f, ensure_ascii=False, indent=2)
                logger.info(f"已创建默认术语库文件: {file_path}")
                return True
            
            with open(file_path, 'r', encoding='utf-8') as f:
                terminology = json.load(f)
            
            # 验证结构
            is_valid, errors = self.validate_terminology_structure(terminology)
            
            if is_valid:
                logger.info("术语库结构验证通过")
                return True
            
            # 记录错误
            logger.warning(f"术语库结构验证失败，错误: {errors}")
            
            # 修复结构
            fixed_terminology = self.fix_terminology_structure(terminology)
            
            # 备份原文件
            backup_path = file_path + '.backup'
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(file_path, backup_path)
            logger.info(f"已备份原文件到: {backup_path}")
            
            # 保存修复后的文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(fixed_terminology, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已修复术语库文件: {file_path}")
            
            # 再次验证
            is_valid_after_fix, _ = self.validate_terminology_structure(fixed_terminology)
            if is_valid_after_fix:
                logger.info("修复后的术语库结构验证通过")
                return True
            else:
                logger.error("修复后的术语库结构仍然无效")
                return False
                
        except Exception as e:
            logger.error(f"验证和修复术语库文件时出错: {str(e)}")
            return False
    
    def get_terminology_stats(self, terminology: Dict[str, Dict[str, str]]) -> Dict[str, int]:
        """
        获取术语库统计信息
        
        Args:
            terminology: 术语库数据
            
        Returns:
            Dict[str, int]: 各语言的术语数量
        """
        stats = {}
        for language in self.supported_languages:
            if language in terminology and isinstance(terminology[language], dict):
                stats[language] = len(terminology[language])
            else:
                stats[language] = 0
        return stats


def validate_terminology_file(file_path: str) -> bool:
    """
    验证术语库文件的便捷函数
    
    Args:
        file_path: 术语库文件路径
        
    Returns:
        bool: 是否验证通过或修复成功
    """
    validator = TerminologyValidator()
    return validator.validate_and_fix_file(file_path)


if __name__ == "__main__":
    # 测试验证器
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        success = validate_terminology_file(file_path)
        if success:
            print(f"术语库文件 {file_path} 验证通过或修复成功")
        else:
            print(f"术语库文件 {file_path} 验证失败")
    else:
        print("用法: python terminology_validator.py <术语库文件路径>")
