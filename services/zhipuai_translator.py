import logging
import json
import requests
import traceback
import warnings
import time
import ssl
import os
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
    def __init__(self, api_key: str = None, model: str = "glm-4-flash-250414", temperature: float = 0.2, timeout: int = 60):
        # 优先从环境变量读取API Key
        self.api_key = api_key or os.getenv('ZHIPU_API_KEY')

        # 如果环境变量和参数都没有，尝试从配置文件读取
        if not self.api_key:
            try:
                config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "API_config", "zhipu_api.json")
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        self.api_key = config.get('api_key', '')
            except Exception as e:
                logger.warning(f"读取API配置文件失败: {e}")

        self.model = model
        self.temperature = temperature
        self.timeout = timeout

        # 使用测试确认的正确URL
        self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

        # 记录初始化信息
        api_key_display = self.api_key[:8] + "..." if self.api_key and len(self.api_key) > 8 else 'None'
        logger.info(f"初始化智谱AI翻译器，模型: {self.model}, API Key前缀: {api_key_display}")

        if self.api_key:
            logger.info(f"API Key来源: {'环境变量' if os.getenv('ZHIPU_API_KEY') else '配置文件'}")
        else:
            logger.error("未找到有效的智谱AI API Key")

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
            # 检查是否为多条目内容，如果是，则分别翻译
            if self._is_multi_item_content(text):
                logger.info("检测到多条目内容，使用分段翻译策略")
                return self._translate_multi_item_content(text, terminology_dict, source_lang, target_lang, prompt)

            # 构建提示词
            # --- 新的直接术语替换策略开始 ---
            processed_text_for_llm = str(text)  # 将发送给LLM的文本
            final_prompt_text = ""  # LLM的完整提示字符串

            # 记录替换的术语，用于日志
            replaced_terms = []

            if terminology_dict:
                # 按键（源术语）长度降序排序，以便优先匹配较长的术语
                # 假设 terminology_dict.keys() 是源语言，.values() 是目标语言
                sorted_terms = sorted(terminology_dict.items(), key=lambda item: len(item[0]), reverse=True)

                temp_processed_text = str(text)  # 在副本上操作

                for source_term_from_dict, target_term_from_dict in sorted_terms:
                    # 跳过空术语
                    if not source_term_from_dict or not source_term_from_dict.strip():
                        continue

                    # 检查源术语是否在文本中
                    if source_term_from_dict in temp_processed_text:
                        # 使用正则表达式进行更精确的替换，避免部分匹配
                        import re

                        # 对于中文术语，使用边界匹配
                        if re.search(r'[\u4e00-\u9fff]', source_term_from_dict):
                            # 中文术语：确保不是其他词的一部分
                            pattern = r'(?<![a-zA-Z0-9\u4e00-\u9fff])' + re.escape(source_term_from_dict) + r'(?![a-zA-Z0-9\u4e00-\u9fff])'
                        else:
                            # 英文术语：使用单词边界
                            pattern = r'\b' + re.escape(source_term_from_dict) + r'\b'

                        # 查找匹配项
                        matches = list(re.finditer(pattern, temp_processed_text))
                        if matches:
                            # 执行替换
                            before_replace = temp_processed_text
                            temp_processed_text = re.sub(pattern, target_term_from_dict, temp_processed_text)

                            # 验证替换是否成功
                            if before_replace != temp_processed_text:
                                replaced_terms.append((source_term_from_dict, target_term_from_dict))
                                logger.info(f"直接替换术语: {source_term_from_dict} -> {target_term_from_dict} (匹配次数: {len(matches)})")
                            else:
                                logger.warning(f"术语替换失败: {source_term_from_dict}")
                        else:
                            # 如果正则表达式没有匹配，但简单字符串包含检查通过，使用简单替换作为后备
                            before_replace = temp_processed_text
                            temp_processed_text = temp_processed_text.replace(source_term_from_dict, target_term_from_dict)
                            if before_replace != temp_processed_text:
                                replaced_terms.append((source_term_from_dict, target_term_from_dict))
                                logger.info(f"使用简单替换术语: {source_term_from_dict} -> {target_term_from_dict}")
                    else:
                        logger.debug(f"术语未在文本中找到: {source_term_from_dict}")

                processed_text_for_llm = temp_processed_text

                # 记录替换统计
                if replaced_terms:
                    logger.info(f"共替换了 {len(replaced_terms)} 个术语")
                    # 记录前5个替换的术语样本
                    terms_sample = replaced_terms[:5]
                    logger.info(f"替换术语样本（前5个）: {terms_sample}")
            # --- 新的直接术语替换策略结束 ---

            # 构建明确的翻译提示词 - 强调直接输出结果
            # 根据源语言和目标语言构建明确的翻译指令
            source_lang_name = self._get_language_name(source_lang)
            target_lang_name = self._get_language_name(target_lang)

            # 构建强调直接输出的提示词
            base_instruction = f"请直接将以下{source_lang_name}文本翻译成{target_lang_name}，只输出翻译结果，不要包含任何分析、解释或思考过程。如果文本包含多个条目（用分号、句号或数字序号分隔），必须完整翻译所有条目，保持原文结构"

            # 构建更强化的提示词，特别强调完整翻译
            complete_instruction = (
                f"{base_instruction}\n\n"
                "特别注意：\n"
                "- 如果文本包含数字序号（如1、2、3、），必须翻译所有序号对应的内容\n"
                "- 如果文本包含分号（；）分隔的多个部分，必须翻译所有部分\n"
                "- 不要省略任何条目或内容\n"
                "- 保持原文的完整结构和所有信息\n\n"
                "要翻译的文本："
            )

            if terminology_dict and replaced_terms:
                # 有术语且进行了替换
                final_prompt_text = f"{complete_instruction}\n{processed_text_for_llm}"
            elif terminology_dict:  # 术语存在，但未找到术语进行替换
                # 明确的翻译指令
                final_prompt_text = f"{complete_instruction}\n{text}"
            else:  # 完全没有术语
                # 明确的翻译指令
                final_prompt_text = f"{complete_instruction}\n{text}"

            # 如果有用户自定义提示词，添加到开头
            if prompt:
                final_prompt_text = f"翻译风格要求：{prompt}\n\n" + final_prompt_text

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            # 构建强调直接输出的系统消息，包含示例
            system_message = (
                "你是一位专业的翻译助手。请严格按照以下要求工作：\n"
                "1. 只输出最终的翻译结果，不要包含任何分析、解释、思考过程或多余的文字\n"
                "2. 不要使用'让我分析'、'根据上下文'、'这个术语'等表述\n"
                "3. 不要输出'翻译结果：'、'译文：'等标记\n"
                "4. 直接给出准确、自然的翻译结果\n"
                "5. 如果文本包含多个条目（用分号、句号或数字序号分隔），必须完整翻译所有条目，不要遗漏任何部分\n"
                "6. 保持原文的结构和格式，包括数字序号、分号等分隔符\n\n"
                "示例：\n"
                "原文：1、产品质量合格；2、包装完整。\n"
                "正确翻译：1. Product quality is qualified; 2. Packaging is complete.\n"
                "错误翻译（不完整）：Packaging is complete.\n\n"
                "原文：备注：1、按照标准A分类；2、按照标准B检测。\n"
                "正确翻译：Note: 1. Classify according to standard A; 2. Test according to standard B.\n"
                "错误翻译（不完整）：Test according to standard B."
            )

            # 构建Few-shot学习的消息序列
            messages = [
                {"role": "system", "content": system_message},
                # 添加示例对话
                {"role": "user", "content": "请翻译：1、产品质量合格；2、包装完整。"},
                {"role": "assistant", "content": "1. Product quality is qualified; 2. Packaging is complete."},
                {"role": "user", "content": "请翻译：备注：1、按照标准A分类；2、按照标准B检测。"},
                {"role": "assistant", "content": "Note: 1. Classify according to standard A; 2. Test according to standard B."},
                # 实际要翻译的内容
                {"role": "user", "content": final_prompt_text}
            ]

            data = {
                "model": self.model,
                "messages": messages,
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

                # 新的直接术语替换策略不需要占位符还原
                # 术语已经在翻译前直接替换，翻译结果应该包含正确的目标术语
                if terminology_dict and replaced_terms:
                    logger.info(f"使用直接术语替换策略，已替换 {len(replaced_terms)} 个术语，无需后处理")

                # 翻译质量检查
                quality_issues = self._check_translation_quality(text, translation, source_lang, target_lang)
                if quality_issues:
                    logger.warning(f"翻译质量检查发现问题: {quality_issues}")

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

    def _check_translation_quality(self, original_text: str, translated_text: str, source_lang: str, target_lang: str) -> list:
        """
        检查翻译质量，识别潜在问题

        Args:
            original_text: 原文
            translated_text: 译文
            source_lang: 源语言
            target_lang: 目标语言

        Returns:
            list: 发现的问题列表
        """
        issues = []

        if not translated_text or not translated_text.strip():
            issues.append("翻译结果为空")
            return issues

        # 1. 检查是否包含占位符残留
        import re
        placeholder_patterns = [
            r'\[术语\d+\]',
            r'\[Term\s*\d+\]',
            r'\[test\]',
            r'\[text\]'
        ]

        for pattern in placeholder_patterns:
            matches = re.findall(pattern, translated_text, re.IGNORECASE)
            if matches:
                issues.append(f"包含未替换的占位符: {matches}")

        # 2. 检查是否包含提示词
        prompt_indicators = [
            '将以下', '翻译', 'translation:', 'text:', 'translate'
        ]

        for indicator in prompt_indicators:
            if indicator.lower() in translated_text.lower():
                issues.append(f"包含提示词: {indicator}")

        # 3. 检查长度异常（译文过短或过长）
        original_len = len(original_text.strip())
        translated_len = len(translated_text.strip())

        if translated_len < original_len * 0.3:
            issues.append("译文过短，可能翻译不完整")
        elif translated_len > original_len * 3:
            issues.append("译文过长，可能包含多余内容")

        # 4. 检查是否原文和译文完全相同（对于需要翻译的内容）
        if original_text.strip() == translated_text.strip() and original_len > 5:
            # 检查是否真的需要翻译
            if source_lang == "zh" and re.search(r'[\u4e00-\u9fff]', original_text):
                issues.append("中文原文未被翻译")
            elif source_lang == "en" and re.match(r'^[a-zA-Z\s\d\.\,\-\+\(\)\[\]]+$', original_text):
                issues.append("英文原文未被翻译")

        # 5. 检查多条目内容是否完整翻译
        # 检测原文中的条目数量（通过分号、句号、数字序号等分隔）
        original_items = self._count_content_items(original_text)
        translated_items = self._count_content_items(translated_text)

        if original_items > 1 and translated_items < original_items:
            issues.append(f"可能存在内容遗漏：原文有{original_items}个条目，译文只有{translated_items}个条目")

        # 6. 检查关键数字和符号是否保留
        # 提取原文中的数字、符号等关键信息
        original_numbers = re.findall(r'[≤<>≥]\s*\d+(?:\.\d+)?(?:μs|ms|s|%|℃|°C)', original_text)
        translated_numbers = re.findall(r'[≤<>≥]\s*\d+(?:\.\d+)?(?:μs|ms|s|%|℃|°C)', translated_text)

        if len(original_numbers) > len(translated_numbers):
            missing_numbers = set(original_numbers) - set(translated_numbers)
            if missing_numbers:
                issues.append(f"译文中缺失关键数值信息: {missing_numbers}")

        return issues

    def _count_content_items(self, text: str) -> int:
        """
        计算文本中的内容条目数量

        Args:
            text: 要分析的文本

        Returns:
            int: 条目数量
        """
        if not text or not text.strip():
            return 0

        import re

        # 方法1：通过数字序号计算（如"1、"、"2、"等）
        numbered_items = re.findall(r'\d+[、．.]', text)
        if len(numbered_items) >= 2:
            return len(numbered_items)

        # 方法2：通过分号分隔计算（包括中文和英文分号）
        semicolon_items = []
        for sep in ['；', ';']:
            items = [item.strip() for item in text.split(sep) if item.strip()]
            if len(items) >= 2:
                semicolon_items = items
                break

        if len(semicolon_items) >= 2:
            return len(semicolon_items)

        # 方法3：通过句号分隔计算（排除小数点）
        sentences = re.split(r'[。．](?!\d)', text)
        meaningful_sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]
        if len(meaningful_sentences) >= 2:
            return len(meaningful_sentences)

        # 默认返回1（单个条目）
        return 1

    def _is_multi_item_content(self, text: str) -> bool:
        """
        检测文本是否包含多个条目

        Args:
            text: 要检测的文本

        Returns:
            bool: 是否为多条目内容
        """
        if not text or not text.strip():
            return False

        import re

        # 检查是否有数字序号（如"1、"、"2、"等）
        numbered_items = re.findall(r'\d+[、．.]', text)
        if len(numbered_items) >= 2:
            return True

        # 检查是否有分号分隔的多个部分
        semicolon_items = [item.strip() for item in text.split('；') if item.strip()]
        if len(semicolon_items) >= 2:
            return True

        return False

    def _translate_multi_item_content(self, text: str, terminology_dict: Optional[Dict] = None,
                                    source_lang: str = "zh", target_lang: str = "en",
                                    prompt: str = None) -> str:
        """
        分段翻译多条目内容

        Args:
            text: 要翻译的多条目文本
            terminology_dict: 术语词典
            source_lang: 源语言代码
            target_lang: 目标语言代码
            prompt: 翻译提示词

        Returns:
            str: 翻译结果
        """
        import re

        logger.info(f"开始分段翻译多条目内容: {text}")

        # 首先尝试按数字序号分割
        numbered_pattern = r'(\d+[、．.])'
        parts = re.split(numbered_pattern, text)

        if len(parts) > 2:  # 有数字序号分割
            logger.info("使用数字序号分割策略")
            translated_parts = []
            current_item = ""

            for i, part in enumerate(parts):
                if re.match(r'\d+[、．.]', part):
                    # 这是一个序号
                    if current_item:
                        # 翻译前一个条目
                        translated_item = self._translate_single_item(current_item, terminology_dict, source_lang, target_lang, prompt)
                        translated_parts.append(translated_item)
                    current_item = part
                else:
                    current_item += part

            # 翻译最后一个条目
            if current_item:
                translated_item = self._translate_single_item(current_item, terminology_dict, source_lang, target_lang, prompt)
                translated_parts.append(translated_item)

            # 更好的合并方式：保持原有的分隔符
            result = " ".join(translated_parts)
            # 确保分号之间有适当的空格
            result = result.replace(";", "; ")
            # 移除多余的空格
            result = re.sub(r'\s+', ' ', result).strip()
            logger.info(f"数字序号分割翻译结果: {result}")
            return result

        # 尝试按分号分割
        semicolon_parts = [item.strip() for item in text.split('；') if item.strip()]
        if len(semicolon_parts) >= 2:
            logger.info("使用分号分割策略")
            translated_parts = []

            for i, part in enumerate(semicolon_parts):
                translated_item = self._translate_single_item(part, terminology_dict, source_lang, target_lang, prompt)
                translated_parts.append(translated_item)

            result = "; ".join(translated_parts)
            logger.info(f"分号分割翻译结果: {result}")
            return result

        # 如果无法分割，回退到原始翻译方法
        logger.warning("无法分割多条目内容，回退到原始翻译方法")
        return self._translate_single_content(text, terminology_dict, source_lang, target_lang, prompt)

    def _translate_single_item(self, text: str, terminology_dict: Optional[Dict] = None,
                             source_lang: str = "zh", target_lang: str = "en",
                             prompt: str = None) -> str:
        """
        翻译单个条目

        Args:
            text: 要翻译的单个条目文本
            terminology_dict: 术语词典
            source_lang: 源语言代码
            target_lang: 目标语言代码
            prompt: 翻译提示词

        Returns:
            str: 翻译结果
        """
        logger.info(f"翻译单个条目: {text}")

        # 使用原始的翻译逻辑，但不使用多条目检测
        return self._translate_single_content(text, terminology_dict, source_lang, target_lang, prompt)

    def _translate_single_content(self, text: str, terminology_dict: Optional[Dict] = None,
                                source_lang: str = "zh", target_lang: str = "en",
                                prompt: str = None) -> str:
        """
        翻译单个内容（原始翻译逻辑）
        """
        # 简化版本：直接使用基本的翻译请求，不进行多条目检测
        if not self.api_key:
            raise Exception("未配置智谱AI API Key")

        # 构建简单的翻译提示词
        source_lang_name = self._get_language_name(source_lang)
        target_lang_name = self._get_language_name(target_lang)

        simple_instruction = f"请直接将以下{source_lang_name}文本翻译成{target_lang_name}，只输出翻译结果："

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 简化的系统消息
        simple_system_message = (
            "你是一位专业的翻译助手。请直接输出翻译结果，不要包含任何分析、解释或多余的文字。"
        )

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": simple_system_message},
                {"role": "user", "content": f"{simple_instruction}\n{text}"}
            ],
            "temperature": self.temperature
        }

        # 创建会话并发送请求
        session = requests.Session()
        adapter = TLSAdapter()
        session.mount('https://', adapter)

        response = session.post(
            self.api_url,
            headers=headers,
            json=data,
            timeout=self.timeout,
            verify=False
        )

        if response.status_code == 200:
            result = response.json()
            translation = result["choices"][0]["message"]["content"].strip()
            # 简单过滤
            translation = self._filter_output(translation, source_lang, target_lang)
            return translation
        else:
            error_info = response.json() if response.text else {"error": "未知错误"}
            error_msg = f"智谱AI HTTP错误 {response.status_code}: {json.dumps(error_info, ensure_ascii=False)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def get_available_models(self) -> list:
        """获取可用的模型列表"""
        # 根据测试结果，这些模型都能正常工作
        return [
            "glm-4-flash-250414"
        ]