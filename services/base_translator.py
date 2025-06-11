from abc import ABC, abstractmethod
from typing import Optional, Dict

class BaseTranslator(ABC):
    @abstractmethod
    def translate(self, text: str, terminology_dict: Optional[Dict] = None, source_lang: str = "zh", target_lang: str = "en", prompt: str = None) -> str:
        """
        翻译文本

        Args:
            text: 要翻译的文本
            terminology_dict: 术语词典
            source_lang: 源语言代码，默认为中文(zh)
            target_lang: 目标语言代码，默认为英文(en)
            prompt: 可选的翻译提示词，用于指导翻译风格和质量

        Returns:
            str: 翻译后的文本
        """
        pass

    def _filter_output(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        """
        过滤模型输出，去除思维链、不必要的标记和提示性文本，并选择最佳翻译结果

        Args:
            text: 模型输出的文本
            source_lang: 源语言代码，默认为中文(zh)
            target_lang: 目标语言代码，默认为英文(en)

        Returns:
            str: 过滤后的最佳翻译文本
        """
        # 如果输入为空，直接返回
        if not text or not text.strip():
            return ""

        # 如果存在<think>标签，提取非思维链部分
        if "<think>" in text:
            # 分割所有的<think>块
            parts = text.split("<think>")
            # 获取最后一个非思维链的内容
            final_text = parts[-1].strip()
            # 如果最后一部分还包含</think>，取其后面的内容
            if "</think>" in final_text:
                final_text = final_text.split("</think>")[-1].strip()
            text = final_text

        # 去除常见的标记前缀
        text = text.strip()

        # 首先检查是否有多个翻译结果，选择最佳的一个
        text = self._select_best_translation(text, target_lang)

        # 定义需要过滤的提示性文本列表
        prompt_texts = [
            "请提供具体的英文文本，以便进行翻译",
            "请提供具体术语内容，以便进行翻译",
            "请提供具体需要翻译的英文文本，以便我进行准确的翻译",
            "请提供英文文本",
            "请提供需要翻译的文本",
            "请提供具体的文本内容",
            "请提供原文",
            "请提供需要翻译的内容",
            "以下是翻译结果",
            "以下是我的翻译",
            "以下是译文",
            "这是翻译结果",
            "这是我的翻译",
            "翻译如下",
            "翻译结果如下",
            "译文如下"
        ]

        # 检查文本是否只包含提示性文本
        for prompt_text in prompt_texts:
            if text.strip() == prompt_text or text.strip() == prompt_text + "。" or text.strip() == prompt_text + ":":
                return ""  # 如果文本只包含提示性文本，则返回空字符串

        # 去除"原文："和"译文："等标记
        lines = text.split('\n')
        filtered_lines = []

        # 检查是否有"原文：xxx 译文：yyy"格式的行
        has_original_translation_pair = False
        for line in lines:
            if "原文：" in line and "译文：" in line:
                has_original_translation_pair = True
                break

        # 如果存在"原文：xxx 译文：yyy"格式，只保留译文部分
        if has_original_translation_pair and target_lang == "zh":
            result_text = ""
            for line in lines:
                if "译文：" in line:
                    # 提取译文部分
                    translation_part = line.split("译文：", 1)[1].strip()
                    if translation_part:
                        result_text += translation_part + "\n"
            if result_text.strip():
                return result_text.strip()

        # 处理常规行
        for line in lines:
            line_stripped = line.strip()

            # 跳过只包含"原文："或"译文："的行
            if line_stripped in ["原文：", "译文："]:
                continue

            # 去除行首的"原文："或"译文："标记
            if line_stripped.startswith("原文："):
                continue
            if line_stripped.startswith("译文："):
                line = line.replace("译文：", "", 1).strip()

            # 去除行尾的"原文："或"译文："标记
            if line_stripped.endswith("原文："):
                line = line.replace("原文：", "", 1).strip()
            if line_stripped.endswith("译文："):
                line = line.replace("译文：", "", 1).strip()

            # 检查是否是提示性文本
            is_prompt_text = False
            for prompt_text in prompt_texts:
                if prompt_text in line_stripped or line_stripped.startswith(prompt_text):
                    is_prompt_text = True
                    break

            if is_prompt_text:
                continue

            # 如果是空行，跳过
            if not line_stripped:
                continue

            # 去除行中的"原文："和"译文："标记（针对混合在一行的情况）
            if "原文：" in line and "译文：" in line and target_lang == "zh":
                # 提取译文部分
                parts = line.split("译文：", 1)
                if len(parts) > 1:
                    line = parts[1].strip()

            filtered_lines.append(line)

        # 重新组合文本
        filtered_text = '\n'.join(filtered_lines)

        # 外语→中文翻译模式下的额外过滤
        if target_lang == "zh":
            # 去除常见的前缀短语
            prefixes_to_remove = [
                "以下是翻译：",
                "翻译结果：",
                "翻译如下：",
                "译文如下：",
                "翻译：",
                "译文：",
                "这是翻译：",
                "这是译文：",
                "以下是中文翻译：",
                "中文翻译：",
                "中文译文："
            ]

            for prefix in prefixes_to_remove:
                if filtered_text.startswith(prefix):
                    filtered_text = filtered_text[len(prefix):].strip()

            # 去除常见的后缀短语
            suffixes_to_remove = [
                "（以上是翻译结果）",
                "（这是翻译结果）",
                "（翻译完成）",
                "（完成翻译）",
                "（以上为翻译）",
                "（以上为译文）"
            ]

            for suffix in suffixes_to_remove:
                if filtered_text.endswith(suffix):
                    filtered_text = filtered_text[:-len(suffix)].strip()

        # 如果过滤后的文本为空，但原文不为空，则可能过滤过度
        # 在这种情况下，返回原始文本
        if not filtered_text.strip() and text.strip():
            return text.strip()

        return filtered_text

    def _select_best_translation(self, text: str, target_lang: str) -> str:
        """
        从多个翻译结果中选择最佳的一个

        Args:
            text: 可能包含多个翻译结果的文本
            target_lang: 目标语言代码

        Returns:
            str: 最佳的翻译结果
        """
        if not text or not text.strip():
            return ""

        # 按行分割文本
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # 如果只有一行，直接返回
        if len(lines) <= 1:
            return text.strip()

        # 检查是否有重复的翻译结果
        unique_lines = []
        seen_lines = set()

        for line in lines:
            # 标准化处理：去除标点符号差异，转换为小写进行比较
            normalized_line = line.lower().replace('.', '').replace(',', '').replace(':', '').replace(';', '').strip()

            # 如果这行内容已经见过（忽略大小写和标点差异），跳过
            if normalized_line in seen_lines:
                continue

            # 过滤掉明显的提示性文本
            if any(prompt in line.lower() for prompt in [
                'translation', 'translate', '翻译', '译文', '原文',
                'here is', 'this is', 'the translation is',
                'below is', 'following is'
            ]):
                continue

            seen_lines.add(normalized_line)
            unique_lines.append(line)

        # 如果没有有效的行，返回原文
        if not unique_lines:
            return text.strip()

        # 如果只有一个有效结果，返回它
        if len(unique_lines) == 1:
            return unique_lines[0]

        # 选择最佳翻译的策略
        best_translation = self._choose_best_from_candidates(unique_lines, target_lang)

        return best_translation

    def _choose_best_from_candidates(self, candidates: list, target_lang: str) -> str:
        """
        从候选翻译中选择最佳的一个

        Args:
            candidates: 候选翻译列表
            target_lang: 目标语言代码

        Returns:
            str: 最佳翻译
        """
        if not candidates:
            return ""

        if len(candidates) == 1:
            return candidates[0]

        # 评分策略
        scored_candidates = []

        for candidate in candidates:
            score = 0

            # 长度评分：适中长度的翻译通常更好
            length = len(candidate)
            if 5 <= length <= 200:  # 合理的长度范围
                score += 10
            elif length > 200:
                score -= 5  # 过长的翻译可能包含多余信息
            elif length < 5:
                score -= 10  # 过短的翻译可能不完整

            # 语言一致性评分
            if target_lang == "en":
                # 英文翻译：应该主要包含英文字符
                english_chars = sum(1 for c in candidate if c.isalpha() and ord(c) < 128)
                chinese_chars = sum(1 for c in candidate if '\u4e00' <= c <= '\u9fff')
                if english_chars > chinese_chars:
                    score += 15
                else:
                    score -= 10
            elif target_lang == "zh":
                # 中文翻译：应该主要包含中文字符
                chinese_chars = sum(1 for c in candidate if '\u4e00' <= c <= '\u9fff')
                english_chars = sum(1 for c in candidate if c.isalpha() and ord(c) < 128)
                if chinese_chars > english_chars:
                    score += 15
                else:
                    score -= 10

            # 格式评分：避免包含多余的标记
            if not any(marker in candidate.lower() for marker in [
                'translation:', 'translated:', '翻译:', '译文:',
                'original:', '原文:', 'result:', '结果:'
            ]):
                score += 5

            # 完整性评分：避免截断的翻译
            if candidate.endswith('.') or candidate.endswith('。') or candidate.endswith('!') or candidate.endswith('？'):
                score += 3

            scored_candidates.append((candidate, score))

        # 按分数排序，选择最高分的
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        return scored_candidates[0][0]