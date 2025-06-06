import logging
import json
import requests
import traceback
import warnings
import time
import ssl
from typing import Optional, Dict
from .base_translator import BaseTranslator
from urllib3.exceptions import InsecureRequestWarning
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.poolmanager import PoolManager

# 禁用不安全请求的警告
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# 创建自定义的SSL适配器，使用TLS 1.2
class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLSv1_2
        )

logger = logging.getLogger(__name__)

class ZhipuAITranslator(BaseTranslator):
    def __init__(self, api_key: str, model: str = "glm-4-flash", temperature: float = 0.2, timeout: int = 60):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

        # 使用测试确认的正确URL
        self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

        # 记录初始化信息
        logger.info(f"初始化智谱AI翻译器，模型: {self.model}, API Key前缀: {self.api_key[:8] if self.api_key else 'None'}")

    def _check_zhipuai_available(self, skip_network_check=False) -> bool:
        """检查智谱AI服务是否可用

        Args:
            skip_network_check: 是否跳过网络连接检查（用于内网环境）
        """
        if not self.api_key:
            logger.warning("未配置智谱AI API Key")
            return False

        # 检查是否为内网环境或离线模式
        if skip_network_check:
            logger.info("跳过智谱AI网络连接检查（内网模式）")
            return True

        # 检查环境变量是否设置了离线模式
        import os
        if os.getenv('OFFLINE_MODE', '').lower() in ['true', '1', 'yes']:
            logger.info("检测到离线模式环境变量，跳过智谱AI连接检查")
            return True

        # 最大重试次数
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                logger.info(f"尝试连接智谱AI服务，API URL: {self.api_url}")

                # 创建一个会话对象
                session = requests.Session()

                # 添加自定义的TLS适配器
                adapter = TLSAdapter()
                session.mount('https://', adapter)

                # 添加重试机制
                retry_strategy = Retry(
                    total=3,
                    backoff_factor=0.5,
                    status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["POST"]
                )
                session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
                }

                data = {
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": "你好"}
                    ],
                    "temperature": self.temperature
                }

                # 添加详细的请求日志
                logger.debug(f"智谱AI请求头: {headers}")
                logger.debug(f"智谱AI请求数据: {json.dumps(data, ensure_ascii=False)}")

                # 禁用SSL验证以排除证书问题
                response = session.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=15,
                    verify=False  # 禁用SSL验证
                )

                logger.info(f"智谱AI连接测试响应状态码: {response.status_code}")
                logger.debug(f"响应头: {dict(response.headers)}")

                if response.status_code == 200:
                    result = response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    # 过滤掉可能导致编码问题的特殊字符
                    safe_content = content.encode('ascii', 'ignore').decode('ascii') if content else ""
                    logger.info(f"智谱AI连接测试成功! 响应: {safe_content[:30]}...")
                    return True
                else:
                    # 输出错误信息以便调试
                    logger.error(f"响应状态码: {response.status_code}, 响应内容: {response.text}")
                    try:
                        error_info = response.json() if response.text else {"error": "未知错误"}
                        logger.error(f"智谱AI连接失败，状态码: {response.status_code}, 错误信息: {json.dumps(error_info, ensure_ascii=False)}")
                    except:
                        logger.error(f"智谱AI连接失败，状态码: {response.status_code}, 响应: {response.text}")

                    # 如果是认证错误，不再重试
                    if response.status_code in [401, 403]:
                        return False

                    # 其他错误继续重试
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"将在2秒后进行第{retry_count+1}次重试...")
                        time.sleep(2)
                    else:
                        logger.error(f"已达到最大重试次数({max_retries})，放弃连接")
                        return False

            except requests.exceptions.SSLError as ssl_err:
                logger.error(f"智谱AI连接SSL错误: {str(ssl_err)}")
                logger.error(f"详细错误: {traceback.format_exc()}")

                # SSL错误重试
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"SSL错误，将在2秒后进行第{retry_count+1}次重试...")
                    time.sleep(2)
                else:
                    logger.error(f"已达到最大重试次数({max_retries})，放弃连接")
                    return False

            except Exception as e:
                logger.error(f"智谱AI连接测试失败: {str(e)}")
                logger.error(f"详细错误: {traceback.format_exc()}")

                # 一般错误重试
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"将在2秒后进行第{retry_count+1}次重试...")
                    time.sleep(2)
                else:
                    logger.error(f"已达到最大重试次数({max_retries})，放弃连接")
                    return False

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
        if not self.api_key:
            raise Exception("未配置智谱AI API Key")

        try:
            # 获取源语言和目标语言的名称
            source_lang_name = self._get_language_name(source_lang)
            target_lang_name = self._get_language_name(target_lang)

            # 构建提示词
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

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一位专业的翻译助手，请严格遵循用户提供的所有翻译指令，特别是关于术语和占位符的指令。"},
                    {"role": "user", "content": final_prompt_text}
                ],
                "temperature": self.temperature
            }

            logger.info(f"发送翻译请求到智谱AI，模型: {self.model}")

            # 创建一个会话对象
            session = requests.Session()

            # 添加自定义的TLS适配器
            adapter = TLSAdapter()
            session.mount('https://', adapter)

            # 添加重试机制
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["POST"]
            )
            session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

            # 使用会话发送请求
            response = session.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=self.timeout,
                verify=False  # 禁用SSL验证
            )

            if response.status_code == 200:
                result = response.json()
                raw_translation = result["choices"][0]["message"]["content"].strip()
                # 过滤思维链
                translation = self._filter_output(raw_translation, source_lang, target_lang)

                # 如果使用了占位符，需要将占位符替换回实际术语
                if placeholders_used and terminology_dict:
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

                logger.info(f"智谱AI翻译成功，结果长度: {len(translation)}")
                return translation
            else:
                error_info = response.json() if response.text else {"error": "未知错误"}
                error_msg = f"智谱AI HTTP错误 {response.status_code}: {json.dumps(error_info, ensure_ascii=False)}"
                logger.error(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            logger.error(f"智谱AI翻译失败: {str(e)}")
            raise Exception(f"智谱AI翻译失败: {str(e)}")

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

    # 使用BaseTranslator中的_filter_output方法

    def get_available_models(self) -> list:
        """获取可用的模型列表"""
        # 根据测试结果，这些模型都能正常工作
        return [
            "glm-4-flash",
            "glm-4-plus",
            "glm-4-long"
        ]