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
    /// Ollama翻译器，用于本地模型翻译
    /// </summary>
    public class OllamaTranslator : BaseTranslator
    {
        private readonly string _model;
        private readonly string _baseUrl;
        private readonly string _apiUrl;
        private readonly int _modelListTimeout;
        private readonly int _translateTimeout;
        private readonly HttpClient _httpClient;

        public OllamaTranslator(ILogger logger, string model, string apiUrl, 
            int modelListTimeout = 10, int translateTimeout = 60)
            : base(logger)
        {
            _model = model ?? throw new ArgumentNullException(nameof(model));
            
            // 统一使用正确的API端点
            if (apiUrl.Contains("localhost:11434"))
            {
                _baseUrl = "http://localhost:11434";
            }
            else
            {
                _baseUrl = apiUrl.TrimEnd('/').Replace("/api", "");
            }
            
            _apiUrl = $"{_baseUrl}/api/generate";
            _modelListTimeout = modelListTimeout;
            _translateTimeout = translateTimeout;

            _httpClient = new HttpClient
            {
                Timeout = TimeSpan.FromSeconds(Math.Max(modelListTimeout, translateTimeout))
            };

            _logger.LogInformation($"初始化Ollama翻译器，模型: {model}, API URL: {_apiUrl}");
        }

        public override async Task<string> TranslateAsync(string text, Dictionary<string, string> terminologyDict = null,
            string sourceLang = "zh", string targetLang = "en", string prompt = null)
        {
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

                // 构建提示词
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

                // 构建Ollama请求
                var requestData = new
                {
                    model = _model,
                    prompt = finalPromptText,
                    stream = false
                };

                var jsonContent = JsonConvert.SerializeObject(requestData);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                // 设置翻译超时
                using var cts = new System.Threading.CancellationTokenSource(TimeSpan.FromSeconds(_translateTimeout));
                
                var response = await _httpClient.PostAsync(_apiUrl, content, cts.Token);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync();
                    var responseData = JsonConvert.DeserializeObject<dynamic>(responseJson);

                    var rawTranslation = responseData.response?.ToString()?.Trim() ?? string.Empty;
                    
                    // 过滤输出结果
                    var translation = FilterOutput(rawTranslation, sourceLang, targetLang);
                    
                    // 如果过滤后为空，返回原始响应
                    if (string.IsNullOrWhiteSpace(translation))
                    {
                        translation = rawTranslation;
                    }

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

                    _logger.LogInformation($"Ollama翻译成功，结果长度: {translation.Length}");
                    return translation;
                }
                else
                {
                    var errorContent = await response.Content.ReadAsStringAsync();
                    _logger.LogError($"Ollama API请求失败，状态码: {response.StatusCode}，错误: {errorContent}");
                    throw new Exception($"Ollama API请求失败: HTTP {response.StatusCode}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Ollama翻译失败");
                throw new Exception($"Ollama翻译失败: {ex.Message}");
            }
        }

        public override async Task<List<string>> GetAvailableModelsAsync()
        {
            try
            {
                using var cts = new System.Threading.CancellationTokenSource(TimeSpan.FromSeconds(_modelListTimeout));
                var response = await _httpClient.GetAsync($"{_baseUrl}/api/tags", cts.Token);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseJson = await response.Content.ReadAsStringAsync();
                    var responseData = JsonConvert.DeserializeObject<dynamic>(responseJson);
                    
                    var models = new List<string>();
                    if (responseData.models != null)
                    {
                        foreach (var model in responseData.models)
                        {
                            models.Add(model.name.ToString());
                        }
                    }
                    return models;
                }
                
                _logger.LogWarning($"获取Ollama模型列表失败，状态码: {response.StatusCode}");
                return new List<string>();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "获取Ollama模型列表失败");
                return new List<string>();
            }
        }

        public override async Task<bool> TestConnectionAsync()
        {
            try
            {
                using var cts = new System.Threading.CancellationTokenSource(TimeSpan.FromSeconds(5));
                var response = await _httpClient.GetAsync($"{_baseUrl}/api/tags", cts.Token);
                
                if (response.IsSuccessStatusCode)
                {
                    _logger.LogInformation("Ollama连接测试成功");
                    return true;
                }
                else
                {
                    _logger.LogWarning($"Ollama连接测试失败，状态码: {response.StatusCode}");
                    return false;
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Ollama连接测试失败");
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
