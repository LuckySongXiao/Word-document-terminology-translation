using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;
using DocumentTranslator.Services.Translation.Translators;

namespace DocumentTranslator.Services.Translation
{
    /// <summary>
    /// 翻译服务管理类，负责管理各种翻译器和翻译配置
    /// </summary>
    public class TranslationService
    {
        private readonly ILogger<TranslationService> _logger;
        private readonly Dictionary<string, ITranslator> _translators;
        private readonly Dictionary<string, object> _config;
        private string _currentTranslatorType;
        private volatile bool _stopFlag;
        private readonly List<string> _currentOperations;

        public TranslationService(ILogger<TranslationService> logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _translators = new Dictionary<string, ITranslator>();
            _config = new Dictionary<string, object>();
            _currentOperations = new List<string>();
            _currentTranslatorType = "siliconflow"; // 默认翻译器
            
            LoadConfiguration();
            InitializeTranslators();
        }

        /// <summary>
        /// 当前翻译器类型
        /// </summary>
        public string CurrentTranslatorType
        {
            get => _currentTranslatorType;
            set
            {
                if (_translators.ContainsKey(value))
                {
                    _currentTranslatorType = value;
                    _logger.LogInformation($"切换到翻译器: {value}");
                }
                else
                {
                    _logger.LogWarning($"翻译器类型 {value} 不存在");
                }
            }
        }

        /// <summary>
        /// 获取当前翻译器
        /// </summary>
        public ITranslator CurrentTranslator => _translators.TryGetValue(_currentTranslatorType, out var translator) ? translator : null;

        /// <summary>
        /// 获取所有可用的翻译器类型
        /// </summary>
        public IEnumerable<string> AvailableTranslatorTypes => _translators.Keys;

        /// <summary>
        /// 重新初始化指定的翻译器
        /// </summary>
        public void ReinitializeTranslator(string translatorType)
        {
            try
            {
                _logger.LogInformation($"重新初始化{translatorType}翻译器");

                // 移除现有的翻译器
                if (_translators.ContainsKey(translatorType))
                {
                    _translators.Remove(translatorType);
                }

                // 重新初始化翻译器
                ITranslator translator = translatorType switch
                {
                    "zhipuai" => InitializeZhipuAITranslator(),
                    "ollama" => InitializeOllamaTranslator(),
                    "siliconflow" => InitializeSiliconFlowTranslator(),
                    "intranet" => InitializeIntranetTranslator(),
                    _ => null
                };

                if (translator != null)
                {
                    _translators[translatorType] = translator;
                    _logger.LogInformation($"{translatorType}翻译器重新初始化成功");
                }
                else
                {
                    _logger.LogWarning($"{translatorType}翻译器重新初始化失败");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"重新初始化{translatorType}翻译器失败");
            }
        }

        /// <summary>
        /// 加载配置文件
        /// </summary>
        private void LoadConfiguration()
        {
            try
            {
                var configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config.json");
                if (File.Exists(configPath))
                {
                    var configJson = File.ReadAllText(configPath);
                    var config = JsonConvert.DeserializeObject<Dictionary<string, object>>(configJson);
                    if (config != null)
                    {
                        foreach (var kvp in config)
                        {
                            _config[kvp.Key] = kvp.Value;
                        }
                    }
                }
                _logger.LogInformation("配置文件加载完成");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "加载配置文件失败");
            }
        }

