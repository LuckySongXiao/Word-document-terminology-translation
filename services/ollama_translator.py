import requests
import logging
import json
from typing import Optional, Dict
from .base_translator import BaseTranslator

logger = logging.getLogger(__name__)

class OllamaTranslator(BaseTranslator):
    def __init__(self, model: str, api_url: str, model_list_timeout: int = 10, translate_timeout: int = 60, use_direct_replacement: bool = True):
        self.model = model
        # 统一使用正确的API端点
        if "localhost:11434" in api_url:
            self.base_url = "http://localhost:11434"
        else:
            self.base_url = api_url.rstrip('/api')  # 移除末尾的/api
        self.api_url = f"{self.base_url}/api/generate"
        self.model_list_timeout = model_list_timeout
        self.translate_timeout = translate_timeout
        self.use_direct_replacement = use_direct_replacement  # 是否使用直接术语替换

    def get_available_models(self) -> list:
        """获取可用的模型列表"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.model_list_timeout)
            if response.status_code == 200:
                models = response.json()
                return [model['name'] for model in models['models']]
            return []
        except Exception as e:
            logger.error(f"获取Ollama模型列表失败: {str(e)}")
            return []

    def _should_skip_translation(self, text: str) -> bool:
        """判断是否应该跳过翻译的内容（避免发送可能导致超时的内容）"""
        if not text or not text.strip():
            return True

        import re
        clean_text = text.strip()

        # 检查是否已经是双语内容（包含中文和英文）
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', clean_text))
        has_english = bool(re.search(r'[A-Za-z]', clean_text))

        # 如果同时包含中文和英文，且内容较长，很可能已经是翻译过的双语内容
        if has_chinese and has_english and len(clean_text) > 10:
            # 进一步检查是否有明显的双语特征
            lines = clean_text.split('\n')
            if len(lines) >= 2:
                # 检查是否有中英文分行的模式
                chinese_lines = [line for line in lines if re.search(r'[\u4e00-\u9fff]', line)]
                english_lines = [line for line in lines if re.search(r'[A-Za-z]', line) and not re.search(r'[\u4e00-\u9fff]', line)]

                # 如果有明显的中英文分行，跳过翻译
                if len(chinese_lines) > 0 and len(english_lines) > 0:
                    logger.info(f"跳过翻译内容（已包含双语）: {clean_text[:50]}...")
                    return True

            # 检查是否包含常见的双语格式标记
            bilingual_indicators = [
                r'[\u4e00-\u9fff].*[A-Za-z].*[\u4e00-\u9fff]',  # 中文-英文-中文模式
                r'[A-Za-z].*[\u4e00-\u9fff].*[A-Za-z]',  # 英文-中文-英文模式
            ]

            for pattern in bilingual_indicators:
                if re.search(pattern, clean_text):
                    logger.info(f"跳过翻译内容（检测到双语模式）: {clean_text[:50]}...")
                    return True

        # 跳过纯数字
        number_patterns = [
            r'^[-+]?\d+$',  # 整数
            r'^[-+]?\d*\.\d+$',  # 小数
            r'^[-+]?\d+\.\d*$',  # 小数
            r'^[-+]?\d+%$',  # 百分比
            r'^[-+]?\d*\.\d+%$',  # 小数百分比
            r'^[-+]?\d+[eE][-+]?\d+$',  # 科学计数法
            r'^\d{1,3}(,\d{3})*(\.\d+)?$',  # 千分位分隔的数字
        ]

        for pattern in number_patterns:
            if re.match(pattern, clean_text):
                return True

        # 跳过纯编码
        if re.match(r'^[A-Za-z0-9\-_\.]+$', clean_text) and len(clean_text) > 1:
            has_digit = bool(re.search(r'\d', clean_text))
            has_letter = bool(re.search(r'[A-Za-z]', clean_text))
            has_separator = bool(re.search(r'[-_\.]', clean_text))
            is_all_upper = clean_text.isupper()

            if (has_digit and has_letter) or has_separator or (is_all_upper and len(clean_text) <= 10):
                return True

        return False

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
        # 检查是否应该跳过翻译（直接返回原文）
        if self._should_skip_translation(text):
            logger.info(f"跳过翻译内容（纯数字/编码）: {text[:50]}...")
            return text

        # 获取源语言和目标语言的名称
        source_lang_name = self._get_language_name(source_lang)
        target_lang_name = self._get_language_name(target_lang)

        # --- 术语预处理和提示构建逻辑开始 ---
        processed_text_for_llm = str(text)  # 将发送给LLM的文本
        final_prompt_text = ""  # LLM的完整提示字符串

        term_instructions_for_llm = []
        placeholders_used = False
        direct_replacement_used = False

        if terminology_dict:
            if self.use_direct_replacement:
                # 使用新的直接替换方法，避免占位符恢复问题
                logger.info("使用直接术语替换模式")
                # 按键（源术语）长度降序排序，以便优先匹配较长的术语
                sorted_terms = sorted(terminology_dict.items(), key=lambda item: len(item[0]), reverse=True)

                temp_processed_text = str(text)  # 在副本上操作

                for source_term_from_dict, target_term_from_dict in sorted_terms:
                    if source_term_from_dict in temp_processed_text and target_term_from_dict:
                        temp_processed_text = temp_processed_text.replace(source_term_from_dict, target_term_from_dict)
                        direct_replacement_used = True
                        logger.info(f"直接替换术语: {source_term_from_dict} -> {target_term_from_dict}")

                if direct_replacement_used:
                    processed_text_for_llm = temp_processed_text
                    logger.info(f"直接替换后的文本: {processed_text_for_llm[:100]}...")
            else:
                # 使用原有的占位符方法
                logger.info("使用占位符术语替换模式")
                # 按键（源术语）长度降序排序，以便优先匹配较长的术语
                sorted_terms = sorted(terminology_dict.items(), key=lambda item: len(item[0]), reverse=True)

                temp_processed_text = str(text)  # 在副本上操作

                for i, (source_term_from_dict, target_term_from_dict) in enumerate(sorted_terms):
                    placeholder = f"__TERM_PH_{i}__"

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
        if direct_replacement_used:
            # 直接替换模式：术语已经直接替换，不需要特殊指令
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
                    f"\n待翻译文本：\n{processed_text_for_llm}\n\n"
                    "请提供纯中文翻译："
                )
            else:
                final_prompt_text = (
                    prompt_core +
                    f"\n待翻译文本：\n{processed_text_for_llm}\n\n"
                    f"请提供纯{target_lang_name}翻译："
                )
        elif placeholders_used:
            # 占位符模式
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
        elif terminology_dict:  # 术语存在，但未找到术语进行替换
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

        data = {
            "model": self.model,
            "prompt": final_prompt_text,
            "stream": False
        }

        try:
            # 使用统一的API URL
            response = requests.post(self.api_url, json=data, timeout=self.translate_timeout)
            if response.status_code == 200:
                try:
                    result = response.json()
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {str(e)}")
                    logger.error(f"服务器响应: {response.text}")
                    raise Exception(f"服务器返回了无效的JSON数据: {response.text[:200]}")

                # 过滤输出结果
                translation = self._filter_output(result.get("response", ""), source_lang, target_lang)
                # 如果过滤后为空，返回原始响应
                if not translation:
                    translation = result.get("response", "").strip()

                # 如果使用了占位符（非直接替换模式），需要将占位符替换回实际术语
                if placeholders_used and terminology_dict and not direct_replacement_used:
                    logger.info("开始恢复占位符为实际术语...")
                    # 创建占位符到目标术语的映射
                    placeholder_to_term = {}
                    sorted_terms = sorted(terminology_dict.items(), key=lambda item: len(item[0]), reverse=True)

                    for i, (source_term_from_dict, target_term_from_dict) in enumerate(sorted_terms):
                        placeholder = f"__TERM_PH_{i}__"
                        if placeholder in translation:
                            placeholder_to_term[placeholder] = target_term_from_dict

                    # 替换占位符为实际术语
                    for placeholder, target_term in placeholder_to_term.items():
                        translation = translation.replace(placeholder, target_term)
                        logger.info(f"恢复占位符: {placeholder} -> {target_term}")

                    logger.info(f"占位符恢复完成，最终翻译结果长度: {len(translation)}")
                elif direct_replacement_used:
                    logger.info("使用直接替换模式，无需恢复占位符")

                return translation
            else:
                error_msg = f"Ollama API错误: HTTP {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - {response.text}"
                raise Exception(error_msg)
        except requests.exceptions.ConnectionError:
            raise Exception("无法连接到Ollama服务，请确保Ollama正在运行")
        except requests.exceptions.Timeout:
            raise Exception("请求超时，请检查网络连接或增加超时时间")
        except Exception as e:
            if "JSON" not in str(e):  # 如果不是已经处理过的JSON错误
                logger.error(f"翻译请求失败: {str(e)}")
            raise

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