import re
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class TranslationDetector:
    """翻译内容检测器 - 自动检测文档中已翻译的内容并跳过"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 双语格式标记模式
        self.bilingual_patterns = [
            # 中英文对照模式
            r'【原文】.*?【译文】',
            r'【中文】.*?【英文】',
            r'【英文】.*?【中文】',
            r'原文[:：].*?译文[:：]',
            r'中文[:：].*?英文[:：]',
            r'英文[:：].*?中文[:：]',

            # 括号对照模式
            r'[\u4e00-\u9fff]+\s*\([A-Za-z\s]+\)',  # 中文(英文)
            r'[A-Za-z\s]+\s*\([\u4e00-\u9fff\s]+\)',  # 英文(中文)

            # 分行对照模式检测 - 更严格的检测，要求英文行包含多个英文单词
            r'[\u4e00-\u9fff].*\n.*\b[A-Za-z]+\s+[A-Za-z]+.*\b',  # 中文行后跟包含多个英文单词的行
            r'\b[A-Za-z]+\s+[A-Za-z]+.*\b.*\n.*[\u4e00-\u9fff]',  # 包含多个英文单词的行后跟中文行
        ]
        
        # 语言检测模式
        self.language_patterns = {
            'chinese': r'[\u4e00-\u9fff]',
            'english': r'[A-Za-z]',
            'japanese': r'[\u3040-\u309f\u30a0-\u30ff]',
            'korean': r'[\uac00-\ud7af]',
            'arabic': r'[\u0600-\u06ff]',
            'russian': r'[\u0400-\u04ff]',
            'french': r'[àâäéèêëïîôöùûüÿç]',
            'german': r'[äöüßÄÖÜ]',
            'spanish': r'[ñáéíóúü]',
        }
        
        # 纯数字/代码模式
        self.skip_patterns = [
            r'^\s*\d+\.?\d*\s*$',  # 纯数字
            r'^\s*\d*\.?\d+[%％]\s*$',  # 百分比（包括小数百分比）
            r'^\s*[A-Z0-9_]+\s*$',  # 全大写代码
            r'^\s*\w+\.\w+\s*$',  # 文件名或域名
            r'^\s*https?://\S+\s*$',  # URL
            r'^\s*\w+@\w+\.\w+\s*$',  # 邮箱
            r'^\s*\d{4}[-/]\d{1,2}[-/]\d{1,2}\s*$',  # 日期
            r'^\s*\d{1,2}:\d{2}(:\d{2})?\s*$',  # 时间
        ]

    def should_skip_translation(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> Tuple[bool, str]:
        """
        判断是否应该跳过翻译的内容
        
        Args:
            text: 要检测的文本
            source_lang: 源语言代码
            target_lang: 目标语言代码
            
        Returns:
            Tuple[bool, str]: (是否跳过, 跳过原因)
        """
        if not text or not text.strip():
            return True, "空文本"
        
        clean_text = text.strip()
        
        # 1. 检查是否为纯数字/代码等应跳过的内容
        for pattern in self.skip_patterns:
            if re.match(pattern, clean_text, re.IGNORECASE):
                return True, f"纯数字/代码内容: {pattern}"
        
        # 2. 检查是否已包含双语格式标记
        for pattern in self.bilingual_patterns:
            if re.search(pattern, clean_text, re.IGNORECASE | re.DOTALL):
                return True, f"检测到双语格式标记: {pattern}"

        # 2.5. 检查单行是否为明显的英文翻译（当源语言为中文时）
        if source_lang == "zh" and target_lang == "en":
            # 如果是纯英文行，且包含常见的翻译词汇，可能是翻译结果
            if re.match(r'^[A-Za-z\s\/:：\-\(\)]+$', clean_text):
                # 检查是否包含常见的翻译关键词
                translation_keywords = [
                    'application', 'form', 'document', 'revision', 'state', 'status',
                    'initial', 'issue', 'obsolete', 'manual', 'procedure', 'instruction',
                    'technical', 'drawing', 'external', 'distribution', 'base'
                ]
                text_lower = clean_text.lower()
                keyword_count = sum(1 for keyword in translation_keywords if keyword in text_lower)
                if keyword_count >= 2 and len(clean_text) > 15:
                    return True, "检测到可能的英文翻译行"
        
        # 3. 检查是否同时包含源语言和目标语言
        skip_result, reason = self._check_mixed_languages(clean_text, source_lang, target_lang)
        if skip_result:
            return True, reason
        
        # 4. 检查是否为已翻译的段落结构
        skip_result, reason = self._check_translated_structure(clean_text, source_lang, target_lang)
        if skip_result:
            return True, reason
        
        return False, ""

    def _check_mixed_languages(self, text: str, source_lang: str, target_lang: str) -> Tuple[bool, str]:
        """检查文本是否同时包含源语言和目标语言"""
        # 获取语言检测模式
        source_pattern = self._get_language_pattern(source_lang)
        target_pattern = self._get_language_pattern(target_lang)

        if not source_pattern or not target_pattern:
            return False, ""

        has_source = bool(re.search(source_pattern, text))
        has_target = bool(re.search(target_pattern, text))

        # 如果同时包含源语言和目标语言，进行详细检查
        if has_source and has_target:
            # 检查是否有括号对照模式
            if source_lang == "zh" and target_lang == "en":
                # 中英文括号对照
                if re.search(r'[\u4e00-\u9fff]+\s*\([A-Za-z\s]+\)', text) or \
                   re.search(r'[A-Za-z\s]+\s*\([\u4e00-\u9fff\s]+\)', text):
                    return True, "检测到中英文括号对照格式"

            # 检查分行对照格式
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) >= 2:
                # 检查连续的中英文行对照
                consecutive_pairs = 0
                for i in range(len(lines) - 1):
                    line1 = lines[i]
                    line2 = lines[i + 1]

                    # 更严格的检查：确保英文行包含有意义的英文内容
                    line1_has_source = re.search(source_pattern, line1)
                    line1_has_target = re.search(target_pattern, line1)
                    line2_has_source = re.search(source_pattern, line2)
                    line2_has_target = re.search(target_pattern, line2)

                    # 检查是否为中文行后跟英文行
                    if (line1_has_source and line2_has_target and
                        not line1_has_target and not line2_has_source):
                        # 额外检查：确保第二行包含有意义的英文内容（至少2个英文单词）
                        english_words = re.findall(r'\b[A-Za-z]{2,}\b', line2)
                        if len(english_words) >= 2:
                            consecutive_pairs += 1
                    # 检查是否为英文行后跟中文行
                    elif (line1_has_target and line2_has_source and
                          not line1_has_source and not line2_has_target):
                        # 额外检查：确保第一行包含有意义的英文内容（至少2个英文单词）
                        english_words = re.findall(r'\b[A-Za-z]{2,}\b', line1)
                        if len(english_words) >= 2:
                            consecutive_pairs += 1

                # 如果有多个连续的双语对照行，认为是已翻译内容
                if consecutive_pairs >= 2:
                    return True, f"检测到{consecutive_pairs}对连续的{source_lang}-{target_lang}对照行"

                # 检查是否有明显的源语言和目标语言分行
                source_lines = [line for line in lines if re.search(source_pattern, line) and not re.search(target_pattern, line)]
                target_lines = [line for line in lines if re.search(target_pattern, line) and not re.search(source_pattern, line)]

                # 如果有明显的源语言和目标语言分行，且比例合理，跳过翻译
                if len(source_lines) > 0 and len(target_lines) > 0:
                    total_lines = len(source_lines) + len(target_lines)
                    if total_lines >= len(lines) * 0.6:  # 至少60%的行是纯语言行
                        return True, f"检测到{source_lang}-{target_lang}双语分行结构"

        return False, ""

    def _check_translated_structure(self, text: str, source_lang: str, target_lang: str) -> Tuple[bool, str]:
        """检查是否为已翻译的段落结构"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if len(lines) < 2:
            return False, ""
        
        # 检查是否有明显的翻译结构标记
        translation_markers = [
            r'【原文】', r'【译文】', r'【中文】', r'【英文】',
            r'原文[:：]', r'译文[:：]', r'中文[:：]', r'英文[:：]',
            r'Original[:：]', r'Translation[:：]', r'Chinese[:：]', r'English[:：]'
        ]
        
        for line in lines:
            for marker in translation_markers:
                if re.search(marker, line, re.IGNORECASE):
                    return True, f"检测到翻译结构标记: {marker}"
        
        # 检查是否有交替的语言模式
        source_pattern = self._get_language_pattern(source_lang)
        target_pattern = self._get_language_pattern(target_lang)
        
        if source_pattern and target_pattern:
            language_sequence = []
            for line in lines:
                if re.search(source_pattern, line):
                    language_sequence.append('source')
                elif re.search(target_pattern, line):
                    language_sequence.append('target')
                else:
                    language_sequence.append('unknown')
            
            # 检查是否有规律的交替模式
            if len(language_sequence) >= 4:
                # 检查是否有source-target-source-target的模式
                alternating_count = 0
                for i in range(len(language_sequence) - 1):
                    if (language_sequence[i] == 'source' and language_sequence[i+1] == 'target') or \
                       (language_sequence[i] == 'target' and language_sequence[i+1] == 'source'):
                        alternating_count += 1
                
                if alternating_count >= 2:
                    return True, f"检测到{source_lang}-{target_lang}交替翻译模式"
        
        return False, ""

    def _get_language_pattern(self, lang_code: str) -> Optional[str]:
        """根据语言代码获取对应的正则表达式模式"""
        lang_mapping = {
            'zh': 'chinese',
            'en': 'english', 
            'ja': 'japanese',
            'ko': 'korean',
            'ar': 'arabic',
            'ru': 'russian',
            'fr': 'french',
            'de': 'german',
            'es': 'spanish'
        }
        
        lang_name = lang_mapping.get(lang_code)
        return self.language_patterns.get(lang_name) if lang_name else None

    def extract_untranslated_content(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> List[str]:
        """
        从混合内容中提取未翻译的部分

        Args:
            text: 包含已翻译和未翻译内容的文本
            source_lang: 源语言代码
            target_lang: 目标语言代码

        Returns:
            List[str]: 需要翻译的文本片段列表
        """
        untranslated_parts = []

        # 按段落分割
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        for paragraph in paragraphs:
            should_skip, reason = self.should_skip_translation(paragraph, source_lang, target_lang)
            if not should_skip:
                untranslated_parts.append(paragraph)
            else:
                self.logger.info(f"跳过已翻译内容: {reason} - {paragraph[:50]}...")

        return untranslated_parts

    def analyze_lines_for_translation(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> List[dict]:
        """
        双行检测：分析文本行，判断相邻两行是否构成翻译对

        Args:
            text: 要分析的文本
            source_lang: 源语言代码
            target_lang: 目标语言代码

        Returns:
            List[dict]: 每行的分析结果，包含行内容、是否需要翻译、跳过原因等
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        results = []
        i = 0

        while i < len(lines):
            current_line = lines[i]

            # 检查当前行是否应该单独跳过（如纯数字、代码等）
            should_skip_single, skip_reason = self._should_skip_single_line(current_line, source_lang, target_lang)

            if should_skip_single:
                results.append({
                    'line': current_line,
                    'action': 'skip',
                    'reason': skip_reason,
                    'line_number': i + 1
                })
                i += 1
                continue

            # 检查是否有下一行进行双行检测
            if i + 1 < len(lines):
                next_line = lines[i + 1]

                # 双行检测：判断是否构成翻译对
                is_translation_pair, pair_reason = self._is_translation_pair(
                    current_line, next_line, source_lang, target_lang
                )

                if is_translation_pair:
                    # 跳过这两行
                    results.append({
                        'line': current_line,
                        'action': 'skip',
                        'reason': f"翻译对的第一行: {pair_reason}",
                        'line_number': i + 1,
                        'paired_with': i + 2
                    })
                    results.append({
                        'line': next_line,
                        'action': 'skip',
                        'reason': f"翻译对的第二行: {pair_reason}",
                        'line_number': i + 2,
                        'paired_with': i + 1
                    })
                    i += 2  # 跳过两行
                    continue

            # 单行处理：需要翻译
            results.append({
                'line': current_line,
                'action': 'translate',
                'reason': '需要翻译的单行内容',
                'line_number': i + 1
            })
            i += 1

        return results

    def _should_skip_single_line(self, line: str, source_lang: str, target_lang: str) -> Tuple[bool, str]:
        """检查单行是否应该跳过（纯数字、代码、URL等）"""
        # 检查纯数字/代码等应跳过的内容
        for pattern in self.skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True, f"纯数字/代码内容: {pattern}"

        # 检查双语格式标记
        for pattern in self.bilingual_patterns:
            if re.search(pattern, line, re.IGNORECASE | re.DOTALL):
                return True, f"包含双语格式标记: {pattern}"

        return False, ""

    def _is_translation_pair(self, line1: str, line2: str, source_lang: str, target_lang: str) -> Tuple[bool, str]:
        """
        判断两行是否构成翻译对

        Args:
            line1: 第一行文本
            line2: 第二行文本
            source_lang: 源语言代码
            target_lang: 目标语言代码

        Returns:
            Tuple[bool, str]: (是否为翻译对, 判断原因)
        """
        # 获取语言检测模式
        source_pattern = self._get_language_pattern(source_lang)
        target_pattern = self._get_language_pattern(target_lang)

        if not source_pattern or not target_pattern:
            return False, "无法获取语言检测模式"

        # 检查第一行是否主要包含源语言
        line1_has_source = bool(re.search(source_pattern, line1))
        line1_has_target = bool(re.search(target_pattern, line1))

        # 检查第二行是否主要包含目标语言
        line2_has_source = bool(re.search(source_pattern, line2))
        line2_has_target = bool(re.search(target_pattern, line2))

        # 基本条件：第一行主要是源语言，第二行主要是目标语言
        if line1_has_source and not line1_has_target and line2_has_target and not line2_has_source:
            # 进一步检查是否可能是翻译关系
            similarity_score = self._calculate_translation_similarity(line1, line2, source_lang, target_lang)

            # 动态阈值：短文本使用较低阈值，长文本使用较高阈值
            threshold = self._get_similarity_threshold(line1, line2)

            # 额外检查：确保这确实是翻译对而不是独立的内容
            if similarity_score > threshold:
                # 进行更严格的翻译对验证
                is_valid_pair = self._validate_translation_pair(line1, line2, source_lang, target_lang)
                if is_valid_pair:
                    return True, f"检测到{source_lang}-{target_lang}翻译对 (相似度: {similarity_score:.2f})"
                else:
                    return False, f"相似度足够但不是有效翻译对 (相似度: {similarity_score:.2f})"

        # 检查反向情况（目标语言在前，源语言在后）
        if line1_has_target and not line1_has_source and line2_has_source and not line2_has_target:
            similarity_score = self._calculate_translation_similarity(line2, line1, source_lang, target_lang)

            threshold = self._get_similarity_threshold(line1, line2)

            if similarity_score > threshold:
                # 进行更严格的翻译对验证
                is_valid_pair = self._validate_translation_pair(line2, line1, source_lang, target_lang)
                if is_valid_pair:
                    return True, f"检测到{target_lang}-{source_lang}翻译对 (相似度: {similarity_score:.2f})"
                else:
                    return False, f"相似度足够但不是有效翻译对 (相似度: {similarity_score:.2f})"

        return False, "不构成翻译对"

    def _validate_translation_pair(self, source_text: str, target_text: str, source_lang: str, target_lang: str) -> bool:
        """
        更严格地验证是否为有效的翻译对

        Args:
            source_text: 源语言文本
            target_text: 目标语言文本
            source_lang: 源语言代码
            target_lang: 目标语言代码

        Returns:
            bool: 是否为有效翻译对
        """
        # 1. 长度检查：翻译对的长度不应该相差太大（放宽标准）
        len_ratio = min(len(source_text), len(target_text)) / max(len(source_text), len(target_text))
        if len_ratio < 0.2:  # 长度相差超过5倍，可能不是翻译对
            return False

        # 2. 内容复杂度检查：过于简单的内容可能不是真正的翻译对（放宽标准）
        source_complexity = self._calculate_text_complexity(source_text)
        target_complexity = self._calculate_text_complexity(target_text)

        # 如果两个文本都过于简单（如单个数字、单个字母），可能不是翻译对
        if source_complexity < 1 and target_complexity < 1:
            return False

        # 3. 语言纯度检查：确保源文本主要是源语言，目标文本主要是目标语言（放宽标准）
        source_purity = self._calculate_language_purity(source_text, source_lang)
        target_purity = self._calculate_language_purity(target_text, target_lang)

        # 降低语言纯度要求，允许混合语言内容
        if source_purity < 0.4 or target_purity < 0.4:
            return False

        # 4. 特殊情况：如果相似度很高，放宽其他限制
        similarity_score = self._calculate_translation_similarity(source_text, target_text, source_lang, target_lang)
        if similarity_score > 0.6:
            return True

        # 5. 结构相似性检查：翻译对应该有相似的结构（放宽标准）
        structure_similarity = self._calculate_structure_similarity(source_text, target_text)
        if structure_similarity < 0.2:
            return False

        return True

    def _calculate_text_complexity(self, text: str) -> int:
        """计算文本复杂度"""
        complexity = 0

        # 字符种类
        if any(c.isalpha() for c in text):
            complexity += 1
        if any(c.isdigit() for c in text):
            complexity += 1
        if any(c in '，。！？；：""''（）【】' for c in text):
            complexity += 1
        if any(c in ',.!?;:""\'()[]' for c in text):
            complexity += 1

        # 长度因子
        if len(text) > 10:
            complexity += 1
        if len(text) > 30:
            complexity += 1

        # 词汇数量
        words = len(text.split())
        if words > 2:
            complexity += 1
        if words > 5:
            complexity += 1

        return complexity

    def _calculate_language_purity(self, text: str, lang: str) -> float:
        """计算语言纯度（文本中目标语言字符的比例）"""
        if not text.strip():
            return 0.0

        total_chars = len([c for c in text if c.isalnum()])
        if total_chars == 0:
            return 0.0

        if lang == "zh":
            # 中文字符
            target_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        else:
            # 英文字符
            target_chars = len([c for c in text if 'a' <= c.lower() <= 'z'])

        return target_chars / total_chars

    def _calculate_structure_similarity(self, text1: str, text2: str) -> float:
        """计算结构相似性"""
        # 标点符号模式
        punct1 = ''.join([c for c in text1 if not c.isalnum() and not c.isspace()])
        punct2 = ''.join([c for c in text2 if not c.isalnum() and not c.isspace()])

        # 计算标点符号相似度
        if not punct1 and not punct2:
            punct_similarity = 1.0
        elif not punct1 or not punct2:
            punct_similarity = 0.0
        else:
            # 简单的字符匹配
            common_punct = sum(1 for c in punct1 if c in punct2)
            punct_similarity = common_punct / max(len(punct1), len(punct2))

        # 词汇数量相似度
        words1 = len(text1.split())
        words2 = len(text2.split())
        if words1 == 0 and words2 == 0:
            word_similarity = 1.0
        else:
            word_similarity = min(words1, words2) / max(words1, words2) if max(words1, words2) > 0 else 0.0

        # 综合相似度
        return (punct_similarity + word_similarity) / 2

    def _get_similarity_threshold(self, line1: str, line2: str) -> float:
        """
        根据文本长度动态计算相似度阈值

        Args:
            line1: 第一行文本
            line2: 第二行文本

        Returns:
            float: 相似度阈值
        """
        # 计算平均长度
        avg_length = (len(line1) + len(line2)) / 2

        # 短文本（平均长度 <= 10）使用较低阈值
        if avg_length <= 10:
            return 0.2
        # 中等文本（平均长度 <= 30）使用中等阈值
        elif avg_length <= 30:
            return 0.25
        # 长文本使用较高阈值
        else:
            return 0.3

    def _calculate_translation_similarity(self, source_text: str, target_text: str, source_lang: str, target_lang: str) -> float:
        """
        计算两个文本之间的翻译相似度

        Args:
            source_text: 源语言文本
            target_text: 目标语言文本
            source_lang: 源语言代码
            target_lang: 目标语言代码

        Returns:
            float: 相似度分数 (0-1)
        """
        score = 0.0

        # 1. 长度相似性（翻译通常长度相近）
        len_ratio = min(len(source_text), len(target_text)) / max(len(source_text), len(target_text))
        if len_ratio > 0.5:
            score += 0.2

        # 2. 数字和特殊字符匹配
        source_numbers = re.findall(r'\d+', source_text)
        target_numbers = re.findall(r'\d+', target_text)
        if source_numbers and source_numbers == target_numbers:
            score += 0.3

        # 3. 标点符号相似性
        source_punct = re.findall(r'[^\w\s]', source_text)
        target_punct = re.findall(r'[^\w\s]', target_text)
        if len(source_punct) > 0 and len(target_punct) > 0:
            punct_similarity = len(set(source_punct) & set(target_punct)) / max(len(set(source_punct)), len(set(target_punct)))
            score += punct_similarity * 0.2

        # 4. 特定语言对的特殊检查
        if source_lang == "zh" and target_lang == "en":
            score += self._check_chinese_english_similarity(source_text, target_text)

        # 5. 常见翻译模式检查
        if self._has_common_translation_patterns(source_text, target_text, source_lang, target_lang):
            score += 0.3

        return min(score, 1.0)

    def _check_chinese_english_similarity(self, chinese_text: str, english_text: str) -> float:
        """检查中英文翻译的特殊相似性"""
        score = 0.0

        # 检查是否包含常见的翻译关键词
        translation_keywords = {
            '申请': ['application', 'apply'],
            '文件': ['document', 'file'],
            '状态': ['state', 'status'],
            '类型': ['type', 'types'],
            '手册': ['manual'],
            '程序': ['procedure'],
            '技术': ['technical'],
            '图纸': ['drawing', 'drawings'],
            '表单': ['form'],
            '分发': ['distribution'],
            '基地': ['base'],
            '修订': ['revision'],
            '废止': ['obsolete'],
            '首次': ['initial'],
            '发行': ['issue']
        }

        english_lower = english_text.lower()
        matched_keywords = 0
        total_keywords = 0

        for chinese_word, english_words in translation_keywords.items():
            if chinese_word in chinese_text:
                total_keywords += 1
                if any(eng_word in english_lower for eng_word in english_words):
                    matched_keywords += 1

        if total_keywords > 0:
            score = matched_keywords / total_keywords

        return score * 0.4  # 最多贡献0.4分

    def _has_common_translation_patterns(self, source_text: str, target_text: str, source_lang: str, target_lang: str) -> bool:
        """检查是否有常见的翻译模式"""
        # 检查是否都包含冒号（常见于标题翻译）
        if ':' in source_text and ':' in target_text:
            return True

        # 检查是否都包含括号
        if '(' in source_text and ')' in source_text and '(' in target_text and ')' in target_text:
            return True

        # 检查是否都是短句（可能是标题或标签）
        if len(source_text.split()) <= 5 and len(target_text.split()) <= 8:
            return True

        return False

    def is_translation_complete(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> bool:
        """
        检查文本是否已完成翻译
        
        Args:
            text: 要检测的文本
            source_lang: 源语言代码
            target_lang: 目标语言代码
            
        Returns:
            bool: 是否已完成翻译
        """
        should_skip, _ = self.should_skip_translation(text, source_lang, target_lang)
        return should_skip
