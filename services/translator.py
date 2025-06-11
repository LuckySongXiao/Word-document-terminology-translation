import requests
import json
import logging
import os
import sys
from pathlib import Path
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

def verify_api_config_files() -> bool:
    """
    验证API配置文件是否存在

    Returns:
        bool: 如果所有必需的配置文件都存在则返回True
    """
    try:
        logger.info("开始验证API配置文件...")
        api_config_dir = find_resource_path("API_config")
        logger.info(f"API配置目录: {api_config_dir}")

        if not os.path.exists(api_config_dir):
            logger.error(f"API配置目录不存在: {api_config_dir}")
            return False

        required_files = [
            "zhipu_api.json",
            "ollama_api.json",
            "siliconflow_api.json"
        ]

        logger.info(f"需要验证的配置文件: {required_files}")

        missing_files = []
        existing_files = []
        for file_name in required_files:
            file_path = os.path.join(api_config_dir, file_name)
            if not os.path.exists(file_path):
                missing_files.append(file_path)
                logger.warning(f"❌ 配置文件缺失: {file_path}")
            else:
                existing_files.append(file_path)
                logger.info(f"✓ 配置文件存在: {file_path}")
                # 检查文件内容
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        logger.debug(f"配置文件内容: {file_name} -> {list(content.keys())}")
                except Exception as e:
                    logger.warning(f"读取配置文件失败 {file_name}: {e}")

        if missing_files:
            logger.error(f"缺失的配置文件: {missing_files}")
            logger.info(f"存在的配置文件: {existing_files}")
            return False

        logger.info("✓ 所有API配置文件验证通过")
        return True
    except Exception as e:
        logger.error(f"验证API配置文件时出错: {e}")
        logger.error(traceback.format_exc())
        return False

