import requests
import json
import logging
from typing import Optional, Dict
from .base_translator import BaseTranslator

logger = logging.getLogger(__name__)

class IntranetTranslator(BaseTranslator):
    def __init__(self, api_url: str, model: str = "deepseek-r1-70b", timeout: int = 60):
        """
        初始化内网翻译器

        Args:
            api_url: 内网API地址，如 http://192.168.100.71:8000/v1/chat/completions
            model: 使用的模型名称
            timeout: 请求超时时间
        """
        self.api_url = api_url
        self.model = model
        self.timeout = timeout

        # 确保API URL格式正确
        if not self.api_url.endswith('/v1/chat/completions'):
            if self.api_url.endswith('/'):
                self.api_url = self.api_url + 'v1/chat/completions'
            else:
                self.api_url = self.api_url + '/v1/chat/completions'

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
        if not text.strip():
            return ""

        # 语言映射
        lang_map = {
            "zh": "中文",
            "en": "英文",
            "ja": "日文",
            "ko": "韩文",
            "fr": "法文",
            "de": "德文",
            "es": "西班牙文",
            "it": "意大利文",
            "pt": "葡萄牙文",
            "ru": "俄文"
        }

        source_lang_name = lang_map.get(source_lang, source_lang)
        target_lang_name = lang_map.get(target_lang, target_lang)

        # 构建翻译提示词
        if terminology_dict and len(terminology_dict) > 0:
            # 有术语的情况
            terminology_text = "\n".join([f"{k}: {v}" for k, v in terminology_dict.items()])

            prompt_core = (
                f"你是一位高度熟练的专业翻译员。请将以下{source_lang_name}文本翻译成{target_lang_name}。\n\n"
                "通用翻译要求：\n"
                "1. 确保翻译专业、准确且自然流畅。\n"
                "2. 最终输出必须仅为翻译后的文本，不含任何额外评论、分析或如 '原文：' 或 '译文：' 等标记。\n"
                "3. 严格按照提供的术语对照表进行翻译，确保术语翻译的一致性和准确性。\n\n"
                f"术语对照表：\n{terminology_text}\n"
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
        else:
            # 没有术语的情况
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

        # 构建请求数据
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一位专业的翻译助手，请严格遵循用户提供的所有翻译指令，特别是关于术语和占位符的指令。"},
                {"role": "user", "content": final_prompt_text}
            ],
            "stream": False,
            "temperature": 0.2
        }

        try:
            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json=data,
                timeout=self.timeout
            )

            if response.status_code == 200:
                try:
                    result = response.json()
                    raw_translation = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                    # 过滤思维链和其他不必要的输出
                    translation = self._filter_output(raw_translation, source_lang, target_lang)

                    if not translation:
                        logger.warning("翻译结果为空，返回原始响应")
                        translation = raw_translation

                    return translation

                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    logger.error(f"解析内网API响应失败: {str(e)}")
                    logger.error(f"服务器响应: {response.text}")
                    raise Exception(f"内网API返回了无效的响应格式: {response.text[:200]}")
            else:
                logger.error(f"内网API请求失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                raise Exception(f"内网API请求失败: HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            logger.error(f"内网API请求超时 (超时时间: {self.timeout}秒)")
            raise Exception(f"内网API请求超时，请检查网络连接或增加超时时间")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"无法连接到内网API: {str(e)}")
            raise Exception(f"无法连接到内网API，请检查服务器地址和网络连接")
        except Exception as e:
            logger.error(f"内网翻译失败: {str(e)}")
            raise

    def get_available_models(self) -> list:
        """
        获取可用的模型列表
        注意：由于内网API可能不提供模型列表接口，这里返回常见的模型名称
        """
        # 常见的内网模型列表，可以根据实际情况调整
        return [
            "deepseek-r1-70b",
            "deepseek-r1-32b",
            "deepseek-r1-8b",
            "qwen2.5-72b",
            "qwen2.5-32b",
            "qwen2.5-14b",
            "qwen2.5-7b",
            "llama3.1-70b",
            "llama3.1-8b"
        ]

    def test_connection(self) -> bool:
        """
        测试与内网API的连接

        Returns:
            bool: 连接是否成功
        """
        try:
            test_data = {
                "model": self.model,
                "messages": [{"role": "user", "content": "测试连接"}],
                "stream": False,
                "max_tokens": 10
            }

            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json=test_data,
                timeout=5  # 减少超时时间，快速检测
            )

            if response.status_code == 200:
                logger.info("内网API连接测试成功")
                return True
            else:
                logger.warning(f"内网API连接测试失败，状态码: {response.status_code}")
                return False

        except requests.exceptions.ConnectTimeout:
            logger.warning("内网API连接超时，请检查网络连接")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"内网API连接错误: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"内网API连接测试失败: {str(e)}")
            return False
