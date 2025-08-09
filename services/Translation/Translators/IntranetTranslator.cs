using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;

namespace DocumentTranslator.Services.Translation.Translators
{
    /// <summary>
    /// 内网翻译器，用于内网环境的API调用
    /// </summary>
    public class IntranetTranslator : BaseTranslator
    {
        private readonly string _apiUrl;
        private readonly string _model;
        private readonly int _timeout;
        private readonly HttpClient _httpClient;

        public IntranetTranslator(ILogger logger, string apiUrl, string model = "deepseek-r1-70b", int timeout = 60)
            : base(logger)
        {
            _model = model ?? throw new ArgumentNullException(nameof(model));
            _timeout = timeout;

            // 确保API URL格式正确
            _apiUrl = apiUrl;
            if (!_apiUrl.EndsWith("/v1/chat/completions"))
            {
                if (_apiUrl.EndsWith("/"))
                {
                    _apiUrl = _apiUrl + "v1/chat/completions";
                }
                else
                {
                    _apiUrl = _apiUrl + "/v1/chat/completions";
                }
            }

            _httpClient = new HttpClient
            {
                Timeout = TimeSpan.FromSeconds(timeout)
            };

            _logger.LogInformation($"初始化内网翻译器，模型: {model}, API URL: {_apiUrl}");
        }

        public override async Task<string> TranslateAsync(string text, Dictionary<string, string> terminologyDict = null,
            string sourceLang = "zh", string targetLang = "en", string prompt = null)
        {
            if (string.IsNullOrWhiteSpace(text))
                return string.Empty;

            try
            {
                // 获取源语言和目标语言的名称
                var sourceLangName = GetLanguageName(sourceLang);
                var targetLangName = GetLanguageName(targetLang);

                // 构建翻译提示词
                string finalPromptText;
                if (terminologyDict != null && terminologyDict.Any())
                {
                    // 有术语的情况
                    var terminologyText = string.Join("\n", terminologyDict.Select(kvp => $"{kvp.Key}: {kvp.Value}"));

                    var promptCore = $"你是一位高度熟练的专业翻译员。请将以下{sourceLangName}文本翻译成{targetLangName}。\n\n" +
                                   "通用翻译要求：\n" +
                                   "1. 确保翻译专业、准确且自然流畅。\n" +
                                   "2. 最终输出必须仅为翻译后的文本，不含任何额外评论、分析或如 '原文：' 或 '译文：' 等标记。\n" +
                                   "3. 严格按照提供的术语对照表进行翻译，确保术语翻译的一致性和准确性。\n\n" +
                                   $"术语对照表：\n{terminologyText}\n";

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
                    // 没有术语的情况
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

                // 构建请求数据
                var requestData = new
                {
                    model = _model,
                    messages = new[]
                    {
                        new { role = "system", content = "你是一位专业的翻译助手，请严格遵循用户提供的所有翻译指令，特别是关于术语和占位符的指令。" },
                        new { role = "user", content = finalPromptText }
                    },
                    stream = false,
                    temperature = 0.2
                };

                var jsonContent = JsonConvert.SerializeObject(requestData);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync(_apiUrl, content);

                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync();
                    var responseData = JsonConvert.DeserializeObject<dynamic>(responseJson);

                    var rawTranslation = responseData?.choices?[0]?.message?.content?.ToString()?.Trim() ?? string.Empty;

                    // 过滤思维链和其他不必要的输出
                    var translation = FilterOutput(rawTranslation, sourceLang, targetLang);

                    if (string.IsNullOrWhiteSpace(translation))
                    {
                        _logger.LogWarning("翻译结果为空，返回原始响应");
                        translation = rawTranslation;
                    }

                    _logger.LogInformation($"内网翻译成功，结果长度: {translation.Length}");
                    return translation;
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    _logger.LogError($"内网API请求失败，状态码: {response.StatusCode}，响应内容: {errorContent}");
                    throw new Exception($"内网API请求失败: HTTP {response.StatusCode}");
                }
            }
            catch (TaskCanceledException)
            {
                _logger.LogError($"内网API请求超时 (超时时间: {_timeout}秒)");
                throw new Exception($"内网API请求超时，请检查网络连接或增加超时时间");
            }
            catch (HttpRequestException ex)
            {
                _logger.LogError(ex, "无法连接到内网API");
                throw new Exception($"无法连接到内网API，请检查服务器地址和网络连接");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "内网翻译失败");
                throw;
            }
        }

        public override async Task<List<string>> GetAvailableModelsAsync()
        {
            // 常见的内网模型列表，可以根据实际情况调整
            return await Task.FromResult(new List<string>
            {
                "deepseek-r1-70b",
                "deepseek-r1-32b",
                "deepseek-r1-8b",
                "qwen2.5-72b",
                "qwen2.5-32b",
                "qwen2.5-14b",
                "qwen2.5-7b",
                "llama3.1-70b",
                "llama3.1-8b"
            });
        }

        public override async Task<bool> TestConnectionAsync()
        {
            try
            {
                var testData = new
                {
                    model = _model,
                    messages = new[] { new { role = "user", content = "测试连接" } },
                    stream = false,
                    max_tokens = 10
                };

                var jsonContent = JsonConvert.SerializeObject(testData);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                using var cts = new System.Threading.CancellationTokenSource(TimeSpan.FromSeconds(5));
                var response = await _httpClient.PostAsync(_apiUrl, content, cts.Token);

                if (response.IsSuccessStatusCode)
                {
                    _logger.LogInformation("内网API连接测试成功");
                    return true;
                }
                else
                {
                    _logger.LogWarning($"内网API连接测试失败，状态码: {response.StatusCode}");
                    return false;
                }
            }
            catch (TaskCanceledException)
            {
                _logger.LogWarning("内网API连接超时，请检查网络连接");
                return false;
            }
            catch (HttpRequestException ex)
            {
                _logger.LogWarning(ex, "内网API连接错误");
                return false;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "内网API连接测试失败");
                return false;
            }
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
