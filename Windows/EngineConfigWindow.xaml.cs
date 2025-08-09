using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using System.Diagnostics;
using System.Net.Http;
using Newtonsoft.Json;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.DependencyInjection;
using DocumentTranslator.Services.Translation;
using DocumentTranslator.Services.Logging;

namespace DocumentTranslator.Windows
{
    public partial class EngineConfigWindow : Window
    {
        private readonly HttpClient _httpClient;
        private readonly string _configPath;
        private readonly TranslationService _translationService;
        private readonly ConfigurationManager _configurationManager;
        private readonly ILogger<EngineConfigWindow> _logger;

        public EngineConfigWindow()
        {
            InitializeComponent();

            // 初始化依赖注入容器
            var services = new ServiceCollection();
            ConfigureServices(services);
            var serviceProvider = services.BuildServiceProvider();

            // 获取服务实例
            _translationService = serviceProvider.GetRequiredService<TranslationService>();
            _configurationManager = serviceProvider.GetRequiredService<ConfigurationManager>();
            _logger = serviceProvider.GetRequiredService<ILogger<EngineConfigWindow>>();

            _httpClient = new HttpClient();
            _configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "API_config");

            LoadAllConfigs();
        }

        /// <summary>
        /// 配置依赖注入服务
        /// </summary>
        private void ConfigureServices(IServiceCollection services)
        {
            // 配置日志
            services.AddLogging(builder =>
            {
                builder.ClearProviders();
                builder.AddProvider(new TranslationLoggerProvider());
                builder.SetMinimumLevel(LogLevel.Information);
            });

            // 注册服务
            services.AddSingleton<ConfigurationManager>();
            services.AddSingleton<TranslationService>();
        }

        private void LoadAllConfigs()
        {
            LoadZhipuConfig();
            LoadOllamaConfig();
            LoadSiliconFlowConfig();
            LoadIntranetConfig();
        }

