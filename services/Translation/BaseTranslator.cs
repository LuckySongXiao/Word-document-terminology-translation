using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace DocumentTranslator.Services.Translation
{
    /// <summary>
    /// 翻译器基础抽象类，提供通用的翻译功能和输出过滤
    /// </summary>
    public abstract class BaseTranslator : ITranslator, IDisposable
    {
        protected readonly ILogger _logger;

        protected BaseTranslator(ILogger logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <summary>
        /// 翻译文本的抽象方法，由具体翻译器实现
        /// </summary>
        public abstract Task<string> TranslateAsync(string text, Dictionary<string, string> terminologyDict = null,
            string sourceLang = "zh", string targetLang = "en", string prompt = null);

        /// <summary>
        /// 获取可用模型列表的抽象方法，由具体翻译器实现
        /// </summary>
        public abstract Task<List<string>> GetAvailableModelsAsync();

        /// <summary>
        /// 测试连接的抽象方法，由具体翻译器实现
        /// </summary>
        public abstract Task<bool> TestConnectionAsync();

        /// <summary>
        /// 过滤模型输出，去除思维链、不必要的标记和提示性文本
        /// </summary>
        /// <param name="text">模型输出的文本</param>
        /// <param name="sourceLang">源语言代码</param>
        /// <param name="targetLang">目标语言代码</param>
        /// <returns>过滤后的文本</returns>
        protected virtual string FilterOutput(string text, string sourceLang = "zh", string targetLang = "en")
        {
            // 如果输入为空，直接返回
            if (string.IsNullOrWhiteSpace(text))
                return string.Empty;

            // 如果存在<think>标签，提取非思维链部分
            if (text.Contains("<think>"))
            {
                // 分割所有的<think>块
                var parts = text.Split(new[] { "<think>" }, StringSplitOptions.None);
                // 获取最后一个非思维链的内容
                var finalText = parts.Last().Trim();
                // 如果最后一部分还包含</think>，取其后面的内容
                if (finalText.Contains("</think>"))
                {
                    finalText = finalText.Split(new[] { "</think>" }, StringSplitOptions.None).Last().Trim();
                }
                text = finalText;
            }

            // 去除常见的标记前缀
            text = text.Trim();

            // 定义需要过滤的提示性文本列表
            var promptTexts = new[]
            {
                "请提供具体的英文文本，以便进行翻译",
                "请提供具体术语内容，以便进行翻译",
                "请提供具体需要翻译的英文文本，以便我进行准确的翻译",
                "请提供英文文本",
                "请提供需要翻译的文本",
                "请提供具体的文本内容",
                "请提供原文",
                "请提供需要翻译的内容",
                "以下是翻译结果",
                "以下是我的翻译",
                "以下是译文",
                "这是翻译结果",
                "这是我的翻译",
                "翻译如下",
                "翻译结果如下",
                "译文如下"
            };

            // 检查文本是否只包含提示性文本
            foreach (var promptText in promptTexts)
            {
                if (text.Trim() == promptText || 
                    text.Trim() == promptText + "。" || 
                    text.Trim() == promptText + ":")
                {
                    return string.Empty; // 如果文本只包含提示性文本，则返回空字符串
                }
            }

            // 去除"原文："和"译文："等标记
            var lines = text.Split('\n');
            var filteredLines = new List<string>();

            // 检查是否有"原文：xxx 译文：yyy"格式的行
            bool hasOriginalTranslationPair = lines.Any(line => line.Contains("原文：") && line.Contains("译文："));

            // 如果存在"原文：xxx 译文：yyy"格式，只保留译文部分
            if (hasOriginalTranslationPair && targetLang == "zh")
            {
                var resultText = string.Empty;
                foreach (var line in lines)
                {
                    if (line.Contains("译文："))
                    {
                        // 提取译文部分
                        var translationPart = line.Split(new[] { "译文：" }, 2, StringSplitOptions.None)[1].Trim();
                        if (!string.IsNullOrEmpty(translationPart))
                        {
                            resultText += translationPart + "\n";
                        }
                    }
                }
                if (!string.IsNullOrWhiteSpace(resultText))
                {
                    return resultText.Trim();
                }
            }

            // 处理常规行
            foreach (var line in lines)
            {
                var lineStripped = line.Trim();

                // 跳过只包含"原文："或"译文："的行
                if (lineStripped == "原文：" || lineStripped == "译文：")
                    continue;

                var processedLine = line;

                // 去除行首的"原文："或"译文："标记
                if (lineStripped.StartsWith("原文："))
                    continue;
                if (lineStripped.StartsWith("译文："))
                {
                    var index = line.IndexOf("译文：");
                    if (index >= 0)
                    {
                        processedLine = line.Substring(0, index) + line.Substring(index + "译文：".Length);
                        processedLine = processedLine.Trim();
                    }
                }

                // 去除行尾的"原文："或"译文："标记
                if (lineStripped.EndsWith("原文："))
                    processedLine = line.Replace("原文：", "").Trim();
                if (lineStripped.EndsWith("译文："))
                    processedLine = line.Replace("译文：", "").Trim();

                // 检查是否是提示性文本
                bool isPromptText = promptTexts.Any(promptText => 
                    lineStripped.Contains(promptText) || lineStripped.StartsWith(promptText));

                if (isPromptText)
                    continue;

                // 如果是空行，跳过
                if (string.IsNullOrWhiteSpace(processedLine))
                    continue;

                // 去除行中的"原文："和"译文："标记（针对混合在一行的情况）
                if (processedLine.Contains("原文：") && processedLine.Contains("译文：") && targetLang == "zh")
                {
                    // 提取译文部分
                    var parts = processedLine.Split(new[] { "译文：" }, 2, StringSplitOptions.None);
                    if (parts.Length > 1)
                    {
                        processedLine = parts[1].Trim();
                    }
                }

                filteredLines.Add(processedLine);
            }

            // 重新组合文本
            var filteredText = string.Join("\n", filteredLines);

            // 外语→中文翻译模式下的额外过滤
            if (targetLang == "zh")
            {
                // 去除常见的前缀短语
                var prefixesToRemove = new[]
                {
                    "以下是翻译：",
                    "翻译结果：",
                    "翻译如下：",
                    "译文如下：",
                    "翻译：",
                    "译文：",
                    "这是翻译：",
                    "这是译文：",
                    "以下是中文翻译：",
                    "中文翻译：",
                    "中文译文："
                };

                foreach (var prefix in prefixesToRemove)
                {
                    if (filteredText.StartsWith(prefix))
                    {
                        filteredText = filteredText.Substring(prefix.Length).Trim();
                    }
                }

                // 去除常见的后缀短语
                var suffixesToRemove = new[]
                {
                    "（以上是翻译结果）",
                    "（这是翻译结果）",
                    "（翻译完成）",
                    "（完成翻译）",
                    "（以上为翻译）",
                    "（以上为译文）"
                };

                foreach (var suffix in suffixesToRemove)
                {
                    if (filteredText.EndsWith(suffix))
                    {
                        filteredText = filteredText.Substring(0, filteredText.Length - suffix.Length).Trim();
                    }
                }
            }

            // 如果过滤后的文本为空，但原文不为空，则可能过滤过度
            // 在这种情况下，返回原始文本
            if (string.IsNullOrWhiteSpace(filteredText) && !string.IsNullOrWhiteSpace(text))
            {
                return text.Trim();
            }

            return filteredText;
        }

        /// <summary>
        /// 根据语言代码获取语言名称
        /// </summary>
        /// <param name="langCode">语言代码</param>
        /// <returns>语言名称</returns>
        protected virtual string GetLanguageName(string langCode)
        {
            var languageMap = new Dictionary<string, string>
            {
                {"zh", "中文"},
                {"en", "英文"},
                {"ja", "日文"},
                {"ko", "韩文"},
                {"fr", "法文"},
                {"de", "德文"},
                {"es", "西班牙文"},
                {"it", "意大利文"},
                {"ru", "俄文"},
                {"pt", "葡萄牙文"},
                {"nl", "荷兰文"},
                {"ar", "阿拉伯文"},
                {"th", "泰文"},
                {"vi", "越南文"}
            };

            return languageMap.TryGetValue(langCode, out var name) ? name : "未知语言";
        }

        /// <summary>
        /// 释放资源
        /// </summary>
        public void Dispose()
        {
            Dispose(true);
            GC.SuppressFinalize(this);
        }

        /// <summary>
        /// 释放资源的虚方法，供子类重写
        /// </summary>
        /// <param name="disposing">是否正在释放托管资源</param>
        protected virtual void Dispose(bool disposing)
        {
            // 基类默认不需要释放资源
        }
    }
}
