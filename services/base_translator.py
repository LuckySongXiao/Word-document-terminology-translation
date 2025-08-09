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
        过滤模型输出，去除思维链、不必要的标记和提示性文本

        Args:
            text: 模型输出的文本
            source_lang: 源语言代码，默认为中文(zh)
            target_lang: 目标语言代码，默认为英文(en)

        Returns:
            str: 过滤后的文本
        """
        # 如果输入为空，直接返回
        if not text or not text.strip():
            return ""

        # 记录原始文本用于调试
        original_text = text

        # 1. 处理思维链标签 - 更全面的处理
        # 处理<think>...</think>标签
        import re

        # 移除所有<think>...</think>块
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # 处理未闭合的<think>标签
        if "<think>" in text.lower():
            parts = re.split(r'<think>', text, flags=re.IGNORECASE)
            if len(parts) > 1:
                # 取第一部分（<think>之前的内容）
                text = parts[0].strip()
                # 如果第一部分为空，尝试取最后一部分
                if not text and len(parts) > 1:
                    text = parts[-1].strip()

        # 2. 处理其他思考过程标记
        thinking_patterns = [
            r'让我.*?思考.*?[：:]',
            r'我需要.*?分析.*?[：:]',
            r'首先.*?分析.*?[：:]',
            r'这个.*?术语.*?应该.*?翻译.*?为.*?[：:]',
            r'根据.*?上下文.*?[：:]',
            r'考虑到.*?[：:]',
            r'分析.*?[：:]',
            r'思考.*?[：:]'
        ]

        for pattern in thinking_patterns:
            # 移除匹配的思考过程
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # 3. 处理"位错"等术语的思考过程
        # 检测并移除术语分析过程
        dislocation_patterns = [
            r'位错.*?是.*?材料.*?科学.*?中.*?的.*?概念.*?[，。]',
            r'位错.*?在.*?英文.*?中.*?通常.*?翻译.*?为.*?[，。]',
            r'位错.*?这个.*?术语.*?[，。]',
            r'在.*?材料.*?科学.*?领域.*?[，。]',
            r'这个.*?术语.*?在.*?英文.*?中.*?[，。]'
        ]

        for pattern in dislocation_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # 4. 移除常见的分析性语句
        analysis_patterns = [
            r'这里.*?应该.*?翻译.*?为.*?[：:]',
            r'最.*?合适.*?的.*?翻译.*?是.*?[：:]',
            r'最.*?准确.*?的.*?翻译.*?是.*?[：:]',
            r'最.*?恰当.*?的.*?翻译.*?是.*?[：:]',
            r'比较.*?合适.*?的.*?翻译.*?是.*?[：:]',
            r'应该.*?翻译.*?为.*?[：:]',
            r'可以.*?翻译.*?为.*?[：:]',
            r'翻译.*?为.*?比较.*?合适.*?[：:]',
            r'在.*?这个.*?语境.*?下.*?[：:]'
        ]

        for pattern in analysis_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # 去除常见的标记前缀
        text = text.strip()

        # 5. 定义需要过滤的提示性文本列表（扩展版）
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
            "译文如下",
            # 新增的过滤项，针对智谱AI可能输出的提示词内容
            "将以下中文文本翻译成英文",
            "将以下英文文本翻译成中文",
            "将以下中文文本翻译成",
            "将以下英文文本翻译成",
            "术语翻译规则",
            "术语对照",
            "翻译风格要求",
            "文本：",
            "翻译：",
            "术语指令",
            "请严格遵守",
            "占位符",
            "必须严格翻译为",
            # 英文提示词
            "translation:",
            "translate:",
            "text:",
            "original:",
            "result:",
            "output:",
            "terminology reference:",
            "reference:",
            "note:",
            "translation test",
            "test translation",
            # 新增：针对思考过程的过滤
            "让我来分析",
            "让我思考",
            "我来分析",
            "我需要分析",
            "首先分析",
            "根据上下文",
            "考虑到",
            "这个术语",
            "在材料科学中",
            "在英文中通常翻译为",
            "最合适的翻译是",
            "最准确的翻译是",
            "最恰当的翻译是",
            "应该翻译为",
            "可以翻译为",
            "比较合适的翻译",
            "在这个语境下"
        ]

        # 6. 智能提取最终翻译结果
        # 如果文本包含多个句子，尝试找到最终的翻译结果
        sentences = re.split(r'[。！？.!?：:]', text)
        if len(sentences) > 1:
            # 查找最可能是翻译结果的句子
            translation_candidates = []
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                # 跳过明显的分析性语句
                is_analysis = False
                analysis_patterns = [
                    "让我", "分析", "考虑", "思考", "应该翻译", "最合适", "最准确", "最恰当",
                    "翻译结果", "以下是", "以上是", "这是", "根据", "在英文中", "在材料科学"
                ]

                for pattern in analysis_patterns:
                    if pattern in sentence:
                        is_analysis = True
                        break

                if not is_analysis:
                    # 检查是否包含目标语言的特征
                    if target_lang == "en":
                        # 英文翻译：应该主要包含英文字符
                        if re.search(r'[a-zA-Z]', sentence) and len(re.findall(r'[a-zA-Z]', sentence)) > len(sentence) * 0.5:
                            translation_candidates.append(sentence)
                    elif target_lang == "zh":
                        # 中文翻译：应该主要包含中文字符
                        if re.search(r'[\u4e00-\u9fff]', sentence) and len(re.findall(r'[\u4e00-\u9fff]', sentence)) > len(sentence) * 0.3:
                            translation_candidates.append(sentence)
                    else:
                        # 其他语言，保留非分析性语句
                        translation_candidates.append(sentence)

            # 如果找到候选翻译，使用最后一个（通常是最终结果）
            if translation_candidates:
                text = translation_candidates[-1].strip()
                # 如果最后一个候选结果太短，尝试使用倒数第二个
                if len(text) < 3 and len(translation_candidates) > 1:
                    text = translation_candidates[-2].strip()

        # 检查文本是否只包含提示性文本
        for prompt_text in prompt_texts:
            if text.strip() == prompt_text or text.strip() == prompt_text + "。" or text.strip() == prompt_text + ":":
                return ""  # 如果文本只包含提示性文本，则返回空字符串

        # 7. 去除"原文："和"译文："等标记
        lines = text.split('\n')
        filtered_lines = []

        # 检查是否有"原文：xxx 译文：yyy"格式的行
        has_original_translation_pair = False
        for line in lines:
            if "原文：" in line and "译文：" in line:
                has_original_translation_pair = True
                break

        # 如果存在"原文：xxx 译文：yyy"格式，只保留译文部分
        if has_original_translation_pair:
            result_text = ""
            for line in lines:
                if "译文：" in line:
                    # 提取译文部分
                    translation_part = line.split("译文：", 1)[1].strip()
                    if translation_part:
                        result_text += translation_part + "\n"
            if result_text.strip():
                return result_text.strip()

        # 8. 处理常规行
        for line in lines:
            line_stripped = line.strip()

            # 跳过空行
            if not line_stripped:
                continue

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

            # 检查是否是提示性文本或分析性语句
            is_prompt_text = False
            for prompt_text in prompt_texts:
                if prompt_text.lower() in line_stripped.lower():
                    is_prompt_text = True
                    break

            if is_prompt_text:
                continue

            # 检查是否是思考过程的句子
            thinking_indicators = [
                "让我", "我来", "我需要", "首先", "根据", "考虑到", "分析", "思考",
                "这个术语", "在材料科学", "在英文中", "最合适", "最准确", "最恰当",
                "应该翻译", "可以翻译", "比较合适", "在这个语境", "所以最合适的翻译是",
                "以下是翻译结果", "以上是翻译结果", "翻译结果："
            ]

            is_thinking = False
            for indicator in thinking_indicators:
                if indicator in line_stripped:
                    is_thinking = True
                    break

            if is_thinking:
                continue

            # 特殊处理：如果行以"文本："开头，提取后面的内容
            if line_stripped.startswith("文本："):
                extracted_content = line_stripped[3:].strip()
                if extracted_content:
                    line = extracted_content
                else:
                    continue

            # 特殊处理：如果行以"翻译："开头，提取后面的内容
            if line_stripped.startswith("翻译："):
                extracted_content = line_stripped[3:].strip()
                if extracted_content:
                    line = extracted_content
                else:
                    continue

            # 特殊处理：如果行以"Translation:"开头，提取后面的内容
            if line_stripped.lower().startswith("translation:"):
                extracted_content = line_stripped[12:].strip()
                if extracted_content:
                    line = extracted_content
                else:
                    continue

            # 特殊处理：如果行只包含"Translation:"，跳过
            if line_stripped.lower() == "translation:":
                continue

            # 如果是空行，跳过
            if not line.strip():
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

        # 9. 外语→中文翻译模式下的额外过滤
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
                "中文译文：",
                "最终翻译：",
                "最终译文：",
                "答案：",
                "结果："
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

        # 10. 最终验证和清理
        # 移除多余的换行符
        filtered_text = re.sub(r'\n+', '\n', filtered_text).strip()

        # 如果结果包含明显的分析性内容，尝试提取核心翻译
        if len(filtered_text.split()) > 20:  # 如果结果过长，可能包含分析
            # 尝试找到最简洁的翻译结果
            lines = filtered_text.split('\n')
            shortest_meaningful_line = ""
            min_length = float('inf')

            for line in lines:
                line = line.strip()
                if line and len(line) < min_length and len(line) > 2:
                    # 检查是否包含目标语言特征
                    if target_lang == "en" and re.search(r'[a-zA-Z]', line):
                        shortest_meaningful_line = line
                        min_length = len(line)
                    elif target_lang == "zh" and re.search(r'[\u4e00-\u9fff]', line):
                        shortest_meaningful_line = line
                        min_length = len(line)

            if shortest_meaningful_line and len(shortest_meaningful_line) < len(filtered_text) * 0.5:
                filtered_text = shortest_meaningful_line

        # 如果过滤后的文本为空，但原文不为空，则可能过滤过度
        # 在这种情况下，返回原始文本的最后一个有意义的句子
        if not filtered_text.strip() and original_text.strip():
            # 尝试从原始文本中提取最后一个有意义的句子
            sentences = re.split(r'[。！？.!?]', original_text)
            for sentence in reversed(sentences):
                sentence = sentence.strip()
                if sentence and len(sentence) > 2:
                    return sentence
            return original_text.strip()

        return filtered_text