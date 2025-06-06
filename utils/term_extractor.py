import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)

class TermExtractor:
    """术语提取和替换工具类"""

    def __init__(self):
        """初始化术语提取器"""
        self.placeholder_format = "[术语{index}]"  # 使用中文格式的占位符，更容易被翻译模型保留
        self.term_map = {}  # 术语映射表 {占位符: (原文术语, 目标语术语)}
        self.match_count = {}  # 记录每个术语的匹配次数

    def extract_terms(self, text: str, terminology: Dict[str, str]) -> Dict[str, str]:
        """
        从中文文本中提取存在的术语

        Args:
            text: 要分析的中文文本
            terminology: 完整术语词典 {中文术语: 目标语术语}

        Returns:
            Dict[str, str]: 文本中存在的术语词典 {中文术语: 目标语术语}
        """
        if not text:
            logger.warning("文本为空，无法提取术语")
            return {}

        if not terminology:
            logger.warning("术语库为空，无法提取术语")
            # 记录术语库内容
            logger.warning(f"术语库类型: {type(terminology)}")
            logger.warning(f"术语库内容: {terminology}")
            return {}

        # 创建一个新的词典来存储文本中存在的术语
        used_terms = {}

        # 记录术语库内容（仅记录前5个术语，避免日志过大）
        terms_sample = list(terminology.items())[:5]
        logger.info(f"术语库样本（前5个）: {terms_sample}")
        logger.info(f"术语库大小: {len(terminology)}")
        logger.info(f"要分析的文本前50个字符: {text[:50]}")

        # 按照术语长度降序排序，确保优先匹配最长的术语
        sorted_terms = sorted(terminology.items(), key=lambda x: len(x[0]), reverse=True)

        logger.info(f"开始从文本中提取术语，术语库大小: {len(terminology)}")
        logger.debug(f"文本前100个字符: {text[:100]}")

        for cn_term, foreign_term in sorted_terms:
            # 跳过空术语
            if not cn_term or not cn_term.strip():
                continue

            try:
                # 使用正则表达式查找完整的术语（确保是独立的词，而不是其他词的一部分）
                # 这里的模式匹配中文术语，考虑到中文术语通常不需要词边界
                pattern = r'(?<![a-zA-Z0-9])' + re.escape(cn_term) + r'(?![a-zA-Z0-9])'

                # 查找所有匹配项
                matches = list(re.finditer(pattern, text))
                if matches:
                    used_terms[cn_term] = foreign_term
                    logger.info(f"在文本中找到术语: {cn_term} -> {foreign_term} (匹配次数: {len(matches)})")

                    # 记录匹配位置
                    match_positions = [f"({m.start()}-{m.end()})" for m in matches[:3]]  # 仅记录前3个匹配位置
                    logger.debug(f"术语 '{cn_term}' 匹配位置: {', '.join(match_positions)}")
            except Exception as e:
                logger.error(f"匹配术语时出错: {str(e)}, 术语: {cn_term}")
                logger.error(f"错误详情: {str(e.__class__.__name__)}: {str(e)}")
                continue

        logger.info(f"从中文文本中提取了 {len(used_terms)} 个术语")

        # 记录提取到的术语样本（仅记录前5个术语，避免日志过大）
        if used_terms:
            terms_sample = list(used_terms.items())[:5]
            logger.info(f"提取到的术语样本（前5个）: {terms_sample}")

        return used_terms

    def extract_foreign_terms(self, text: str, terminology: Dict[str, str]) -> Dict[str, str]:
        """
        从外语文本中提取存在的术语

        Args:
            text: 要分析的外语文本
            terminology: 完整术语词典 {中文术语: 目标语术语}

        Returns:
            Dict[str, str]: 文本中存在的术语词典 {外语术语: 中文术语}
        """
        if not text or not terminology:
            return {}

        # 创建一个新的词典来存储文本中存在的术语
        used_terms = {}

        # 创建反向映射 {外语术语: 中文术语}
        reverse_terminology = {}
        for cn_term, foreign_term in terminology.items():
            # 确保外语术语不为空
            if foreign_term and foreign_term.strip():
                reverse_terminology[foreign_term] = cn_term

        # 如果没有有效的反向映射，直接返回空词典
        if not reverse_terminology:
            logger.warning("未找到有效的外语术语，无法进行反向匹配")
            return {}

        # 按照术语长度降序排序，确保优先匹配最长的术语
        sorted_terms = sorted(reverse_terminology.items(), key=lambda x: len(x[0]), reverse=True)

        for foreign_term, cn_term in sorted_terms:
            try:
                # 使用正则表达式查找完整的术语（确保是独立的词，而不是其他词的一部分）
                # 对于外语术语，使用单词边界
                if re.search(r'\b' + re.escape(foreign_term) + r'\b', text):
                    used_terms[foreign_term] = cn_term
                    logger.debug(f"在外语文本中找到术语: {foreign_term} -> {cn_term}")
            except Exception as e:
                logger.error(f"匹配外语术语时出错: {str(e)}, 术语: {foreign_term}")
                continue

        logger.info(f"从外语文本中提取了 {len(used_terms)} 个术语")
        return used_terms

    def extract_foreign_terms_by_chinese_values(self, text: str, terminology: Dict[str, str]) -> Dict[str, str]:
        """
        从外语文本中提取存在的术语，通过匹配中文术语对应的外语值

        遍历术语目标语种的值，若被翻译的文本中存在该值，则将术语的键写入预选术语字典中，
        当所有的术语都被筛选一遍之后，将所有术语的键替换文本中与值一致的关键词，
        然后将替换后的文本进行翻译

        Args:
            text: 要分析的外语文本
            terminology: 完整术语词典 {中文术语: 目标语术语}

        Returns:
            Dict[str, str]: 文本中存在的术语词典 {外语术语: 中文术语}
        """
        if not text:
            logger.warning("文本为空，无法提取术语")
            return {}

        if not terminology:
            logger.warning("术语库为空，无法提取术语")
            # 记录术语库内容
            logger.warning(f"术语库类型: {type(terminology)}")
            logger.warning(f"术语库内容: {terminology}")
            return {}

        # 创建一个新的词典来存储文本中存在的术语
        used_terms = {}

        # 记录术语库内容（仅记录前5个术语，避免日志过大）
        terms_sample = list(terminology.items())[:5]
        logger.info(f"术语库样本（前5个）: {terms_sample}")
        logger.info(f"术语库大小: {len(terminology)}")
        logger.info(f"要分析的文本前50个字符: {text[:50]}")

        # 创建值到键的映射 {外语术语: [中文术语1, 中文术语2, ...]}
        # 因为可能有多个中文术语对应同一个外语术语
        value_to_keys = {}
        for cn_term, foreign_term in terminology.items():
            # 确保外语术语不为空
            if foreign_term and foreign_term.strip():
                if foreign_term not in value_to_keys:
                    value_to_keys[foreign_term] = []
                value_to_keys[foreign_term].append(cn_term)

        # 如果没有有效的映射，直接返回空词典
        if not value_to_keys:
            logger.warning("未找到有效的外语术语，无法进行匹配")
            return {}

        # 按照外语术语长度降序排序，确保优先匹配最长的术语
        sorted_terms = sorted(value_to_keys.items(), key=lambda x: len(x[0]), reverse=True)

        logger.info(f"开始从外语文本中提取术语，有效术语数量: {len(value_to_keys)}")

        # 记录排序后的术语样本（仅记录前5个术语，避免日志过大）
        terms_sample = sorted_terms[:5]
        logger.info(f"排序后的术语样本（前5个）: {terms_sample}")

        # 遍历术语目标语种的值
        for foreign_term, cn_terms in sorted_terms:
            try:
                # 跳过空术语
                if not foreign_term or not foreign_term.strip():
                    continue

                # 使用正则表达式查找完整的术语（确保是独立的词，而不是其他词的一部分）
                # 对于外语术语，使用单词边界
                pattern = r'\b' + re.escape(foreign_term) + r'\b'

                # 查找所有匹配项
                matches = list(re.finditer(pattern, text))
                if matches:
                    # 如果有多个中文术语对应同一个外语术语，选择最长的中文术语
                    cn_term = sorted(cn_terms, key=len, reverse=True)[0]
                    used_terms[foreign_term] = cn_term
                    logger.info(f"在外语文本中找到术语值匹配: {foreign_term} -> {cn_term} (匹配次数: {len(matches)})")

                    # 记录匹配位置
                    match_positions = [f"({m.start()}-{m.end()})" for m in matches[:3]]  # 仅记录前3个匹配位置
                    logger.debug(f"术语 '{foreign_term}' 匹配位置: {', '.join(match_positions)}")
            except Exception as e:
                logger.error(f"匹配外语术语值时出错: {str(e)}, 术语: {foreign_term}")
                logger.error(f"错误详情: {str(e.__class__.__name__)}: {str(e)}")
                continue

        logger.info(f"通过中文术语对应的外语值匹配，从外语文本中提取了 {len(used_terms)} 个术语")

        # 记录提取到的术语样本（仅记录前5个术语，避免日志过大）
        if used_terms:
            terms_sample = list(used_terms.items())[:5]
            logger.info(f"提取到的术语样本（前5个）: {terms_sample}")

        return used_terms

    def extract_foreign_terms_from_reversed_dict(self, text: str, reversed_terminology: Dict[str, str]) -> Dict[str, str]:
        """
        从外语文本中提取存在的术语，使用预先对调的术语库（高效版本）

        Args:
            text: 要分析的外语文本
            reversed_terminology: 预先对调的术语词典 {外语术语: 中文术语}

        Returns:
            Dict[str, str]: 文本中存在的术语词典 {外语术语: 中文术语}
        """
        if not text:
            logger.warning("文本为空，无法提取术语")
            return {}

        if not reversed_terminology:
            logger.warning("反向术语库为空，无法提取术语")
            return {}

        # 创建一个新的词典来存储文本中存在的术语
        used_terms = {}

        # 记录术语库内容（仅记录前5个术语，避免日志过大）
        terms_sample = list(reversed_terminology.items())[:5]
        logger.info(f"反向术语库样本（前5个）: {terms_sample}")
        logger.info(f"反向术语库大小: {len(reversed_terminology)}")
        logger.info(f"要分析的文本前50个字符: {text[:50]}")

        # 按照外语术语长度降序排序，确保优先匹配最长的术语
        sorted_terms = sorted(reversed_terminology.items(), key=lambda x: len(x[0]), reverse=True)

        logger.info(f"开始从外语文本中提取术语，使用缓存的反向术语库，术语数量: {len(reversed_terminology)}")

        # 记录排序后的术语样本（仅记录前5个术语，避免日志过大）
        terms_sample = sorted_terms[:5]
        logger.info(f"排序后的术语样本（前5个）: {terms_sample}")

        # 遍历反向术语库
        for foreign_term, cn_term in sorted_terms:
            try:
                # 跳过空术语
                if not foreign_term or not foreign_term.strip():
                    continue

                # 使用正则表达式查找完整的术语（确保是独立的词，而不是其他词的一部分）
                # 对于外语术语，使用单词边界
                pattern = r'\b' + re.escape(foreign_term) + r'\b'

                # 查找所有匹配项
                matches = list(re.finditer(pattern, text))
                if matches:
                    used_terms[foreign_term] = cn_term
                    logger.info(f"在外语文本中找到术语匹配（缓存版本）: {foreign_term} -> {cn_term} (匹配次数: {len(matches)})")

                    # 记录匹配位置
                    match_positions = [f"({m.start()}-{m.end()})" for m in matches[:3]]  # 仅记录前3个匹配位置
                    logger.debug(f"术语 '{foreign_term}' 匹配位置: {', '.join(match_positions)}")
            except Exception as e:
                logger.error(f"匹配外语术语时出错: {str(e)}, 术语: {foreign_term}")
                logger.error(f"错误详情: {str(e.__class__.__name__)}: {str(e)}")
                continue

        logger.info(f"使用缓存的反向术语库，从外语文本中提取了 {len(used_terms)} 个术语")
        return used_terms

    def replace_terms_with_placeholders(self, text: str, terminology: Dict[str, str]) -> str:
        """
        将中文文本中的术语替换为占位符

        Args:
            text: 原始中文文本
            terminology: 要替换的术语词典 {中文术语: 目标语术语}

        Returns:
            str: 替换后的文本
        """
        if not text or not terminology:
            logger.warning("文本为空或术语库为空，无法替换术语")
            return text

        # 清空之前的术语映射和匹配计数
        self.term_map = {}
        self.match_count = {}

        # 按照术语长度降序排序，确保优先替换最长的术语
        sorted_terms = sorted(terminology.items(), key=lambda x: len(x[0]), reverse=True)

        logger.info(f"开始替换术语为占位符，术语库大小: {len(terminology)}")
        logger.debug(f"原始文本前100个字符: {text[:100]}")

        # 记录术语库样本（仅记录前5个术语，避免日志过大）
        terms_sample = list(terminology.items())[:5]
        logger.info(f"术语库样本（前5个）: {terms_sample}")

        # 替换文本中的术语为占位符
        result_text = text
        replaced_count = 0

        for index, (cn_term, foreign_term) in enumerate(sorted_terms):
            # 跳过空术语
            if not cn_term or not cn_term.strip():
                continue

            try:
                placeholder = self.placeholder_format.format(index=index)
                # 使用正则表达式替换完整的术语（确保是独立的词，而不是其他词的一部分）
                pattern = r'(?<![a-zA-Z0-9])' + re.escape(cn_term) + r'(?![a-zA-Z0-9])'

                # 查找所有匹配项
                matches = list(re.finditer(pattern, result_text))
                if matches:
                    # 记录匹配次数
                    match_count = len(matches)
                    self.match_count[cn_term] = match_count

                    # 替换前的文本
                    before_replace = result_text
                    # 执行替换
                    result_text = re.sub(pattern, placeholder, result_text)
                    # 验证替换是否成功
                    if before_replace != result_text:
                        # 保存术语映射
                        self.term_map[placeholder] = (cn_term, foreign_term)
                        replaced_count += 1
                        logger.info(f"替换中文术语: {cn_term} -> {placeholder} (匹配次数: {match_count})")

                        # 记录匹配位置
                        match_positions = [f"({m.start()}-{m.end()})" for m in matches[:3]]  # 仅记录前3个匹配位置
                        logger.debug(f"术语 '{cn_term}' 匹配位置: {', '.join(match_positions)}")
                    else:
                        logger.warning(f"术语替换失败: {cn_term}")
            except Exception as e:
                logger.error(f"替换术语时出错: {str(e)}, 术语: {cn_term}")
                logger.error(f"错误详情: {str(e.__class__.__name__)}: {str(e)}")
                continue

        logger.info(f"替换了 {replaced_count} 个中文术语为占位符")
        if replaced_count > 0:
            logger.debug(f"替换后文本前100个字符: {result_text[:100]}")

            # 记录术语映射表
            term_map_sample = list(self.term_map.items())[:5]  # 仅记录前5个映射
            logger.info(f"术语映射表样本（前5个）: {term_map_sample}")

        return result_text

    def replace_foreign_terms_with_placeholders(self, text: str, terminology: Dict[str, str]) -> str:
        """
        将外语文本中的术语替换为占位符

        遍历术语目标语种的值，若被翻译的文本中存在该值，则将术语的键写入预选术语字典中，
        当所有的术语都被筛选一遍之后，将所有术语的键替换文本中与值一致的关键词，
        然后将替换后的文本进行翻译

        Args:
            text: 原始外语文本
            terminology: 要替换的术语词典 {外语术语: 中文术语}

        Returns:
            str: 替换后的文本
        """
        if not text or not terminology:
            logger.warning("文本为空或术语库为空，无法替换术语")
            return text

        # 清空之前的术语映射和匹配计数
        self.term_map = {}
        self.match_count = {}

        # 按照术语长度降序排序，确保优先替换最长的术语
        sorted_terms = sorted(terminology.items(), key=lambda x: len(x[0]), reverse=True)

        logger.info(f"开始替换外语术语为占位符，术语库大小: {len(terminology)}")
        logger.debug(f"原始文本前100个字符: {text[:100]}")

        # 记录术语库样本（仅记录前5个术语，避免日志过大）
        terms_sample = list(terminology.items())[:5]
        logger.info(f"术语库样本（前5个）: {terms_sample}")

        # 替换文本中的术语为占位符
        result_text = text
        replaced_count = 0

        for index, (foreign_term, cn_term) in enumerate(sorted_terms):
            try:
                # 跳过空术语
                if not foreign_term or not foreign_term.strip():
                    continue

                placeholder = self.placeholder_format.format(index=index)
                # 使用正则表达式替换完整的术语（确保是独立的词，而不是其他词的一部分）
                # 对于外语术语，使用单词边界
                pattern = r'\b' + re.escape(foreign_term) + r'\b'

                # 查找所有匹配项
                matches = list(re.finditer(pattern, result_text))
                if matches:
                    # 记录匹配次数
                    match_count = len(matches)
                    self.match_count[foreign_term] = match_count

                    # 替换前的文本
                    before_replace = result_text
                    # 执行替换
                    result_text = re.sub(pattern, placeholder, result_text)
                    # 检查是否成功替换
                    if before_replace != result_text:
                        # 保存术语映射
                        self.term_map[placeholder] = (foreign_term, cn_term)
                        replaced_count += 1
                        logger.info(f"替换外语术语: {foreign_term} -> {placeholder} (匹配次数: {match_count})")

                        # 记录匹配位置
                        match_positions = [f"({m.start()}-{m.end()})" for m in matches[:3]]  # 仅记录前3个匹配位置
                        logger.debug(f"术语 '{foreign_term}' 匹配位置: {', '.join(match_positions)}")
                    else:
                        logger.warning(f"术语替换失败: {foreign_term}")
            except Exception as e:
                logger.error(f"替换外语术语时出错: {str(e)}, 术语: {foreign_term}")
                logger.error(f"错误详情: {str(e.__class__.__name__)}: {str(e)}")
                continue

        logger.info(f"替换了 {replaced_count} 个外语术语为占位符")
        if replaced_count > 0:
            logger.debug(f"替换后文本前100个字符: {result_text[:100]}")

            # 记录术语映射表
            term_map_sample = list(self.term_map.items())[:5]  # 仅记录前5个映射
            logger.info(f"术语映射表样本（前5个）: {term_map_sample}")

        return result_text

    def restore_placeholders_with_foreign_terms(self, text: str) -> str:
        """
        将文本中的占位符替换为目标外语术语

        Args:
            text: 包含占位符的文本

        Returns:
            str: 替换后的文本
        """
        if not text or not self.term_map:
            logger.warning("文本为空或术语映射为空，无法恢复占位符")
            return text

        result_text = text
        logger.info(f"开始恢复占位符为外语术语，占位符数量: {len(self.term_map)}")
        logger.debug(f"原始文本: {text[:100]}...")

        # 记录术语映射表样本（仅记录前5个，避免日志过大）
        term_map_sample = list(self.term_map.items())[:5]
        logger.info(f"术语映射表样本（前5个）: {term_map_sample}")

        replaced_count = 0
        # 首先尝试直接替换完全匹配的占位符
        for placeholder, term_tuple in self.term_map.items():
            # 确保term_tuple有两个元素，并且第二个元素是外语术语
            if len(term_tuple) != 2:
                logger.warning(f"术语映射格式不正确: {placeholder} -> {term_tuple}")
                continue

            # 获取外语术语（在中文→外语模式下，这是第二个元素）
            foreign_term = term_tuple[1]
            if not foreign_term:
                logger.warning(f"外语术语为空: {placeholder} -> {term_tuple}")
                continue

            # 替换占位符
            pattern = re.escape(placeholder)
            if re.search(pattern, result_text):
                before_replace = result_text
                result_text = re.sub(pattern, foreign_term, result_text)
                if before_replace != result_text:
                    replaced_count += 1
                    # 获取匹配次数（如果有记录）
                    match_count = self.match_count.get(term_tuple[0], "未知")
                    logger.info(f"恢复占位符为外语术语: {placeholder} -> {foreign_term} (原术语匹配次数: {match_count})")
                else:
                    logger.warning(f"占位符替换失败: {placeholder}")
            else:
                logger.warning(f"在文本中未找到占位符: {placeholder}")

        # 然后使用正则表达式查找可能格式略有不同的占位符（如 [术语1]）
        # 由于我们现在使用中文格式的占位符，主要匹配这种格式
        term_pattern = r'\[术语(\d+)\]'  # 匹配 [术语X]

        # 创建索引到术语的映射
        index_to_term = {}
        for placeholder, term_tuple in self.term_map.items():
            # 从占位符中提取索引
            index_match = re.search(r'术语(\d+)', placeholder)
            if index_match and len(term_tuple) == 2:
                index = index_match.group(1)
                index_to_term[index] = term_tuple[1]  # 外语术语

        # 记录索引到术语的映射样本
        index_map_sample = list(index_to_term.items())[:5]
        logger.info(f"索引到术语的映射样本（前5个）: {index_map_sample}")

        # 查找所有匹配的占位符
        matches = re.findall(term_pattern, result_text)
        if matches:
            logger.info(f"发现 {len(matches)} 个需要额外处理的占位符，尝试使用正则表达式匹配")

            # 替换所有匹配的占位符
            for index in matches:
                if index in index_to_term:
                    replace_pattern = r'\[术语' + index + r'\]'
                    before_replace = result_text
                    result_text = re.sub(replace_pattern, index_to_term[index], result_text)
                    if before_replace != result_text:
                        logger.info(f"使用正则表达式恢复占位符: {replace_pattern} -> {index_to_term[index]}")

        # 检查是否还有未替换的占位符
        remaining_placeholders = re.findall(r'\[术语\d+\]', result_text)
        if remaining_placeholders:
            logger.warning(f"仍有 {len(remaining_placeholders)} 个占位符未被替换: {remaining_placeholders[:5]}")

            # 尝试更宽松的匹配方式进行最后的恢复
            for placeholder_text in remaining_placeholders:
                # 提取索引
                index_match = re.search(r'术语(\d+)', placeholder_text)
                if index_match and index_match.group(1) in index_to_term:
                    index = index_match.group(1)
                    result_text = result_text.replace(placeholder_text, index_to_term[index])
                    logger.info(f"使用最终替换恢复占位符: {placeholder_text} -> {index_to_term[index]}")

        logger.info(f"恢复了 {replaced_count} 个占位符为目标外语术语")
        logger.info(f"处理后文本前100个字符: {result_text[:100]}...")
        return result_text

    def restore_placeholders_with_chinese_terms(self, text: str) -> str:
        """
        将文本中的占位符替换为中文术语

        Args:
            text: 包含占位符的文本

        Returns:
            str: 替换后的文本
        """
        if not text or not self.term_map:
            logger.warning("文本为空或术语映射为空，无法恢复占位符")
            return text

        result_text = text
        logger.debug(f"开始恢复占位符为中文术语，占位符数量: {len(self.term_map)}")
        logger.debug(f"原始文本: {text[:100]}...")

        # 记录替换的数量
        replaced_count = 0

        # 首先尝试直接替换完全匹配的占位符
        for placeholder, term_tuple in self.term_map.items():
            # 确保term_tuple有两个元素，并且第二个元素是中文术语
            if len(term_tuple) != 2:
                logger.warning(f"术语映射格式不正确: {placeholder} -> {term_tuple}")
                continue

            # 获取中文术语（在外语→中文模式下，这是第二个元素）
            cn_term = term_tuple[1]
            if not cn_term:
                logger.warning(f"中文术语为空: {placeholder} -> {term_tuple}")
                continue

            # 替换占位符
            if placeholder in result_text:
                # 替换前的文本
                before_replace = result_text
                # 执行替换
                result_text = result_text.replace(placeholder, cn_term)
                # 检查是否成功替换
                if before_replace != result_text:
                    replaced_count += 1
                    # 获取匹配次数（如果有记录）
                    match_count = self.match_count.get(term_tuple[0], "未知")
                    logger.debug(f"恢复占位符为中文术语: {placeholder} -> {cn_term} (原术语匹配次数: {match_count})")
                else:
                    logger.warning(f"占位符替换失败: {placeholder}")
            else:
                logger.warning(f"在文本中未找到占位符: {placeholder}")

        # 然后使用正则表达式查找可能格式略有不同的占位符（如 [术语1]）
        # 由于我们现在使用中文格式的占位符，主要匹配这种格式
        term_pattern = r'\[术语(\d+)\]'  # 匹配 [术语X]

        # 创建索引到术语的映射
        index_to_term = {}
        for placeholder, term_tuple in self.term_map.items():
            # 从占位符中提取索引
            index_match = re.search(r'术语(\d+)', placeholder)
            if index_match and len(term_tuple) == 2:
                index = index_match.group(1)
                index_to_term[index] = term_tuple[1]  # 中文术语

        # 查找所有匹配的占位符
        matches = re.findall(term_pattern, result_text)
        if matches:
            logger.info(f"发现 {len(matches)} 个需要额外处理的占位符，尝试使用正则表达式匹配")

            # 替换所有匹配的占位符
            for index in matches:
                if index in index_to_term:
                    replace_pattern = r'\[术语' + index + r'\]'
                    before_replace = result_text
                    result_text = re.sub(replace_pattern, index_to_term[index], result_text)
                    if before_replace != result_text:
                        logger.debug(f"使用正则表达式恢复占位符: {replace_pattern} -> {index_to_term[index]}")

        # 检查是否还有未替换的占位符
        remaining_placeholders = re.findall(r'\[术语\d+\]', result_text)
        if remaining_placeholders:
            logger.warning(f"仍有 {len(remaining_placeholders)} 个占位符未被替换: {remaining_placeholders[:5]}")

            # 尝试更宽松的匹配方式进行最后的恢复
            for placeholder_text in remaining_placeholders:
                # 提取索引
                index_match = re.search(r'术语(\d+)', placeholder_text)
                if index_match and index_match.group(1) in index_to_term:
                    index = index_match.group(1)
                    result_text = result_text.replace(placeholder_text, index_to_term[index])
                    logger.debug(f"使用最终替换恢复占位符: {placeholder_text} -> {index_to_term[index]}")

        logger.info(f"恢复了 {replaced_count} 个占位符为中文术语")
        logger.debug(f"处理后文本: {result_text[:100]}...")
        return result_text

    def get_used_terminology(self) -> Dict[str, str]:
        """
        获取当前使用的术语词典

        Returns:
            Dict[str, str]: 使用的术语词典 {原文术语: 目标语术语}
        """
        return {source_term: target_term for _, (source_term, target_term) in self.term_map.items()}

    def get_terminology_usage_stats(self) -> Dict[str, Dict]:
        """
        获取术语使用统计信息

        Returns:
            Dict[str, Dict]: 术语使用统计 {
                术语: {
                    'source': 原文术语,
                    'target': 目标语术语,
                    'count': 匹配次数
                }
            }
        """
        stats = {}
        for placeholder, (source_term, target_term) in self.term_map.items():
            # 获取匹配次数
            count = self.match_count.get(source_term, 0)
            stats[source_term] = {
                'source': source_term,
                'target': target_term,
                'count': count
            }
        return stats