        #region 智谱AI配置
        private async void LoadZhipuConfig()
        {
            try
            {
                // 使用配置管理器加载配置
                var translatorConfig = _configurationManager.GetTranslatorConfig("zhipuai");
                var apiKey = _configurationManager.GetApiKey("zhipuai");

                // 优先从环境变量加载API密钥
                var envApiKey = LoadApiKeyFromEnvironment("ZHIPU_API_KEY");
                ZhipuApiKey.Password = !string.IsNullOrEmpty(envApiKey) ? envApiKey : apiKey;

                ZhipuApiUrl.Text = translatorConfig.ApiUrl;
                ZhipuTemperature.Value = translatorConfig.Temperature;
                ZhipuMaxTokens.Text = "4000"; // 默认值

                // 动态加载模型列表
                await LoadZhipuModels(translatorConfig.Model);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "加载智谱AI配置失败");
                MessageBox.Show($"加载智谱AI配置失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        /// <summary>
        /// 加载智谱AI模型列表
        /// </summary>
        private async Task LoadZhipuModels(string defaultModel)
        {
            try
            {
                // 清空现有模型列表
                ZhipuDefaultModel.Items.Clear();

                // 尝试从翻译服务获取可用模型
                var models = await _translationService.GetAvailableModelsAsync("zhipuai");

                if (models.Any())
                {
                    foreach (var model in models)
                    {
                        ZhipuDefaultModel.Items.Add(new ComboBoxItem { Content = model });
                    }
                }
                else
                {
                    // 如果无法获取模型列表，使用默认模型
                    var defaultModels = new[]
                    {
                        "glm-4-flash-250414",
                        "GLM-4-Flash",
                        "GLM-Z1-Flash",
                        "GLM-4.1V-Thinking-Flash"
                    };

                    foreach (var model in defaultModels)
                    {
                        ZhipuDefaultModel.Items.Add(new ComboBoxItem { Content = model });
                    }
                }

                // 设置默认选中的模型
                SetSelectedModel(ZhipuDefaultModel, defaultModel);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "加载智谱AI模型列表失败");
            }
        }

        /// <summary>
        /// 设置ComboBox的选中模型
        /// </summary>
        private void SetSelectedModel(ComboBox comboBox, string modelName)
        {
            try
            {
                if (string.IsNullOrEmpty(modelName)) return;

                foreach (ComboBoxItem item in comboBox.Items)
                {
                    if (item.Content.ToString() == modelName)
                    {
                        comboBox.SelectedItem = item;
                        return;
                    }
                }

                // 如果没有找到匹配的模型，设置为第一个
                if (comboBox.Items.Count > 0)
                {
                    comboBox.SelectedIndex = 0;
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, $"设置选中模型失败: {modelName}");
            }
        }

        private async void TestZhipuConnection(object sender, RoutedEventArgs e)
        {
            var button = sender as Button;
            button.IsEnabled = false;
            button.Content = "🔄 测试中...";

            try
            {
                // 检查翻译服务是否已初始化
                if (_translationService == null)
                {
                    MessageBox.Show("❌ 翻译服务未初始化", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // 设置当前翻译器类型
                _translationService.CurrentTranslatorType = "zhipuai";

                // 检查当前翻译器是否可用
                if (_translationService.CurrentTranslator == null)
                {
                    MessageBox.Show("❌ 智谱AI翻译器未初始化，请检查配置", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // 执行连接测试
                var result = await _translationService.CurrentTranslator.TestConnectionAsync();

                if (result == true)
                {
                    MessageBox.Show("✅ 智谱AI连接测试成功！", "测试结果", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                else
                {
                    MessageBox.Show("❌ 智谱AI连接测试失败，请检查API密钥和网络连接", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "智谱AI连接测试异常");
                MessageBox.Show($"❌ 连接测试异常: {ex.Message}", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                button.IsEnabled = true;
                button.Content = "🧪 测试连接";
            }
        }

        private void SaveZhipuConfig(object sender, RoutedEventArgs e)
        {
            try
            {
                // 保存API密钥到环境变量和配置管理器
                SaveApiKeyToEnvironment("ZHIPU_API_KEY", ZhipuApiKey.Password);
                _configurationManager.SaveApiConfig("zhipuai", ZhipuApiKey.Password);

                // 保存其他配置到主配置文件
                var selectedModel = (ZhipuDefaultModel.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "GLM-4-Flash";

                _configurationManager.SaveConfig("zhipuai_translator", new
                {
                    model = selectedModel,
                    temperature = ZhipuTemperature.Value,
                    timeout = 60,
                    api_url = ZhipuApiUrl.Text
                });

                MessageBox.Show("✅ 智谱AI配置保存成功！\nAPI密钥已安全保存到系统环境变量中。", "保存结果", MessageBoxButton.OK, MessageBoxImage.Information);

                // 重新初始化智谱AI翻译器
                _translationService.ReinitializeTranslator("zhipuai");

                _logger.LogInformation($"智谱AI配置已保存: 模型={selectedModel}, 温度={ZhipuTemperature.Value}");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "保存智谱AI配置失败");
                MessageBox.Show($"❌ 保存配置失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        #endregion

        #region Ollama配置
        private async void LoadOllamaConfig()
        {
            try
            {
                // 使用配置管理器加载配置
                var translatorConfig = _configurationManager.GetTranslatorConfig("ollama");

                OllamaUrl.Text = translatorConfig.ApiUrl;
                OllamaTemperature.Value = translatorConfig.Temperature;
                OllamaContextLength.Text = "4096"; // 默认值
                OllamaKeepAlive.IsChecked = false; // 默认值

                // 动态加载模型列表
                await LoadOllamaModels(translatorConfig.Model);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "加载Ollama配置失败");
                MessageBox.Show($"加载Ollama配置失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                LoadDefaultOllamaModels();
            }
        }

        /// <summary>
        /// 加载Ollama模型列表
        /// </summary>
        private async Task LoadOllamaModels(string defaultModel)
        {
            try
            {
                // 清空现有模型列表
                OllamaDefaultModel.Items.Clear();

                // 尝试从翻译服务获取可用模型
                var models = await _translationService.GetAvailableModelsAsync("ollama");

                if (models.Any())
                {
                    foreach (var model in models)
                    {
                        OllamaDefaultModel.Items.Add(new ComboBoxItem { Content = model });
                    }
                }
                else
                {
                    // 如果无法获取模型列表，使用默认模型
                    LoadDefaultOllamaModels();
                }

                // 设置默认选中的模型
                SetSelectedModel(OllamaDefaultModel, defaultModel);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "加载Ollama模型列表失败");
                LoadDefaultOllamaModels();
            }
        }

        private void LoadDetectedModels(dynamic config)
        {
            try
            {
                // 清空现有模型列表
                OllamaDefaultModel.Items.Clear();

                // 添加默认模型选项
                LoadDefaultOllamaModels();

                // 如果有检测到的模型，添加到列表中
                if (config?.detected_models != null)
                {
                    foreach (var model in config.detected_models)
                    {
                        var modelName = model.name?.ToString();
                        if (!string.IsNullOrEmpty(modelName))
                        {
                            // 检查是否已存在，避免重复
                            bool exists = false;
                            foreach (ComboBoxItem item in OllamaDefaultModel.Items)
                            {
                                if (item.Content.ToString() == modelName)
                                {
                                    exists = true;
                                    break;
                                }
                            }

                            if (!exists)
                            {
                                OllamaDefaultModel.Items.Add(new ComboBoxItem { Content = modelName });
                            }
                        }
                    }

                    // 显示最后检测时间
                    var lastDetection = config?.last_detection?.ToString();
                    if (!string.IsNullOrEmpty(lastDetection))
                    {
                        System.Diagnostics.Debug.WriteLine($"上次模型检测时间: {lastDetection}");
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"加载检测到的模型失败: {ex.Message}");
            }
        }

        private void LoadDefaultOllamaModels()
        {
            // 添加常用的默认模型选项
            var defaultModels = new[] { "llama2", "qwen", "mistral", "codellama", "llama3", "gemma" };

            foreach (var model in defaultModels)
            {
                OllamaDefaultModel.Items.Add(new ComboBoxItem { Content = model });
            }
        }

        private async void RefreshOllamaModels(object sender, RoutedEventArgs e)
        {
            var button = sender as Button;
            button.IsEnabled = false;
            button.Content = "🔄 刷新中...";

            try
            {
                // 使用翻译服务获取模型列表
                _translationService.CurrentTranslatorType = "ollama";
                var models = await _translationService.GetAvailableModelsAsync("ollama");

                OllamaDefaultModel.Items.Clear();
                var modelCount = 0;

                if (models.Any())
                {
                    foreach (var model in models)
                    {
                        OllamaDefaultModel.Items.Add(new ComboBoxItem { Content = model });
                        modelCount++;
                    }

                    MessageBox.Show($"✅ 模型列表刷新成功！检测到 {modelCount} 个模型", "刷新结果", MessageBoxButton.OK, MessageBoxImage.Information);
                    _logger.LogInformation($"Ollama模型列表刷新成功，检测到 {modelCount} 个模型");
                }
                else
                {
                    // 如果无法获取模型，加载默认模型
                    LoadDefaultOllamaModels();
                    MessageBox.Show("⚠️ 无法获取Ollama模型列表，已加载默认模型\n请确保Ollama服务正在运行", "刷新结果", MessageBoxButton.OK, MessageBoxImage.Warning);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "刷新Ollama模型列表失败");
                LoadDefaultOllamaModels();
                MessageBox.Show($"❌ 刷新异常: {ex.Message}\n请检查Ollama服务地址是否正确", "刷新结果", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                button.IsEnabled = true;
                button.Content = "🔄 刷新模型";
            }
        }

        private async Task SaveDetectedModelsToConfig(dynamic models)
        {
            try
            {
                var configFile = Path.Combine(_configPath, "ollama_api.json");
                var config = new Dictionary<string, object>();

                // 加载现有配置
                if (File.Exists(configFile))
                {
                    var existingJson = await File.ReadAllTextAsync(configFile);
                    config = JsonConvert.DeserializeObject<Dictionary<string, object>>(existingJson) ?? new Dictionary<string, object>();
                }

                // 更新模型列表
                var modelList = new List<object>();
                if (models != null)
                {
                    foreach (var model in models)
                    {
                        modelList.Add(new
                        {
                            name = model.name?.ToString(),
                            size = model.size?.ToString(),
                            modified_at = model.modified_at?.ToString(),
                            digest = model.digest?.ToString()
                        });
                    }
                }

                config["detected_models"] = modelList;
                config["last_detection"] = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");

                // 保存配置
                var json = JsonConvert.SerializeObject(config, Formatting.Indented);
                Directory.CreateDirectory(_configPath);
                await File.WriteAllTextAsync(configFile, json);
            }
            catch (Exception ex)
            {
                // 静默处理保存错误，不影响主要功能
                System.Diagnostics.Debug.WriteLine($"保存模型列表失败: {ex.Message}");
            }
        }

        private async void TestOllamaConnection(object sender, RoutedEventArgs e)
        {
            var button = sender as Button;
            button.IsEnabled = false;
            button.Content = "🔄 测试中...";

            try
            {
                // 检查翻译服务是否已初始化
                if (_translationService == null)
                {
                    MessageBox.Show("❌ 翻译服务未初始化", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // 设置当前翻译器类型
                _translationService.CurrentTranslatorType = "ollama";

                // 检查当前翻译器是否可用
                if (_translationService.CurrentTranslator == null)
                {
                    MessageBox.Show("❌ Ollama翻译器未初始化，请检查配置", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // 执行连接测试
                var result = await _translationService.CurrentTranslator.TestConnectionAsync();

                if (result == true)
                {
                    MessageBox.Show("✅ Ollama连接测试成功！", "测试结果", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                else
                {
                    MessageBox.Show("❌ Ollama连接测试失败，请检查服务是否运行", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Ollama连接测试异常");
                MessageBox.Show($"❌ 连接测试异常: {ex.Message}", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                button.IsEnabled = true;
                button.Content = "🧪 测试连接";
            }
        }

        private void SaveOllamaConfig(object sender, RoutedEventArgs e)
        {
            try
            {
                // 保存配置到配置管理器
                var selectedModel = (OllamaDefaultModel.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "qwen2.5:7b";

                _configurationManager.SaveConfig("ollama_translator", new
                {
                    model = selectedModel,
                    api_url = OllamaUrl.Text,
                    temperature = OllamaTemperature.Value,
                    model_list_timeout = 10,
                    translate_timeout = 60
                });

                MessageBox.Show("✅ Ollama配置保存成功！", "保存结果", MessageBoxButton.OK, MessageBoxImage.Information);

                // 重新初始化Ollama翻译器
                _translationService.ReinitializeTranslator("ollama");

                _logger.LogInformation($"Ollama配置已保存: 模型={selectedModel}, API地址={OllamaUrl.Text}");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "保存Ollama配置失败");
                MessageBox.Show($"❌ 保存配置失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        #endregion

        #region 硅基流动配置
        private void LoadSiliconFlowConfig()
        {
            try
            {
                var configFile = Path.Combine(_configPath, "siliconflow_api.json");
                if (File.Exists(configFile))
                {
                    var json = File.ReadAllText(configFile);
                    var config = JsonConvert.DeserializeObject<dynamic>(json);

                    // 优先从环境变量加载API密钥
                    var envApiKey = LoadApiKeyFromEnvironment("SILICONFLOW_API_KEY");
                    SiliconFlowApiKey.Password = !string.IsNullOrEmpty(envApiKey) ? envApiKey : (config?.api_key ?? "");

                    SiliconFlowApiUrl.Text = config?.api_url ?? "https://api.siliconflow.cn/v1/chat/completions";
                    SiliconFlowDefaultModel.Text = config?.default_model ?? "deepseek-ai/DeepSeek-V2.5";
                    SiliconFlowTemperature.Value = config?.temperature ?? 0.3;
                    SiliconFlowMaxTokens.Text = config?.max_tokens?.ToString() ?? "4000";
                }
                else
                {
                    // 如果配置文件不存在，尝试从环境变量加载API密钥
                    var envApiKey = LoadApiKeyFromEnvironment("SILICONFLOW_API_KEY");
                    SiliconFlowApiKey.Password = envApiKey;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"加载硅基流动配置失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async void TestSiliconFlowConnection(object sender, RoutedEventArgs e)
        {
            var button = sender as Button;
            button.IsEnabled = false;
            button.Content = "🔄 测试中...";

            try
            {
                // 检查翻译服务是否已初始化
                if (_translationService == null)
                {
                    MessageBox.Show("❌ 翻译服务未初始化", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // 设置当前翻译器类型
                _translationService.CurrentTranslatorType = "siliconflow";

                // 检查当前翻译器是否可用
                if (_translationService.CurrentTranslator == null)
                {
                    MessageBox.Show("❌ 硅基流动翻译器未初始化，请检查配置", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // 执行连接测试
                var result = await _translationService.CurrentTranslator.TestConnectionAsync();

                if (result == true)
                {
                    MessageBox.Show("✅ 硅基流动连接测试成功！", "测试结果", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                else
                {
                    MessageBox.Show("❌ 硅基流动连接测试失败，请检查API密钥和网络连接", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "硅基流动连接测试异常");
                MessageBox.Show($"❌ 连接测试异常: {ex.Message}", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                button.IsEnabled = true;
                button.Content = "🧪 测试连接";
            }
        }

        private void SaveSiliconFlowConfig(object sender, RoutedEventArgs e)
        {
            try
            {
                // 保存API密钥到环境变量
                SaveApiKeyToEnvironment("SILICONFLOW_API_KEY", SiliconFlowApiKey.Password);

                var config = new
                {
                    // 不在配置文件中保存API密钥，仅保存其他配置
                    api_url = SiliconFlowApiUrl.Text,
                    default_model = SiliconFlowDefaultModel.Text,
                    temperature = SiliconFlowTemperature.Value,
                    max_tokens = int.Parse(SiliconFlowMaxTokens.Text),
                    // 添加标记表示API密钥保存在环境变量中
                    api_key_in_env = true
                };

                var json = JsonConvert.SerializeObject(config, Formatting.Indented);
                var configFile = Path.Combine(_configPath, "siliconflow_api.json");

                Directory.CreateDirectory(_configPath);
                File.WriteAllText(configFile, json);

                MessageBox.Show("✅ 硅基流动配置保存成功！\nAPI密钥已安全保存到系统环境变量中。", "保存结果", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"❌ 保存配置失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        #endregion

        #region 内网OpenAI配置
        private void LoadIntranetConfig()
        {
            try
            {
                var configFile = Path.Combine(_configPath, "intranet_api.json");
                if (File.Exists(configFile))
                {
                    var json = File.ReadAllText(configFile);
                    var config = JsonConvert.DeserializeObject<dynamic>(json);

                    // 优先从环境变量加载API密钥
                    var envApiKey = LoadApiKeyFromEnvironment("INTRANET_API_KEY");
                    IntranetApiKey.Password = !string.IsNullOrEmpty(envApiKey) ? envApiKey : (config?.api_key ?? "");

                    IntranetApiUrl.Text = config?.api_url ?? "http://your-internal-server/v1/chat/completions";
                    IntranetDefaultModel.Text = config?.default_model ?? "deepseek-r1-70b";
                    IntranetTemperature.Value = config?.temperature ?? 0.3;
                    IntranetMaxTokens.Text = config?.max_tokens?.ToString() ?? "4000";
                    IntranetSkipSSL.IsChecked = config?.skip_ssl ?? false;
                }
                else
                {
                    // 如果配置文件不存在，尝试从环境变量加载API密钥
                    var envApiKey = LoadApiKeyFromEnvironment("INTRANET_API_KEY");
                    IntranetApiKey.Password = envApiKey;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"加载内网OpenAI配置失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async void TestIntranetConnection(object sender, RoutedEventArgs e)
        {
            var button = sender as Button;
            button.IsEnabled = false;
            button.Content = "🔄 测试中...";

            try
            {
                // 检查翻译服务是否已初始化
                if (_translationService == null)
                {
                    MessageBox.Show("❌ 翻译服务未初始化", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // 设置当前翻译器类型
                _translationService.CurrentTranslatorType = "intranet";

                // 检查当前翻译器是否可用
                if (_translationService.CurrentTranslator == null)
                {
                    MessageBox.Show("❌ 内网翻译器未初始化，请检查配置", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // 执行连接测试
                var result = await _translationService.CurrentTranslator.TestConnectionAsync();

                if (result == true)
                {
                    MessageBox.Show("✅ 内网OpenAI连接测试成功！", "测试结果", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                else
                {
                    MessageBox.Show("❌ 内网OpenAI连接测试失败，请检查API密钥和网络连接", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "内网OpenAI连接测试异常");
                MessageBox.Show($"❌ 连接测试异常: {ex.Message}", "测试结果", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                button.IsEnabled = true;
                button.Content = "🧪 测试连接";
            }
        }

        private void SaveIntranetConfig(object sender, RoutedEventArgs e)
        {
            try
            {
                // 保存API密钥到环境变量
                SaveApiKeyToEnvironment("INTRANET_API_KEY", IntranetApiKey.Password);

                var config = new
                {
                    // 不在配置文件中保存API密钥，仅保存其他配置
                    api_url = IntranetApiUrl.Text,
                    default_model = IntranetDefaultModel.Text,
                    temperature = IntranetTemperature.Value,
                    max_tokens = int.Parse(IntranetMaxTokens.Text),
                    skip_ssl = IntranetSkipSSL.IsChecked ?? false,
                    // 添加标记表示API密钥保存在环境变量中
                    api_key_in_env = true
                };

                var json = JsonConvert.SerializeObject(config, Formatting.Indented);
                var configFile = Path.Combine(_configPath, "intranet_api.json");

                Directory.CreateDirectory(_configPath);
                File.WriteAllText(configFile, json);

                MessageBox.Show("✅ 内网OpenAI配置保存成功！\nAPI密钥已安全保存到系统环境变量中。", "保存结果", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"❌ 保存配置失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        #endregion

        #region 环境变量操作
        private void SaveApiKeyToEnvironment(string keyName, string apiKey)
        {
            try
            {
                if (!string.IsNullOrEmpty(apiKey))
                {
                    // 保存到用户环境变量
                    Environment.SetEnvironmentVariable(keyName, apiKey, EnvironmentVariableTarget.User);
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"保存环境变量失败: {ex.Message}");
            }
        }

        private string LoadApiKeyFromEnvironment(string keyName)
        {
            try
            {
                return Environment.GetEnvironmentVariable(keyName, EnvironmentVariableTarget.User) ?? "";
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"读取环境变量失败: {ex.Message}");
                return "";
            }
        }

        private void RemoveApiKeyFromEnvironment(string keyName)
        {
            try
            {
                Environment.SetEnvironmentVariable(keyName, null, EnvironmentVariableTarget.User);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"删除环境变量失败: {ex.Message}");
            }
        }
        #endregion

        #region 通用功能
        private void OpenConfigDirectory(object sender, RoutedEventArgs e)
        {
            try
            {
                Directory.CreateDirectory(_configPath);
                Process.Start("explorer.exe", _configPath);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"打开配置目录失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void ResetAllConfigs(object sender, RoutedEventArgs e)
        {
            var result = MessageBox.Show("确定要重置所有配置吗？这将删除所有已保存的API配置。",
                                       "确认重置", MessageBoxButton.YesNo, MessageBoxImage.Warning);

            if (result == MessageBoxResult.Yes)
            {
                try
                {
                    if (Directory.Exists(_configPath))
                    {
                        Directory.Delete(_configPath, true);
                    }

                    // 重新加载默认配置
                    LoadAllConfigs();

                    MessageBox.Show("✅ 所有配置已重置！", "重置完成", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"重置配置失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        private void CloseWindow(object sender, RoutedEventArgs e)
        {
            this.Close();
        }

        protected override void OnClosed(EventArgs e)
        {
            _httpClient?.Dispose();
            base.OnClosed(e);
        }
        #endregion
    }
}
