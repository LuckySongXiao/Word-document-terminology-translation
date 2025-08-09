using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Security.Authentication;
using System.Text;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;

namespace DocumentTranslator.Services.Translation.Translators
{
    /// <summary>
    /// 智谱AI翻译器
    /// </summary>
    public class ZhipuAITranslator : BaseTranslator
    {
        private readonly string _apiKey;
        private readonly string _model;
        private readonly float _temperature;
        private readonly int _timeout;
        private readonly HttpClient _httpClient;
        private const string ApiUrl = "https://open.bigmodel.cn/api/paas/v4/chat/completions";

        public ZhipuAITranslator(ILogger logger, string apiKey, string model = "GLM-4-Flash-250414", 
            float temperature = 0.2f, int timeout = 60)
            : base(logger)
        {
            _apiKey = apiKey ?? throw new ArgumentNullException(nameof(apiKey));
            _model = model;
            _temperature = temperature;
            _timeout = timeout;

            // 创建HttpClient，配置TLS和重试策略
            var handler = new HttpClientHandler()
            {
                SslProtocols = SslProtocols.Tls12,
                ServerCertificateCustomValidationCallback = (sender, cert, chain, sslPolicyErrors) => true
            };

            _httpClient = new HttpClient(handler)
            {
                Timeout = TimeSpan.FromSeconds(timeout)
            };

            _httpClient.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiKey}");

            var apiKeyDisplay = apiKey.Length > 8 ? apiKey.Substring(0, 8) + "..." : "None";
            _logger.LogInformation($"初始化智谱AI翻译器，模型: {model}, API Key前缀: {apiKeyDisplay}");
        }

