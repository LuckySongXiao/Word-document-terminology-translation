from openai import OpenAI
import logging
from typing import Optional, Dict
from .base_translator import BaseTranslator

logger = logging.getLogger(__name__)

class SiliconFlowTranslator(BaseTranslator):
    def __init__(self, api_key: str, model: str = "deepseek-ai/DeepSeek-V2.5", timeout: int = 60):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        if api_key:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://api.siliconflow.cn/v1",
                timeout=timeout
            )

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
        try:
            # 获取源语言和目标语言的名称
            source_lang_name = self._get_language_name(source_lang)
            target_lang_name = self._get_language_name(target_lang)

            # --- 术语预处理和提示构建逻辑开始 ---
            processed_text_for_llm = str(text)  # 将发送给LLM的文本（可能包含占位符）
            final_prompt_text = ""  # LLM的完整提示字符串

            term_instructions_for_llm = []
            placeholders_used = False

            if terminology_dict:
                # 按键（源术语）长度降序排序，以便优先匹配较长的术语
                # 假设 terminology_dict.keys() 是源语言，.values() 是目标语言
                sorted_terms = sorted(terminology_dict.items(), key=lambda item: len(item[0]), reverse=True)

                temp_processed_text = str(text)  # 在副本上操作

                for i, (source_term_from_dict, target_term_from_dict) in enumerate(sorted_terms):
                    placeholder = f"[术语{i}]"

                    if source_term_from_dict in temp_processed_text:
                        temp_processed_text = temp_processed_text.replace(source_term_from_dict, placeholder)
                        term_instructions_for_llm.append(
                            f"占位符 {placeholder} (原文为 \"{source_term_from_dict}\") 必须严格翻译为 \"{target_term_from_dict}\"。"
                        )
                        placeholders_used = True

                if placeholders_used:
                    processed_text_for_llm = temp_processed_text
            # --- 术语预处理和提示构建逻辑结束 ---

            # 构建 prompt_content
            if placeholders_used:
                instruction_block = "术语指令 (请严格遵守)：\n" + "\n".join(term_instructions_for_llm)
                prompt_core = (
                    f"你是一位高度熟练的专业翻译员。请将以下{source_lang_name}文本翻译成{target_lang_name}。\n"
                    f"{instruction_block}\n\n"
                    "通用翻译要求：\n"
                    "1. 对于任何占位符，请严格遵守上述术语指令。\n"
                    "2. 对于文本中未被占位符覆盖的部分，请确保翻译专业、准确且自然流畅。\n"
                    "3. 最终输出必须仅为翻译后的文本，不含任何额外评论、分析或如 '原文：' 或 '译文：' 等标记。\n"
                )
                if prompt:
                    prompt_core += f"\n额外的用户提供风格/语气指导：{prompt}\n"

                if target_lang == "zh":
                    final_prompt_text = (
                        prompt_core +
                        f"\n待翻译文本 (可能包含占位符)：\n{processed_text_for_llm}\n\n"
                        "请提供纯中文翻译："
                    )
                else:
                    final_prompt_text = (
                        prompt_core +
                        f"\n待翻译文本 (可能包含占位符)：\n{processed_text_for_llm}\n\n"
                        f"请提供纯{target_lang_name}翻译："
                    )
            elif terminology_dict:  # 术语存在，但未找到术语进行占位符替换
                prompt_core = (
                    f"你是一位高度熟练的专业翻译员。请将以下{source_lang_name}文本翻译成{target_lang_name}。\n\n"
                    "请严格使用此术语映射：\n"
                )
                for s_term, t_term in terminology_dict.items(): # 假设 terminology_dict 已正确定向
                    prompt_core += f"[{s_term}] → [{t_term}]\n"

                prompt_core += (
                    "\n通用翻译要求：\n"
                    "1. 上述映射中的所有术语必须按规定翻译。\n"
                    "2. 其余文本确保翻译专业、准确且自然流畅。\n"
                    "3. 最终输出必须仅为翻译后的文本，不含任何额外评论、分析或如 '原文：' 或 '译文：' 等标记。\n"
                )
                if prompt:
                    prompt_core += f"\n额外的用户提供风格/语气指导：{prompt}\n"

                if target_lang == "zh":
                    final_prompt_text = (
                        prompt_core +
                        f"\n待翻译文本：\n{text}\n\n"  # 此处为原始文本
                        "请提供纯中文翻译："
                    )
                else:
                    final_prompt_text = (
                        prompt_core +
                        f"\n待翻译文本：\n{text}\n\n"  # 此处为原始文本
                        f"请提供纯{target_lang_name}翻译："
                    )
            else:  # 完全没有术语
                prompt_core = (
                    f"你是一位高度熟练的专业翻译员。请将以下{source_lang_name}文本翻译成{target_lang_name}。\n\n"
                    "通用翻译要求：\n"
                    "1. 确保翻译专业、准确且自然流畅。\n"
                    "2. 最终输出必须仅为翻译后的文本，不含任何额外评论、分析或如 '原文：' 或 '译文：' 等标记。\n"
                )
                if prompt:
                    prompt_core += f"\n额外的用户提供风格/语气指导：{prompt}\n"

                if target_lang == "zh":
                    final_prompt_text = (
                        prompt_core +
                        f"\n待翻译文本：\n{text}\n\n"
                        "请提供纯中文翻译："
                    )
                else:
                    final_prompt_text = (
                        prompt_core +
                        f"\n待翻译文本：\n{text}\n\n"
                        f"请提供纯{target_lang_name}翻译："
                    )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的翻译助手，请严格遵循用户提供的所有翻译指令，特别是关于术语和占位符的指令。"},
                    {"role": "user", "content": final_prompt_text}
                ],
                temperature=0.2,
                stream=False
            )

            raw_translation = response.choices[0].message.content.strip()
            # 过滤思维链
            translation = self._filter_output(raw_translation, source_lang, target_lang)

            # 如果使用了占位符，需要将占位符替换回实际术语
            if placeholders_used and terminology_dict:
                logger.info("开始恢复占位符为实际术语...")
                # 创建占位符到目标术语的映射
                placeholder_to_term = {}
                sorted_terms = sorted(terminology_dict.items(), key=lambda item: len(item[0]), reverse=True)

                for i, (source_term_from_dict, target_term_from_dict) in enumerate(sorted_terms):
                    placeholder = f"[术语{i}]"
                    if placeholder in translation:
                        placeholder_to_term[placeholder] = target_term_from_dict

                # 替换占位符为实际术语
                replaced_count = 0
                for placeholder, target_term in placeholder_to_term.items():
                    if placeholder in translation:
                        before_replace = translation
                        translation = translation.replace(placeholder, target_term)
                        if before_replace != translation:
                            replaced_count += 1
                            logger.info(f"恢复占位符: {placeholder} -> {target_term}")
                        else:
                            logger.warning(f"占位符替换失败: {placeholder}")
                    else:
                        logger.warning(f"在翻译结果中未找到占位符: {placeholder}")

                # 检查是否还有未替换的占位符
                import re
                remaining_placeholders = re.findall(r'\[术语\d+\]', translation)
                if remaining_placeholders:
                    logger.warning(f"仍有 {len(remaining_placeholders)} 个占位符未被替换: {remaining_placeholders[:5]}")

                    # 尝试更宽松的匹配方式进行最后的恢复
                    for placeholder_text in remaining_placeholders:
                        # 提取索引
                        index_match = re.search(r'术语(\d+)', placeholder_text)
                        if index_match:
                            index = int(index_match.group(1))
                            if index < len(sorted_terms):
                                target_term = sorted_terms[index][1]
                                translation = translation.replace(placeholder_text, target_term)
                                logger.info(f"使用最终替换恢复占位符: {placeholder_text} -> {target_term}")

                logger.info(f"占位符恢复完成，成功替换 {replaced_count} 个占位符，最终翻译结果长度: {len(translation)}")

            logger.info(f"硅基流动翻译成功，结果长度: {len(translation)}")
            return translation

        except Exception as e:
            logger.error(f"硅基流动翻译失败: {str(e)}")
            raise Exception(f"硅基流动翻译失败: {str(e)}")

    # 使用BaseTranslator中的_filter_output方法

    def _get_language_name(self, lang_code: str) -> str:
        """
        根据语言代码获取语言名称

        Args:
            lang_code: 语言代码

        Returns:
            str: 语言名称
        """
        language_map = {
            "zh": "中文",
            "en": "英文",
            "ja": "日文",
            "ko": "韩文",
            "fr": "法文",
            "de": "德文",
            "es": "西班牙文",
            "it": "意大利文",
            "ru": "俄文",
            "pt": "葡萄牙文",
            "nl": "荷兰文",
            "ar": "阿拉伯文",
            "th": "泰文",
            "vi": "越南文"
        }
        return language_map.get(lang_code, "未知语言")

    def get_available_models(self) -> list:
        """获取可用的模型列表"""
        # 目前硅基流动支持的模型列表
        return [
            "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
            "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
            "internlm/internlm2_5-7b-chat",
            "Qwen/Qwen2-7B-Instruct",
            "Qwen/Qwen2-1.5B-Instruct",
            "THUDM/glm-4-9b-chat",
            "THUDM/chatglm3-6b",
            "Qwen/Qwen2.5-Coder-7B-Instruct",
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct-128K",
            "Qwen/QwQ-32B-Preview",
            "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
            "Qwen/QwQ-32B",
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1"
        ]