import requests
import json
import logging
import os
from typing import Dict, Optional
from abc import ABC, abstractmethod
from .ollama_manager import setup_ollama
import pandas as pd
from datetime import datetime
from .ollama_translator import OllamaTranslator
from .base_translator import BaseTranslator
from .siliconflow_translator import SiliconFlowTranslator
from .zhipuai_translator import ZhipuAITranslator
from .intranet_translator import IntranetTranslator
import traceback

logger = logging.getLogger(__name__)

class BaseTranslator(ABC):
    @abstractmethod
    def translate(self, text: str) -> str:
        pass

# 注意：OllamaTranslator 类已经从 .ollama_translator 导入，不需要在这里重新定义

class TranslationService:
    def __init__(self):
        self.use_fallback = False
        self.load_config()

        # 初始化 translators 字典
        self.translators = {}

        # 初始化 current_translator_type
        self.current_translator_type = self.config.get('current_translator_type', 'zhipuai')

        # 初始化所有翻译器
        try:
            # 初始化智谱AI翻译器
            zhipuai_translator = self._init_zhipuai_translator()
            if zhipuai_translator:
                self.translators['zhipuai'] = zhipuai_translator

            # 初始化Ollama翻译器
            ollama_translator = self._init_ollama_translator()
            if ollama_translator:
                self.translators['ollama'] = ollama_translator

            # 初始化硅基流动翻译器
            siliconflow_translator = self._init_siliconflow_translator()
            if siliconflow_translator:
                self.translators['siliconflow'] = siliconflow_translator

            # 初始化内网翻译器
            intranet_translator = self._init_intranet_translator()
            if intranet_translator:
                self.translators['intranet'] = intranet_translator

        except Exception as e:
            logger.error(f"初始化翻译器失败: {str(e)}")
            logger.error(traceback.format_exc())

        # 设置Ollama环境
        available_models = setup_ollama()
        if available_models:
            self.config['fallback_translator']['available_models'] = available_models
            if self.config['fallback_translator']['model'] not in available_models:
                self.config['fallback_translator']['model'] = available_models[0]

        # 检查是否为内网环境
        is_intranet = self._detect_intranet_environment()

        # 检查智谱AI可用性
        if 'zhipuai' in self.translators:
            if not self._check_zhipuai_available(skip_network_check=is_intranet):
                logger.warning("无法连接到智谱AI，自动切换到Ollama模式")
                self.use_fallback = True
        else:
            logger.warning("主翻译器不支持可用性检查，默认切换到Ollama模式")
            self.use_fallback = True

    def load_config(self):
        """加载配置"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        # 初始化主要翻译器
        try:
            primary_config = self.config['primary_translator']
            if primary_config['type'] == 'zhipuai':
                # 使用 ZhipuAITranslator
                from .zhipuai_translator import ZhipuAITranslator
                self.primary_translator = ZhipuAITranslator(
                    api_key=primary_config['api_key'],
                    model=primary_config.get('model', 'glm-4-flash'),
                    temperature=primary_config.get('temperature', 0.3)
                )
                logger.info("使用智谱AI翻译器初始化完成")
            else:
                raise ValueError(f"不支持的主要翻译器类型: {primary_config['type']}")
        except Exception as e:
            logger.error(f"初始化主要翻译器失败: {str(e)}")
            logger.error(traceback.format_exc())
            # 如果主翻译器初始化失败，标记使用备用翻译器
            self.use_fallback = True

        # 初始化备用翻译器
        try:
            fallback_config = self.config['fallback_translator']
            if fallback_config['type'] == 'ollama':
                from .ollama_translator import OllamaTranslator
                self.fallback_translator = OllamaTranslator(
                    fallback_config['model'],
                    fallback_config['api_url'],
                    fallback_config.get("model_list_timeout", 10),
                    fallback_config.get("translate_timeout", 60)
                )
            else:
                raise ValueError(f"不支持的备用翻译器类型: {fallback_config['type']}")
        except Exception as e:
            logger.error(f"初始化备用翻译器失败: {str(e)}")
            logger.error(traceback.format_exc())

    def set_translator_type(self, translator_type: str):
        """设置当前使用的翻译器类型"""
        if translator_type in ["zhipuai", "ollama", "siliconflow", "intranet"]:
            self.current_translator_type = translator_type
            # 更新配置文件
            self.config["current_translator_type"] = translator_type
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        return False

    def set_model(self, model: str):
        """设置当前翻译器使用的模型"""
        translator_type = self.current_translator_type

        # 更新配置文件中的模型设置
        if translator_type == "zhipuai":
            if "zhipuai_translator" not in self.config:
                self.config["zhipuai_translator"] = {}
            self.config["zhipuai_translator"]["model"] = model

            # 如果翻译器实例存在，更新其模型
            if "zhipuai" in self.translators and hasattr(self.translators["zhipuai"], "model"):
                self.translators["zhipuai"].model = model

        elif translator_type == "ollama":
            if "fallback_translator" not in self.config:
                self.config["fallback_translator"] = {}
            self.config["fallback_translator"]["model"] = model

            # 如果翻译器实例存在，更新其模型
            if "ollama" in self.translators and hasattr(self.translators["ollama"], "model"):
                self.translators["ollama"].model = model

        elif translator_type == "siliconflow":
            if "siliconflow_translator" not in self.config:
                self.config["siliconflow_translator"] = {}
            self.config["siliconflow_translator"]["model"] = model

            # 如果翻译器实例存在，更新其模型
            if "siliconflow" in self.translators and hasattr(self.translators["siliconflow"], "model"):
                self.translators["siliconflow"].model = model

        elif translator_type == "intranet":
            if "intranet_translator" not in self.config:
                self.config["intranet_translator"] = {}
            self.config["intranet_translator"]["model"] = model

            # 如果翻译器实例存在，更新其模型
            if "intranet" in self.translators and hasattr(self.translators["intranet"], "model"):
                self.translators["intranet"].model = model
        else:
            return False

        # 保存配置文件
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)

        return True

    def get_available_models(self, translator_type: str = None) -> list:
        """获取指定翻译器类型的可用模型列表"""
        if translator_type is None:
            translator_type = self.current_translator_type

        translator = self.translators.get(translator_type)
        if translator:
            if hasattr(translator, "get_available_models"):
                return translator.get_available_models()
        return []

    def get_current_translator_type(self) -> str:
        """获取当前使用的翻译器类型"""
        return self.current_translator_type

    def get_current_model(self) -> str:
        """获取当前使用的模型"""
        translator_type = self.current_translator_type

        if translator_type == "zhipuai" and "zhipuai" in self.translators:
            return self.translators["zhipuai"].model
        elif translator_type == "ollama" and "ollama" in self.translators:
            return self.translators["ollama"].model
        elif translator_type == "siliconflow" and "siliconflow" in self.translators:
            return self.translators["siliconflow"].model
        elif translator_type == "intranet" and "intranet" in self.translators:
            return self.translators["intranet"].model

        # 如果无法获取当前模型，返回配置中的默认模型
        if translator_type == "zhipuai":
            return self.config.get("zhipuai_translator", {}).get("model", "glm-4-flash")
        elif translator_type == "ollama":
            return self.config.get("fallback_translator", {}).get("model", "")
        elif translator_type == "siliconflow":
            return self.config.get("siliconflow_translator", {}).get("model", "deepseek-ai/DeepSeek-V3")
        elif translator_type == "intranet":
            return self.config.get("intranet_translator", {}).get("model", "deepseek-r1-70b")

        return ""

    def refresh_models(self, translator_type: str = None) -> list:
        """刷新并返回模型列表"""
        if translator_type is None:
            translator_type = self.current_translator_type

        if translator_type == "ollama":
            # 刷新Ollama模型列表
            available_models = setup_ollama()
            if available_models:
                self.config['fallback_translator']['available_models'] = available_models
                # 重新初始化Ollama翻译器
                self.translators["ollama"] = self._init_ollama_translator()
                return available_models
        elif translator_type == "zhipuai":
            # 对于智谱AI，重新检查连接并返回模型列表
            if self._check_zhipuai_available():
                return self.translators["zhipuai"].get_available_models()
        elif translator_type == "siliconflow":
            # 对于硅基流动，检查连接并返回模型列表
            if self.check_siliconflow_service():
                return self.translators["siliconflow"].get_available_models()
        elif translator_type == "intranet":
            # 对于内网翻译器，检查连接并返回模型列表
            if self.check_intranet_service():
                return self.translators["intranet"].get_available_models()

        return []

    def translate_text(self, text: str, terminology_dict: Optional[Dict] = None, source_lang: str = "zh", target_lang: str = "en", prompt: str = None) -> str:
        """
        翻译单个文本片段

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

        translator = self.translators.get(self.current_translator_type)
        if not translator:
            logger.error(f"未找到{self.current_translator_type}翻译器")
            # 尝试切换到备用翻译器
            fallback_type = "ollama" if self.current_translator_type != "ollama" else "zhipuai"
            fallback_translator = self.translators.get(fallback_type)
            if fallback_translator:
                logger.warning(f"尝试使用{fallback_type}作为备用翻译器")
                try:
                    # 检查翻译器类型并使用正确的参数调用
                    if fallback_type == "ollama" and isinstance(fallback_translator, OllamaTranslator):
                        # OllamaTranslator.translate 方法的参数与其他翻译器不同
                        return fallback_translator.translate(text, terminology_dict)
                    elif isinstance(fallback_translator, (ZhipuAITranslator, SiliconFlowTranslator)):
                        return fallback_translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
                    else:
                        # 对于其他可能的翻译器，如果它们有统一的接口
                        return fallback_translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
                except Exception as e:
                    logger.error(f"{fallback_type}翻译失败: {str(e)}")
                    raise
            raise Exception(f"未找到可用的翻译器")

        try:
            # 确保将 terminology_dict 传递给实际的翻译器
            if isinstance(translator, (ZhipuAITranslator, SiliconFlowTranslator, IntranetTranslator)):
                return translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
            elif isinstance(translator, OllamaTranslator):
                 # OllamaTranslator.translate 方法的参数与其他翻译器不同
                return translator.translate(text, terminology_dict)
            else:
                # 对于其他可能的翻译器，如果它们有统一的接口
                return translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
        except Exception as e:
            logger.error(f"{self.current_translator_type}翻译失败: {str(e)}")
            # 尝试切换到备用翻译器
            fallback_type = "ollama" if self.current_translator_type != "ollama" else "zhipuai"
            fallback_translator = self.translators.get(fallback_type)
            if fallback_translator:
                logger.warning(f"尝试使用{fallback_type}作为备用翻译器")
                try:
                    # 检查翻译器类型并使用正确的参数调用
                    if fallback_type == "ollama" and isinstance(fallback_translator, OllamaTranslator):
                        # OllamaTranslator.translate 方法的参数与其他翻译器不同
                        return fallback_translator.translate(text, terminology_dict)
                    elif isinstance(fallback_translator, (ZhipuAITranslator, SiliconFlowTranslator, IntranetTranslator)):
                        return fallback_translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
                    else:
                        # 对于其他可能的翻译器，如果它们有统一的接口
                        return fallback_translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
                except Exception as fallback_e:
                    logger.error(f"{fallback_type}翻译失败: {str(fallback_e)}")
                    raise Exception(f"{self.current_translator_type}翻译失败: {str(e)}; {fallback_type}翻译失败: {str(fallback_e)}")
            raise

    def check_ollama_service(self) -> bool:
        """检查Ollama服务是否可用"""
        try:
            if isinstance(self.translators["ollama"], OllamaTranslator):
                models = self.translators["ollama"].get_available_models()
                return len(models) > 0
            return False
        except Exception as e:
            logger.error(f"检查Ollama服务状态失败: {str(e)}")
            return False

    def _check_ollama_available(self) -> bool:
        """检查Ollama服务是否可用（兼容PC端UI）"""
        return self.check_ollama_service()

    def check_siliconflow_service(self):
        """检查硅基流动服务是否可用"""
        try:
            if "siliconflow" in self.translators and isinstance(self.translators["siliconflow"], SiliconFlowTranslator):
                # 检查API key是否存在
                if not self.translators["siliconflow"].api_key:
                    logger.warning("硅基流动API key未配置")
                    return False

                # 进行简单的连接测试
                try:
                    test_response = self.translators["siliconflow"].client.chat.completions.create(
                        model=self.translators["siliconflow"].model,
                        messages=[{"role": "user", "content": "测试"}],
                        max_tokens=5,
                        timeout=15  # 增加超时时间到15秒
                    )
                    logger.info("硅基流动连接测试成功")
                    return True
                except Exception as test_e:
                    logger.warning(f"硅基流动连接测试失败: {str(test_e)}")
                    # 如果是超时或连接错误，仍然认为API key有效，只是网络问题
                    if "timeout" in str(test_e).lower() or "connection" in str(test_e).lower():
                        logger.info("硅基流动API key有效，但网络连接存在问题")
                        return True  # 认为服务可用，只是网络问题
                    return False
            return False
        except Exception as e:
            logger.error(f"检查硅基流动服务状态失败: {str(e)}")
            return False

    def check_intranet_service(self):
        """检查内网服务是否可用"""
        try:
            if "intranet" in self.translators and isinstance(self.translators["intranet"], IntranetTranslator):
                # 使用连接测试方法
                return self.translators["intranet"].test_connection()
            return False
        except Exception as e:
            logger.error(f"检查内网服务状态失败: {str(e)}")
            return False

    def translate_document(self, file_path, target_language, model_name=None):
        """
        翻译整个文档（此方法保留但未实现，实际翻译由DocumentProcessor处理）

        Args:
            file_path: 文件路径
            target_language: 目标语言
            model_name: 模型名称（可选）

        Returns:
            str: 输出文件路径
        """
        logger.warning("translate_document方法已弃用，请使用DocumentProcessor")

        # 翻译完成后
        if hasattr(self, 'translation_pairs') and self.translation_pairs:
            self.export_translation_to_excel(file_path, target_language)

        return None

    def export_translation_to_excel(self, file_path, target_language):
        """将翻译结果导出为Excel文件"""
        try:
            # 确保有翻译结果
            if not hasattr(self, 'translation_pairs') or not self.translation_pairs:
                return None

            # 创建DataFrame
            df = pd.DataFrame({
                '原文': [pair[0] for pair in self.translation_pairs],
                f'{target_language}翻译': [pair[1] for pair in self.translation_pairs]
            })

            # 生成保存路径
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            output_dir = os.path.join(os.path.dirname(file_path), "输出")

            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)

            # 构建Excel文件路径
            excel_path = os.path.join(output_dir, f"{base_name}_翻译对照表_{timestamp}.xlsx")

            # 保存到Excel
            df.to_excel(excel_path, index=False, engine='openpyxl')

            print(f"翻译对照表已保存至: {excel_path}")
            return excel_path
        except Exception as e:
            print(f"导出Excel文件时出错: {e}")
            return None

    def _init_ollama_translator(self):
        """初始化Ollama翻译器"""
        try:
            # 从单独的配置文件读取API URL
            api_config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "API_config")
            ollama_config_path = os.path.join(api_config_dir, "ollama_api.json")
            api_url = "http://localhost:11434"  # 默认值

            if os.path.exists(ollama_config_path):
                try:
                    with open(ollama_config_path, "r", encoding="utf-8") as f:
                        ollama_config = json.load(f)
                        api_url = ollama_config.get("api_url", api_url)
                except Exception as e:
                    logger.error(f"读取Ollama API配置失败: {str(e)}")

            if api_url:
                ollama_config = self.config.get("fallback_translator", {})
                model = ollama_config.get("model", "")
                model_list_timeout = ollama_config.get("model_list_timeout", 10)
                translate_timeout = ollama_config.get("translate_timeout", 60)

                return OllamaTranslator(
                    model=model,
                    api_url=api_url,
                    model_list_timeout=model_list_timeout,
                    translate_timeout=translate_timeout
                )
        except Exception as e:
            logger.error(f"初始化Ollama翻译器失败: {str(e)}")
        return None

    def _init_siliconflow_translator(self):
        """初始化硅基流动翻译器"""
        try:
            # 从单独的配置文件读取API key
            api_config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "API_config")
            siliconflow_config_path = os.path.join(api_config_dir, "siliconflow_api.json")
            api_key = ""

            if os.path.exists(siliconflow_config_path):
                try:
                    with open(siliconflow_config_path, "r", encoding="utf-8") as f:
                        siliconflow_config = json.load(f)
                        api_key = siliconflow_config.get("api_key", "")
                except Exception as e:
                    logger.error(f"读取硅基流动API配置失败: {str(e)}")

            if api_key:
                siliconflow_config = self.config.get("siliconflow_translator", {})
                model = siliconflow_config.get("model", "deepseek-ai/DeepSeek-V3")
                timeout = siliconflow_config.get("timeout", 60)

                return SiliconFlowTranslator(
                    api_key=api_key,
                    model=model,
                    timeout=timeout
                )
        except Exception as e:
            logger.error(f"初始化硅基流动翻译器失败: {str(e)}")
        return None

    def _init_zhipuai_translator(self):
        """初始化智谱AI翻译器"""
        try:
            # 从单独的配置文件读取API key
            api_config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "API_config")
            zhipu_config_path = os.path.join(api_config_dir, "zhipu_api.json")
            api_key = ""

            if os.path.exists(zhipu_config_path):
                try:
                    with open(zhipu_config_path, "r", encoding="utf-8") as f:
                        zhipu_config = json.load(f)
                        api_key = zhipu_config.get("api_key", "")
                except Exception as e:
                    logger.error(f"读取智谱API配置失败: {str(e)}")

            if api_key:
                zhipuai_config = self.config.get("zhipuai_translator", {})
                model = zhipuai_config.get("model", "glm-4-flash")
                temperature = zhipuai_config.get("temperature", 0.2)

                return ZhipuAITranslator(
                    api_key=api_key,
                    model=model,
                    temperature=temperature
                )
        except Exception as e:
            logger.error(f"初始化智谱AI翻译器失败: {str(e)}")
        return None

    def _init_intranet_translator(self):
        """初始化内网翻译器"""
        try:
            intranet_config = self.config.get("intranet_translator", {})
            api_url = intranet_config.get("api_url", "")
            model = intranet_config.get("model", "deepseek-r1-70b")
            timeout = intranet_config.get("timeout", 60)

            if api_url:
                return IntranetTranslator(
                    api_url=api_url,
                    model=model,
                    timeout=timeout
                )
        except Exception as e:
            logger.error(f"初始化内网翻译器失败: {str(e)}")
        return None

    def _detect_intranet_environment(self) -> bool:
        """检测是否为内网环境"""
        try:
            import os
            import socket

            # 1. 检查配置文件设置
            env_config = self.config.get('environment', {})
            if env_config.get('intranet_mode', False):
                logger.info("配置文件中启用了内网模式")
                return True

            if env_config.get('offline_mode', False):
                logger.info("配置文件中启用了离线模式")
                return True

            if env_config.get('skip_network_checks', False):
                logger.info("配置文件中设置跳过网络检查")
                return True

            # 2. 检查环境变量
            if os.getenv('OFFLINE_MODE', '').lower() in ['true', '1', 'yes']:
                logger.info("检测到离线模式环境变量")
                return True

            if os.getenv('INTRANET_MODE', '').lower() in ['true', '1', 'yes']:
                logger.info("检测到内网模式环境变量")
                return True

            # 3. 尝试连接外网进行检测（快速检测）
            try:
                # 尝试连接DNS服务器（快速）
                socket.create_connection(("8.8.8.8", 53), timeout=2)
                logger.info("检测到外网连接，非内网环境")
                return False
            except (socket.timeout, socket.error):
                try:
                    # 再尝试连接国内常用网站
                    socket.create_connection(("www.baidu.com", 80), timeout=2)
                    logger.info("检测到外网连接，非内网环境")
                    return False
                except (socket.timeout, socket.error):
                    logger.warning("无法连接外网，判断为内网环境")
                    return True

        except Exception as e:
            logger.error(f"检测内网环境失败: {str(e)}")
            # 出错时默认认为是内网环境，避免不必要的网络请求
            return True

    def _check_zhipuai_available(self, skip_network_check=False) -> bool:
        """检查智谱AI服务是否可用"""
        try:
            if "zhipuai" in self.translators and isinstance(self.translators["zhipuai"], ZhipuAITranslator):
                # 直接调用ZhipuAITranslator中的_check_zhipuai_available方法
                return self.translators["zhipuai"]._check_zhipuai_available(skip_network_check=skip_network_check)
            logger.warning("智谱AI翻译器未初始化或类型不正确")
            return False
        except KeyError:
            logger.error("智谱AI翻译器未在translators字典中")
            return False
        except Exception as e:
            logger.error(f"检查智谱AI服务状态失败: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def _init_primary_translator(self):
        """初始化主要翻译器"""
        try:
            primary_config = self.config['primary_translator']
            if primary_config['type'] == 'zhipuai':
                # 使用ZhipuAITranslator作为主要翻译器
                api_key = primary_config.get('api_key', '')
                model = primary_config.get('model', 'glm-4-flash')
                temperature = primary_config.get('temperature', 0.3)

                return ZhipuAITranslator(
                    api_key=api_key,
                    model=model,
                    temperature=temperature
                )
            else:
                logger.warning(f"不支持的主要翻译器类型: {primary_config['type']}")
                return None
        except Exception as e:
            logger.error(f"初始化主要翻译器失败: {str(e)}")
            return None