        /// <summary>
        /// 初始化所有翻译器
        /// </summary>
        private void InitializeTranslators()
        {
            try
            {
                // 初始化SiliconFlow翻译器
                var siliconFlowTranslator = InitializeSiliconFlowTranslator();
                if (siliconFlowTranslator != null)
                {
                    _translators["siliconflow"] = siliconFlowTranslator;
                }

                // 初始化ZhipuAI翻译器
                var zhipuAITranslator = InitializeZhipuAITranslator();
                if (zhipuAITranslator != null)
                {
                    _translators["zhipuai"] = zhipuAITranslator;
                }

                // 初始化Ollama翻译器
                var ollamaTranslator = InitializeOllamaTranslator();
                if (ollamaTranslator != null)
                {
                    _translators["ollama"] = ollamaTranslator;
                }

                // 初始化内网翻译器
                var intranetTranslator = InitializeIntranetTranslator();
                if (intranetTranslator != null)
                {
                    _translators["intranet"] = intranetTranslator;
                }

                _logger.LogInformation($"已初始化 {_translators.Count} 个翻译器");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "初始化翻译器失败");
            }
        }

        /// <summary>
        /// 初始化SiliconFlow翻译器
        /// </summary>
        private ITranslator InitializeSiliconFlowTranslator(string preferredModel = null)
        {
            try
            {
                var apiKey = GetApiKey("siliconflow");
                if (!string.IsNullOrEmpty(apiKey))
                {
                    var siliconFlowConfig = GetConfig("siliconflow_translator") as Dictionary<string, object> ?? new Dictionary<string, object>();
                    var model = preferredModel ?? siliconFlowConfig.GetValueOrDefault("model", "deepseek-ai/DeepSeek-V3").ToString();
                    var timeout = Convert.ToInt32(siliconFlowConfig.GetValueOrDefault("timeout", 60));

                    _logger.LogInformation($"初始化硅基流动翻译器，使用模型: {model}");
                    return new SiliconFlowTranslator(_logger, apiKey, model, timeout);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "初始化硅基流动翻译器失败");
            }
            return null;
        }

        /// <summary>
        /// 初始化ZhipuAI翻译器
        /// </summary>
        private ITranslator InitializeZhipuAITranslator(string preferredModel = null)
        {
            try
            {
                var apiKey = GetApiKey("zhipuai");
                if (!string.IsNullOrEmpty(apiKey))
                {
                    var zhipuAIConfig = GetConfig("zhipuai_translator") as Dictionary<string, object> ?? new Dictionary<string, object>();
                    var model = preferredModel ?? zhipuAIConfig.GetValueOrDefault("model", "glm-4-flash-250414").ToString();
                    var temperature = Convert.ToSingle(zhipuAIConfig.GetValueOrDefault("temperature", 0.2));
                    var timeout = Convert.ToInt32(zhipuAIConfig.GetValueOrDefault("timeout", 60));

                    _logger.LogInformation($"初始化智谱AI翻译器，使用模型: {model}");
                    return new ZhipuAITranslator(_logger, apiKey, model, temperature, timeout);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "初始化智谱AI翻译器失败");
            }
            return null;
        }

        /// <summary>
        /// 初始化Ollama翻译器
        /// </summary>
        private ITranslator InitializeOllamaTranslator(string preferredModel = null)
        {
            try
            {
                var ollamaConfig = GetConfig("ollama_translator") as Dictionary<string, object> ?? new Dictionary<string, object>();
                var model = preferredModel ?? ollamaConfig.GetValueOrDefault("model", "qwen2.5:7b").ToString();
                var apiUrl = ollamaConfig.GetValueOrDefault("api_url", "http://localhost:11434").ToString();
                var modelListTimeout = Convert.ToInt32(ollamaConfig.GetValueOrDefault("model_list_timeout", 10));
                var translateTimeout = Convert.ToInt32(ollamaConfig.GetValueOrDefault("translate_timeout", 60));

                _logger.LogInformation($"初始化Ollama翻译器，使用模型: {model}");
                return new OllamaTranslator(_logger, model, apiUrl, modelListTimeout, translateTimeout);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "初始化Ollama翻译器失败");
            }
            return null;
        }

        /// <summary>
        /// 初始化内网翻译器
        /// </summary>
        private ITranslator InitializeIntranetTranslator(string preferredModel = null)
        {
            try
            {
                var intranetConfig = GetConfig("intranet_translator") as Dictionary<string, object> ?? new Dictionary<string, object>();
                var apiUrl = intranetConfig.GetValueOrDefault("api_url", "").ToString();
                
                if (!string.IsNullOrEmpty(apiUrl))
                {
                    var model = preferredModel ?? intranetConfig.GetValueOrDefault("model", "deepseek-r1-70b").ToString();
                    var timeout = Convert.ToInt32(intranetConfig.GetValueOrDefault("timeout", 60));

                    _logger.LogInformation($"初始化内网翻译器，使用模型: {model}");
                    return new IntranetTranslator(_logger, apiUrl, model, timeout);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "初始化内网翻译器失败");
            }
            return null;
        }

        /// <summary>
        /// 获取API密钥
        /// </summary>
        private string GetApiKey(string service)
        {
            try
            {
                // 首先尝试从环境变量获取API密钥
                var envKeyName = service.ToUpper() switch
                {
                    "ZHIPUAI" => "ZHIPU_API_KEY",
                    "SILICONFLOW" => "SILICONFLOW_API_KEY",
                    "INTRANET" => "INTRANET_API_KEY",
                    _ => $"{service.ToUpper()}_API_KEY"
                };

                var envApiKey = Environment.GetEnvironmentVariable(envKeyName, EnvironmentVariableTarget.User);
                if (!string.IsNullOrEmpty(envApiKey))
                {
                    _logger.LogDebug($"从环境变量获取{service} API密钥");
                    return envApiKey;
                }

                // 如果环境变量中没有，则从配置文件获取
                var configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "API_config", $"{service}_api.json");
                if (File.Exists(configPath))
                {
                    var configJson = File.ReadAllText(configPath);
                    var config = JsonConvert.DeserializeObject<Dictionary<string, string>>(configJson);
                    var apiKey = config?.GetValueOrDefault("api_key", "");
                    if (!string.IsNullOrEmpty(apiKey))
                    {
                        _logger.LogDebug($"从配置文件获取{service} API密钥");
                        return apiKey;
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"获取{service} API密钥失败");
            }
            return string.Empty;
        }

        /// <summary>
        /// 获取配置项
        /// </summary>
        private object GetConfig(string key)
        {
            return _config.TryGetValue(key, out var value) ? value : null;
        }

        /// <summary>
        /// 翻译文本
        /// </summary>
        public async Task<string> TranslateTextAsync(string text, Dictionary<string, string> terminologyDict = null,
            string sourceLang = "zh", string targetLang = "en", string prompt = null)
        {
            if (string.IsNullOrWhiteSpace(text))
                return string.Empty;

            // 检查是否需要停止
            if (_stopFlag)
            {
                _logger.LogInformation("翻译操作被停止");
                return string.Empty;
            }

            var translator = CurrentTranslator;
            if (translator == null)
            {
                _logger.LogError($"未找到{_currentTranslatorType}翻译器");
                throw new InvalidOperationException($"未找到可用的翻译器");
            }

            try
            {
                return await translator.TranslateAsync(text, terminologyDict, sourceLang, targetLang, prompt);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"{_currentTranslatorType}翻译失败");
                throw;
            }
        }

        /// <summary>
        /// 获取可用模型列表
        /// </summary>
        public async Task<List<string>> GetAvailableModelsAsync(string translatorType = null)
        {
            var type = translatorType ?? _currentTranslatorType;
            if (_translators.TryGetValue(type, out var translator))
            {
                try
                {
                    return await translator.GetAvailableModelsAsync();
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, $"获取{type}模型列表失败");
                }
            }
            return new List<string>();
        }

        /// <summary>
        /// 停止当前操作
        /// </summary>
        public void StopCurrentOperations()
        {
            try
            {
                _stopFlag = true;
                _logger.LogInformation("设置停止标志，正在停止当前翻译操作...");

                // 清理当前操作列表
                lock (_currentOperations)
                {
                    _currentOperations.Clear();
                }

                // 重置停止标志
                Task.Run(async () =>
                {
                    await Task.Delay(1000); // 等待1秒后重置
                    _stopFlag = false;
                    _logger.LogInformation("停止标志已重置");
                });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "停止当前操作失败");
            }
        }
    }
}