def find_resource_path(resource_name: str, max_retries: int = 5) -> str:
    """
    查找资源文件路径，适用于源码和封装环境
    增加重试机制以应对文件解压时序问题

    Args:
        resource_name: 资源名称，如 'config.json', 'API_config'
        max_retries: 最大重试次数

    Returns:
        str: 资源文件的完整路径
    """
    import time

    logger.debug(f"查找资源: {resource_name}")
    logger.debug(f"运行环境: {'封装' if getattr(sys, 'frozen', False) else '源码'}")

    for retry in range(max_retries):
        possible_paths = []

        if getattr(sys, 'frozen', False):
            # 封装环境 - 增加更多候选路径
            if hasattr(sys, '_MEIPASS'):
                # PyInstaller单文件模式
                meipass_dir = Path(sys._MEIPASS)
                possible_paths.extend([
                    meipass_dir / resource_name,
                    meipass_dir / "_internal" / resource_name,
                    meipass_dir / "data" / resource_name,
                ])
                logger.debug(f"_MEIPASS目录: {sys._MEIPASS}")

            # 可执行文件目录
            exe_dir = Path(sys.executable).parent
            possible_paths.extend([
                exe_dir / resource_name,
                exe_dir / "_internal" / resource_name,
                exe_dir / "data" / resource_name,
            ])
            logger.debug(f"可执行文件目录: {exe_dir}")
        else:
            # 源码环境
            current_dir = Path(__file__).parent.parent
            possible_paths.extend([
                current_dir / resource_name,
                current_dir / ".." / resource_name,
            ])
            logger.debug(f"源码目录: {current_dir}")

        logger.debug(f"候选路径 (重试 {retry + 1}/{max_retries}): {[str(p) for p in possible_paths]}")

        # 查找存在的路径
        for path in possible_paths:
            logger.debug(f"检查路径: {path} -> 存在: {path.exists()}")
            if path.exists():
                if retry > 0:
                    logger.info(f"找到资源 {resource_name}: {path} (重试次数: {retry})")
                else:
                    logger.debug(f"找到资源 {resource_name}: {path}")
                return str(path)

        # 如果没找到且还有重试次数，等待一下再试
        if retry < max_retries - 1:
            logger.warning(f"资源 {resource_name} 未找到，等待500ms后重试 ({retry + 1}/{max_retries})")
            time.sleep(0.5)

    # 所有重试都失败，返回默认路径
    default_path = Path(__file__).parent.parent / resource_name
    logger.error(f"经过 {max_retries} 次重试仍未找到资源 {resource_name}，使用默认路径: {default_path}")
    logger.error(f"最后尝试的路径: {[str(p) for p in possible_paths]}")
    return str(default_path)

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

        # 添加错误计数器，用于跟踪API连接失败次数
        self.api_error_counts = {
            'zhipuai': 0,
            'siliconflow': 0,
            'intranet': 0
        }
        self.max_api_errors = 2  # 最大允许的API错误次数

        # 添加连接状态缓存
        self.connection_status = {
            'zhipuai': None,  # None表示未测试，True表示可用，False表示不可用
            'siliconflow': None,
            'intranet': None,
            'ollama': None
        }

        # 在封装环境中，先验证配置文件是否存在
        if getattr(sys, 'frozen', False):
            logger.info("检测到封装环境，验证API配置文件...")
            logger.info(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'Not found')}")
            logger.info(f"sys.executable: {sys.executable}")
            if not verify_api_config_files():
                logger.error("部分API配置文件缺失，翻译器初始化将受影响")
            else:
                logger.info("API配置文件验证通过")
        else:
            logger.info("检测到源码环境，直接进行翻译器初始化")

        # 初始化所有翻译器（不进行连接测试）
        initialized_count = 0
        try:
            # 初始化智谱AI翻译器
            try:
                zhipuai_translator = self._init_zhipuai_translator()
                if zhipuai_translator:
                    self.translators['zhipuai'] = zhipuai_translator
                    initialized_count += 1
                    logger.info("智谱AI翻译器初始化成功")
                else:
                    logger.warning("智谱AI翻译器初始化失败：API密钥未配置或配置错误")
            except Exception as e:
                logger.error(f"智谱AI翻译器初始化异常: {str(e)}")

            # 初始化Ollama翻译器
            try:
                ollama_translator = self._init_ollama_translator()
                if ollama_translator:
                    self.translators['ollama'] = ollama_translator
                    initialized_count += 1
                    logger.info("Ollama翻译器初始化成功")
                else:
                    logger.warning("Ollama翻译器初始化失败：配置错误")
            except Exception as e:
                logger.error(f"Ollama翻译器初始化异常: {str(e)}")

            # 初始化硅基流动翻译器
            try:
                siliconflow_translator = self._init_siliconflow_translator()
                if siliconflow_translator:
                    self.translators['siliconflow'] = siliconflow_translator
                    initialized_count += 1
                    logger.info("硅基流动翻译器初始化成功")
                else:
                    logger.warning("硅基流动翻译器初始化失败：API密钥未配置或配置错误")
            except Exception as e:
                logger.error(f"硅基流动翻译器初始化异常: {str(e)}")

            # 初始化内网翻译器
            try:
                intranet_translator = self._init_intranet_translator()
                if intranet_translator:
                    self.translators['intranet'] = intranet_translator
                    initialized_count += 1
                    logger.info("内网翻译器初始化成功")
                else:
                    logger.warning("内网翻译器初始化失败：API URL未配置或配置错误")
            except Exception as e:
                logger.error(f"内网翻译器初始化异常: {str(e)}")

        except Exception as e:
            logger.error(f"翻译器初始化过程中发生严重错误: {str(e)}")
            logger.error(traceback.format_exc())

        logger.info(f"翻译器初始化完成，成功初始化 {initialized_count} 个翻译器")

        if initialized_count == 0:
            logger.error("没有任何翻译器初始化成功，请检查配置文件和API密钥")
            raise Exception("翻译服务初始化失败：没有可用的翻译器")

        # 设置Ollama环境
        available_models = setup_ollama()
        if available_models:
            self.config['fallback_translator']['available_models'] = available_models
            if self.config['fallback_translator']['model'] not in available_models:
                self.config['fallback_translator']['model'] = available_models[0]

        logger.info("翻译服务初始化完成，连接测试将在用户选择平台时进行")

    def load_config(self):
        """加载配置"""
        config_path = find_resource_path('config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        # 不在这里初始化主要翻译器，而是在后面的初始化过程中统一处理
        # 这样可以确保使用正确的API配置文件
        logger.info("配置文件加载完成，翻译器将在后续步骤中初始化")

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

    def test_translator_connection(self, translator_type: str) -> bool:
        """
        测试指定翻译器的连接状态

        Args:
            translator_type: 翻译器类型 ('zhipuai', 'siliconflow', 'intranet', 'ollama')

        Returns:
            bool: 连接是否成功
        """
        # 如果已经测试过且状态为可用，直接返回
        if self.connection_status.get(translator_type) is True:
            logger.info(f"{translator_type}连接状态已缓存为可用")
            return True

        logger.info(f"正在测试{translator_type}连接...")

        try:
            if translator_type == 'zhipuai':
                if 'zhipuai' in self.translators:
                    result = self._check_zhipuai_available()
                    self.connection_status['zhipuai'] = result
                    if result:
                        logger.info("智谱AI连接测试成功")
                        self.api_error_counts['zhipuai'] = 0  # 重置错误计数
                    else:
                        logger.warning("智谱AI连接测试失败")
                    return result

            elif translator_type == 'siliconflow':
                if 'siliconflow' in self.translators:
                    result = self.check_siliconflow_service()
                    self.connection_status['siliconflow'] = result
                    if result:
                        logger.info("硅基流动连接测试成功")
                        self.api_error_counts['siliconflow'] = 0  # 重置错误计数
                    else:
                        logger.warning("硅基流动连接测试失败")
                    return result

            elif translator_type == 'intranet':
                if 'intranet' in self.translators:
                    result = self.check_intranet_service()
                    self.connection_status['intranet'] = result
                    if result:
                        logger.info("内网翻译器连接测试成功")
                        self.api_error_counts['intranet'] = 0  # 重置错误计数
                    else:
                        logger.warning("内网翻译器连接测试失败")
                    return result

            elif translator_type == 'ollama':
                if 'ollama' in self.translators:
                    result = self.check_ollama_service()
                    self.connection_status['ollama'] = result
                    if result:
                        logger.info("Ollama连接测试成功")
                    else:
                        logger.warning("Ollama连接测试失败")
                    return result

        except Exception as e:
            logger.error(f"测试{translator_type}连接时发生异常: {str(e)}")
            self.connection_status[translator_type] = False

        return False

    def handle_translation_error(self, translator_type: str, error: Exception):
        """
        处理翻译错误，实现错误计数和自动切换逻辑

        Args:
            translator_type: 发生错误的翻译器类型
            error: 错误对象
        """
        if translator_type in self.api_error_counts:
            self.api_error_counts[translator_type] += 1
            logger.warning(f"{translator_type}翻译错误计数: {self.api_error_counts[translator_type]}/{self.max_api_errors}")

            # 如果错误次数达到阈值，切换到Ollama
            if self.api_error_counts[translator_type] >= self.max_api_errors:
                logger.error(f"{translator_type}连续失败{self.max_api_errors}次，自动切换到Ollama模式")
                self.connection_status[translator_type] = False

                # 如果Ollama可用，切换到Ollama
                if self.test_translator_connection('ollama'):
                    self.current_translator_type = 'ollama'
                    logger.info("已成功切换到Ollama翻译器")
                    return True
                else:
                    logger.error("Ollama翻译器也不可用，无法自动切换")
                    return False

        return False

    def set_translator_type(self, translator_type: str):
        """设置当前使用的翻译器类型"""
        if translator_type in ["zhipuai", "ollama", "siliconflow", "intranet"]:
            self.current_translator_type = translator_type
            # 更新配置文件
            self.config["current_translator_type"] = translator_type
            config_path = find_resource_path('config.json')
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
        config_path = find_resource_path('config.json')
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
                        # OllamaTranslator.translate 方法现在支持完整参数
                        return fallback_translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
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
            # 在翻译前先测试连接（如果尚未测试过）
            if self.connection_status.get(self.current_translator_type) is None:
                if not self.test_translator_connection(self.current_translator_type):
                    raise Exception(f"{self.current_translator_type}连接测试失败")

            # 确保将 terminology_dict 传递给实际的翻译器
            if isinstance(translator, (ZhipuAITranslator, SiliconFlowTranslator, IntranetTranslator)):
                return translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
            elif isinstance(translator, OllamaTranslator):
                 # OllamaTranslator.translate 方法现在支持完整参数
                return translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
            else:
                # 对于其他可能的翻译器，如果它们有统一的接口
                return translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
        except Exception as e:
            logger.error(f"{self.current_translator_type}翻译失败: {str(e)}")

            # 处理翻译错误，可能触发自动切换
            if self.handle_translation_error(self.current_translator_type, e):
                # 如果成功切换到Ollama，重新尝试翻译
                logger.info("已切换翻译器，重新尝试翻译...")
                new_translator = self.translators.get(self.current_translator_type)
                if new_translator and isinstance(new_translator, OllamaTranslator):
                    try:
                        return new_translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
                    except Exception as retry_e:
                        logger.error(f"切换后的翻译器也失败: {str(retry_e)}")
                        raise Exception(f"原翻译器失败: {str(e)}; 切换后翻译器失败: {str(retry_e)}")

            # 如果没有自动切换或切换失败，尝试手动备用翻译器
            fallback_type = "ollama" if self.current_translator_type != "ollama" else "zhipuai"
            fallback_translator = self.translators.get(fallback_type)
            if fallback_translator:
                logger.warning(f"尝试使用{fallback_type}作为备用翻译器")
                try:
                    # 检查翻译器类型并使用正确的参数调用
                    if fallback_type == "ollama" and isinstance(fallback_translator, OllamaTranslator):
                        # OllamaTranslator.translate 方法现在支持完整参数
                        return fallback_translator.translate(text, terminology_dict, source_lang, target_lang, prompt)
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
                # 获取可用模型列表
                models = self.translators["ollama"].get_available_models()
                if len(models) == 0:
                    logger.warning("Ollama服务运行中，但没有可用的模型")
                    return False

                # 检查配置的模型是否存在
                configured_model = self.translators["ollama"].model
                if configured_model not in models:
                    logger.warning(f"配置的Ollama模型 '{configured_model}' 不存在")
                    logger.info(f"可用的Ollama模型: {models}")

                    # 尝试使用第一个可用的模型
                    if models:
                        # 过滤掉无效的模型名
                        valid_models = [m for m in models if m not in ['failed', 'NAME'] and ':' in m]
                        if valid_models:
                            new_model = valid_models[0]
                            logger.info(f"自动切换到可用模型: {new_model}")
                            self.translators["ollama"].model = new_model
                            # 更新配置
                            self.config['fallback_translator']['model'] = new_model
                            return True
                    return False

                logger.info(f"Ollama模型 '{configured_model}' 验证成功")
                return True
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
            api_config_dir = find_resource_path("API_config")
            ollama_config_path = os.path.join(api_config_dir, "ollama_api.json")
            api_url = "http://localhost:11434"  # 默认值

            logger.debug(f"查找Ollama配置文件: {ollama_config_path}")
            if os.path.exists(ollama_config_path):
                try:
                    with open(ollama_config_path, "r", encoding="utf-8") as f:
                        ollama_config = json.load(f)
                        api_url = ollama_config.get("api_url", api_url)
                        logger.info(f"成功读取Ollama配置，API URL: {api_url}")
                except Exception as e:
                    logger.error(f"读取Ollama API配置失败: {str(e)}")
            else:
                logger.info(f"Ollama配置文件不存在，使用默认URL: {api_url}")

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
            logger.error(traceback.format_exc())
        return None

    def _init_siliconflow_translator(self):
        """初始化硅基流动翻译器"""
        try:
            # 从单独的配置文件读取API key
            api_config_dir = find_resource_path("API_config")
            siliconflow_config_path = os.path.join(api_config_dir, "siliconflow_api.json")
            api_key = ""

            logger.debug(f"查找硅基流动配置文件: {siliconflow_config_path}")
            if os.path.exists(siliconflow_config_path):
                try:
                    with open(siliconflow_config_path, "r", encoding="utf-8") as f:
                        siliconflow_config = json.load(f)
                        api_key = siliconflow_config.get("api_key", "")
                        logger.info(f"成功读取硅基流动配置，API Key前缀: {api_key[:8]}..." if api_key else "API Key为空")
                except Exception as e:
                    logger.error(f"读取硅基流动API配置失败: {str(e)}")
            else:
                logger.warning(f"硅基流动配置文件不存在: {siliconflow_config_path}")

            if api_key:
                siliconflow_config = self.config.get("siliconflow_translator", {})
                model = siliconflow_config.get("model", "deepseek-ai/DeepSeek-V3")
                timeout = siliconflow_config.get("timeout", 60)

                return SiliconFlowTranslator(
                    api_key=api_key,
                    model=model,
                    timeout=timeout
                )
            else:
                logger.warning("硅基流动API密钥未配置")
        except Exception as e:
            logger.error(f"初始化硅基流动翻译器失败: {str(e)}")
            logger.error(traceback.format_exc())
        return None

    def _init_zhipuai_translator(self):
        """初始化智谱AI翻译器"""
        try:
            # 从单独的配置文件读取API key
            api_config_dir = find_resource_path("API_config")
            zhipu_config_path = os.path.join(api_config_dir, "zhipu_api.json")
            api_key = ""

            logger.debug(f"查找智谱AI配置文件: {zhipu_config_path}")
            if os.path.exists(zhipu_config_path):
                try:
                    with open(zhipu_config_path, "r", encoding="utf-8") as f:
                        zhipu_config = json.load(f)
                        api_key = zhipu_config.get("api_key", "")
                        logger.info(f"成功读取智谱AI配置，API Key前缀: {api_key[:8]}..." if api_key else "API Key为空")
                except Exception as e:
                    logger.error(f"读取智谱API配置失败: {str(e)}")
            else:
                logger.warning(f"智谱AI配置文件不存在: {zhipu_config_path}")

            if api_key:
                zhipuai_config = self.config.get("zhipuai_translator", {})
                model = zhipuai_config.get("model", "glm-4-flash")
                temperature = zhipuai_config.get("temperature", 0.2)

                return ZhipuAITranslator(
                    api_key=api_key,
                    model=model,
                    temperature=temperature
                )
            else:
                logger.warning("智谱AI API密钥未配置")
        except Exception as e:
            logger.error(f"初始化智谱AI翻译器失败: {str(e)}")
            logger.error(traceback.format_exc())
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
                # 使用ZhipuAITranslator作为主要翻译器，从API配置文件读取密钥
                api_config_dir = find_resource_path("API_config")
                zhipu_config_path = os.path.join(api_config_dir, "zhipu_api.json")
                api_key = ""

                if os.path.exists(zhipu_config_path):
                    try:
                        with open(zhipu_config_path, "r", encoding="utf-8") as f:
                            zhipu_config = json.load(f)
                            api_key = zhipu_config.get("api_key", "")
                    except Exception as e:
                        logger.error(f"读取智谱API配置失败: {str(e)}")

                if not api_key:
                    logger.warning("智谱AI API密钥未配置，跳过主要翻译器初始化")
                    return None

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