using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace DocumentTranslator.Services.Translation
{
    /// <summary>
    /// 配置管理器，负责加载和管理翻译相关的配置
    /// </summary>
    public class ConfigurationManager
    {
        private readonly ILogger<ConfigurationManager> _logger;
        private Dictionary<string, object> _config;
        private Dictionary<string, ApiConfiguration> _apiConfigurations;

        public ConfigurationManager(ILogger<ConfigurationManager> logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _config = new Dictionary<string, object>();
            _apiConfigurations = new Dictionary<string, ApiConfiguration>();
            
            LoadConfiguration();
            LoadApiConfigurations();
        }

        /// <summary>
        /// 加载主配置文件
        /// </summary>
        private void LoadConfiguration()
        {
            try
            {
                var configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config.json");
                if (File.Exists(configPath))
                {
                    var configJson = File.ReadAllText(configPath);
                    var config = JsonSerializer.Deserialize<Dictionary<string, object>>(configJson);
                    if (config != null)
                    {
                        _config = config;
                    }
                }
                _logger.LogInformation("主配置文件加载完成");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "加载主配置文件失败");
            }
        }

        /// <summary>
        /// 加载API配置文件
        /// </summary>
        private void LoadApiConfigurations()
        {
            try
            {
                var apiConfigDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "API_config");
                if (!Directory.Exists(apiConfigDir))
                {
                    _logger.LogWarning($"API配置目录不存在: {apiConfigDir}");
                    return;
                }

                // 加载各种API配置
                LoadApiConfiguration("siliconflow", "siliconflow_api.json");
                LoadApiConfiguration("zhipuai", "zhipu_api.json");
                LoadApiConfiguration("ollama", "ollama_api.json");
                LoadApiConfiguration("intranet", "intranet_api.json");

                _logger.LogInformation($"API配置加载完成，共加载 {_apiConfigurations.Count} 个配置");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "加载API配置失败");
            }
        }

        /// <summary>
        /// 加载单个API配置
        /// </summary>
        private void LoadApiConfiguration(string serviceName, string fileName)
        {
            try
            {
                var configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "API_config", fileName);
                if (File.Exists(configPath))
                {
                    var configJson = File.ReadAllText(configPath);
                    var config = JsonSerializer.Deserialize<ApiConfiguration>(configJson);
                    if (config != null)
                    {
                        _apiConfigurations[serviceName] = config;
                        _logger.LogInformation($"加载 {serviceName} API配置成功");
                    }
                }
                else
                {
                    _logger.LogWarning($"API配置文件不存在: {configPath}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"加载 {serviceName} API配置失败");
            }
        }

        /// <summary>
        /// 获取API密钥
        /// </summary>
        public string GetApiKey(string serviceName)
        {
            if (_apiConfigurations.TryGetValue(serviceName, out var config))
            {
                return config.ApiKey ?? string.Empty;
            }
            return string.Empty;
        }

        /// <summary>
        /// 获取配置项
        /// </summary>
        public T GetConfig<T>(string key, T defaultValue = default)
        {
            try
            {
                if (_config.TryGetValue(key, out var value))
                {
                    if (value is JsonElement jsonElement)
                    {
                        return JsonSerializer.Deserialize<T>(jsonElement.GetRawText());
                    }
                    return (T)Convert.ChangeType(value, typeof(T));
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, $"获取配置项 '{key}' 失败，使用默认值");
            }
            return defaultValue;
        }

        /// <summary>
        /// 获取翻译器配置
        /// </summary>
        public TranslatorConfiguration GetTranslatorConfig(string translatorType)
        {
            try
            {
                var configKey = $"{translatorType}_translator";
                var config = GetConfig<Dictionary<string, object>>(configKey, new Dictionary<string, object>());
                
                return new TranslatorConfiguration
                {
                    Model = GetConfigValue(config, "model", GetDefaultModel(translatorType)),
                    Temperature = GetConfigValue(config, "temperature", 0.2f),
                    Timeout = GetConfigValue(config, "timeout", 60),
                    ApiUrl = GetConfigValue(config, "api_url", GetDefaultApiUrl(translatorType)),
                    ModelListTimeout = GetConfigValue(config, "model_list_timeout", 10),
                    TranslateTimeout = GetConfigValue(config, "translate_timeout", 60)
                };
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"获取 {translatorType} 翻译器配置失败");
                return new TranslatorConfiguration();
            }
        }

        /// <summary>
        /// 获取配置值
        /// </summary>
        private T GetConfigValue<T>(Dictionary<string, object> config, string key, T defaultValue)
        {
            try
            {
                if (config.TryGetValue(key, out var value))
                {
                    if (value is JsonElement jsonElement)
                    {
                        return JsonSerializer.Deserialize<T>(jsonElement.GetRawText());
                    }
                    return (T)Convert.ChangeType(value, typeof(T));
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, $"获取配置值 '{key}' 失败，使用默认值");
            }
            return defaultValue;
        }

        /// <summary>
        /// 获取默认模型
        /// </summary>
        private string GetDefaultModel(string translatorType)
        {
            return translatorType switch
            {
                "siliconflow" => "deepseek-ai/DeepSeek-V3",
                "zhipuai" => "glm-4-flash-250414",
                "ollama" => "qwen2.5:7b",
                "intranet" => "deepseek-r1-70b",
                _ => "default-model"
            };
        }

        /// <summary>
        /// 获取默认API URL
        /// </summary>
        private string GetDefaultApiUrl(string translatorType)
        {
            return translatorType switch
            {
                "siliconflow" => "https://api.siliconflow.cn/v1",
                "zhipuai" => "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "ollama" => "http://localhost:11434",
                "intranet" => "",
                _ => ""
            };
        }

        /// <summary>
        /// 保存配置
        /// </summary>
        public void SaveConfig(string key, object value)
        {
            try
            {
                _config[key] = value;
                
                var configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config.json");
                var options = new JsonSerializerOptions
                {
                    WriteIndented = true,
                    Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
                };
                
                var configJson = JsonSerializer.Serialize(_config, options);
                File.WriteAllText(configPath, configJson);
                
                _logger.LogInformation($"配置项 '{key}' 保存成功");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"保存配置项 '{key}' 失败");
            }
        }

        /// <summary>
        /// 保存API配置
        /// </summary>
        public void SaveApiConfig(string serviceName, string apiKey)
        {
            try
            {
                var config = new ApiConfiguration { ApiKey = apiKey };
                _apiConfigurations[serviceName] = config;
                
                var fileName = serviceName switch
                {
                    "siliconflow" => "siliconflow_api.json",
                    "zhipuai" => "zhipu_api.json",
                    "ollama" => "ollama_api.json",
                    "intranet" => "intranet_api.json",
                    _ => $"{serviceName}_api.json"
                };
                
                var configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "API_config", fileName);
                var directory = Path.GetDirectoryName(configPath);
                
                if (!Directory.Exists(directory))
                {
                    Directory.CreateDirectory(directory);
                }
                
                var options = new JsonSerializerOptions
                {
                    WriteIndented = true,
                    PropertyNamingPolicy = JsonNamingPolicy.CamelCase
                };
                
                var configJson = JsonSerializer.Serialize(config, options);
                File.WriteAllText(configPath, configJson);
                
                _logger.LogInformation($"{serviceName} API配置保存成功");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"保存 {serviceName} API配置失败");
            }
        }

        /// <summary>
        /// 重新加载配置
        /// </summary>
        public void ReloadConfiguration()
        {
            LoadConfiguration();
            LoadApiConfigurations();
        }

        /// <summary>
        /// 获取所有支持的翻译器类型
        /// </summary>
        public List<string> GetSupportedTranslatorTypes()
        {
            return new List<string> { "siliconflow", "zhipuai", "ollama", "intranet" };
        }

        /// <summary>
        /// 检查翻译器是否已配置
        /// </summary>
        public bool IsTranslatorConfigured(string translatorType)
        {
            return translatorType switch
            {
                "siliconflow" => !string.IsNullOrEmpty(GetApiKey("siliconflow")),
                "zhipuai" => !string.IsNullOrEmpty(GetApiKey("zhipuai")),
                "ollama" => true, // Ollama通常不需要API密钥
                "intranet" => !string.IsNullOrEmpty(GetTranslatorConfig("intranet").ApiUrl),
                _ => false
            };
        }
    }

    /// <summary>
    /// API配置类
    /// </summary>
    public class ApiConfiguration
    {
        public string ApiKey { get; set; } = string.Empty;
    }

    /// <summary>
    /// 翻译器配置类
    /// </summary>
    public class TranslatorConfiguration
    {
        public string Model { get; set; } = string.Empty;
        public float Temperature { get; set; } = 0.2f;
        public int Timeout { get; set; } = 60;
        public string ApiUrl { get; set; } = string.Empty;
        public int ModelListTimeout { get; set; } = 10;
        public int TranslateTimeout { get; set; } = 60;
    }
}