        public override async Task<string> TranslateAsync(string text, Dictionary<string, string> terminologyDict = null,
            string sourceLang = "zh", string targetLang = "en", string prompt = null)
        {
            if (string.IsNullOrEmpty(_apiKey))
            {
                throw new InvalidOperationException("未配置智谱AI API Key");
            }

            try
            {
                // 获取源语言和目标语言的名称
                var sourceLangName = GetLanguageName(sourceLang);
                var targetLangName = GetLanguageName(targetLang);

                // 术语预处理和提示构建逻辑
                var processedTextForLlm = text;
                var finalPromptText = string.Empty;
                var termInstructionsForLlm = new List<string>();
                var placeholdersUsed = false;
                var placeholderToTerm = new Dictionary<string, string>();

                if (terminologyDict != null && terminologyDict.Any())
                {
                    // 按键（源术语）长度降序排序，以便优先匹配较长的术语
                    var sortedTerms = terminologyDict.OrderByDescending(kvp => kvp.Key.Length).ToList();
                    var tempProcessedText = text;

                    for (int i = 0; i < sortedTerms.Count; i++)
                    {
                        var (sourceTermFromDict, targetTermFromDict) = sortedTerms[i];
                        var placeholder = $"__TERM_PH_{i}__";

                        if (tempProcessedText.Contains(sourceTermFromDict))
                        {
                            tempProcessedText = tempProcessedText.Replace(sourceTermFromDict, placeholder);
                            termInstructionsForLlm.Add(
                                $"占位符 {placeholder} (原文为 \"{sourceTermFromDict}\") 必须严格翻译为 \"{targetTermFromDict}\"。");
                            placeholdersUsed = true;
                            placeholderToTerm[placeholder] = targetTermFromDict;
                        }
                    }

                    if (placeholdersUsed)
                    {
                        processedTextForLlm = tempProcessedText;
                    }
                }

                // 构建提示词（与SiliconFlow相同的逻辑）
                if (placeholdersUsed)
                {
                    var instructionBlock = "术语指令 (请严格遵守)：\n" + string.Join("\n", termInstructionsForLlm);
                    var promptCore = $"你是一位高度熟练的专业翻译员。请将以下{sourceLangName}文本翻译成{targetLangName}。\n" +
                                   $"{instructionBlock}\n\n" +
                                   "通用翻译要求：\n" +
                                   "1. 对于任何占位符，请严格遵守上述术语指令。\n" +
                                   "2. 对于文本中未被占位符覆盖的部分，请确保翻译专业、准确且自然流畅。\n" +
                                   "3. 最终输出必须仅为翻译后的文本，不含任何额外评论、分析或如 '原文：' 或 '译文：' 等标记。\n";

                    if (!string.IsNullOrEmpty(prompt))
                    {
                        promptCore += $"\n额外的用户提供风格/语气指导：{prompt}\n";
                    }

                    finalPromptText = targetLang == "zh"
                        ? promptCore + $"\n待翻译文本 (可能包含占位符)：\n{processedTextForLlm}\n\n请提供纯中文翻译："
                        : promptCore + $"\n待翻译文本 (可能包含占位符)：\n{processedTextForLlm}\n\n请提供纯{targetLangName}翻译：";
                }
                else if (terminologyDict != null && terminologyDict.Any())
                {
                    // 术语存在，但未找到术语进行占位符替换
                    var promptCore = $"你是一位高度熟练的专业翻译员。请将以下{sourceLangName}文本翻译成{targetLangName}。\n\n" +
                                   "请严格使用此术语映射：\n";

                    foreach (var (sTerm, tTerm) in terminologyDict)
                    {
                        promptCore += $"[{sTerm}] → [{tTerm}]\n";
                    }

                    promptCore += "\n通用翻译要求：\n" +
                                "1. 上述映射中的所有术语必须按规定翻译。\n" +
                                "2. 其余文本确保翻译专业、准确且自然流畅。\n" +
                                "3. 最终输出必须仅为翻译后的文本，不含任何额外评论、分析或如 '原文：' 或 '译文：' 等标记。\n";

                    if (!string.IsNullOrEmpty(prompt))
                    {
                        promptCore += $"\n额外的用户提供风格/语气指导：{prompt}\n";
                    }

                    finalPromptText = targetLang == "zh"
                        ? promptCore + $"\n待翻译文本：\n{text}\n\n请提供纯中文翻译："
                        : promptCore + $"\n待翻译文本：\n{text}\n\n请提供纯{targetLangName}翻译：";
                }
                else
                {
                    // 完全没有术语
                    var promptCore = $"你是一位高度熟练的专业翻译员。请将以下{sourceLangName}文本翻译成{targetLangName}。\n\n" +
                                   "通用翻译要求：\n" +
                                   "1. 确保翻译专业、准确且自然流畅。\n" +
                                   "2. 最终输出必须仅为翻译后的文本，不含任何额外评论、分析或如 '原文：' 或 '译文：' 等标记。\n";

                    if (!string.IsNullOrEmpty(prompt))
                    {
                        promptCore += $"\n额外的用户提供风格/语气指导：{prompt}\n";
                    }

                    finalPromptText = targetLang == "zh"
                        ? promptCore + $"\n待翻译文本：\n{text}\n\n请提供纯中文翻译："
                        : promptCore + $"\n待翻译文本：\n{text}\n\n请提供纯{targetLangName}翻译：";
                }

                // 构建请求
                var requestData = new
                {
                    model = _model,
                    messages = new[]
                    {
                        new { role = "system", content = "你是一位专业的翻译助手，请严格遵循用户提供的所有翻译指令，特别是关于术语和占位符的指令。" },
                        new { role = "user", content = finalPromptText }
                    },
                    temperature = _temperature
                };

                var jsonContent = JsonConvert.SerializeObject(requestData);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                _logger.LogInformation($"发送翻译请求到智谱AI，模型: {_model}");

                // 发送请求，包含重试机制
                var response = await SendRequestWithRetryAsync(content);
                response.EnsureSuccessStatusCode();

                var responseJson = await response.Content.ReadAsStringAsync();
                var responseData = JsonConvert.DeserializeObject<dynamic>(responseJson);

                var rawTranslation = responseData.choices[0].message.content.ToString().Trim();
                
                // 过滤思维链
                var translation = FilterOutput(rawTranslation, sourceLang, targetLang);

                // 如果使用了占位符，需要将占位符替换回实际术语
                if (placeholdersUsed && placeholderToTerm.Any())
                {
                    _logger.LogInformation("开始恢复占位符为实际术语...");
                    
                    foreach (var (placeholder, targetTerm) in placeholderToTerm)
                    {
                        if (translation.Contains(placeholder))
                        {
                            translation = translation.Replace(placeholder, targetTerm);
                            _logger.LogInformation($"恢复占位符: {placeholder} -> {targetTerm}");
                        }
                    }

                    _logger.LogInformation($"占位符恢复完成，最终翻译结果长度: {translation.Length}");
                }

                _logger.LogInformation($"智谱AI翻译成功，结果长度: {translation.Length}");
                return translation;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "智谱AI翻译失败");
                throw new Exception($"智谱AI翻译失败: {ex.Message}");
            }
        }

        /// <summary>
        /// 发送请求并包含重试机制
        /// </summary>
        private async Task<HttpResponseMessage> SendRequestWithRetryAsync(HttpContent content, int maxRetries = 3)
        {
            for (int attempt = 0; attempt < maxRetries; attempt++)
            {
                try
                {
                    var response = await _httpClient.PostAsync(ApiUrl, content);
                    if (response.IsSuccessStatusCode)
                    {
                        return response;
                    }
                    
                    if (attempt == maxRetries - 1)
                    {
                        return response; // 最后一次尝试，返回响应让上层处理
                    }
                    
                    _logger.LogWarning($"智谱AI请求失败，状态码: {response.StatusCode}，正在重试 ({attempt + 1}/{maxRetries})");
                    await Task.Delay(TimeSpan.FromSeconds(Math.Pow(2, attempt))); // 指数退避
                }
                catch (Exception ex) when (attempt < maxRetries - 1)
                {
                    _logger.LogWarning(ex, $"智谱AI请求异常，正在重试 ({attempt + 1}/{maxRetries})");
                    await Task.Delay(TimeSpan.FromSeconds(Math.Pow(2, attempt))); // 指数退避
                }
            }
            
            throw new InvalidOperationException("重试次数已用完");
        }

        public override async Task<List<string>> GetAvailableModelsAsync()
        {
            // 智谱AI支持的模型列表
            return await Task.FromResult(new List<string>
            {
                "GLM-4-Flash-250414",
                "GLM-4-Flash",
                "GLM-Z1-Flash",
                "GLM-4.1V-Thinking-Flash"
            });
        }

        public override async Task<bool> TestConnectionAsync()
        {
            if (string.IsNullOrEmpty(_apiKey))
            {
                _logger.LogWarning("未配置智谱AI API Key");
                return false;
            }

            const int maxRetries = 3;
            for (int retryCount = 0; retryCount < maxRetries; retryCount++)
            {
                try
                {
                    _logger.LogInformation($"尝试连接智谱AI服务，API URL: {ApiUrl}");

                    var testData = new
                    {
                        model = _model,
                        messages = new[]
                        {
                            new { role = "user", content = "测试连接" }
                        },
                        max_tokens = 10
                    };

                    var jsonContent = JsonConvert.SerializeObject(testData);
                    var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                    var response = await _httpClient.PostAsync(ApiUrl, content);
                    
                    if (response.IsSuccessStatusCode)
                    {
                        _logger.LogInformation("智谱AI连接测试成功");
                        return true;
                    }
                    else
                    {
                        _logger.LogWarning($"智谱AI连接测试失败，状态码: {response.StatusCode}");
                        var errorContent = await response.Content.ReadAsStringAsync();
                        _logger.LogWarning($"错误详情: {errorContent}");
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, "智谱AI连接测试失败");

                    // 一般错误重试
                    if (retryCount < maxRetries - 1)
                    {
                        _logger.LogInformation($"将在2秒后进行第{retryCount + 2}次重试...");
                        await Task.Delay(2000);
                    }
                    else
                    {
                        _logger.LogError($"已达到最大重试次数({maxRetries})，放弃连接");
                        return false;
                    }
                }
            }

            return false;
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                _httpClient?.Dispose();
            }
            base.Dispose(disposing);
        }
    }
}
