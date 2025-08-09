using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using Microsoft.Extensions.Logging;

namespace DocumentTranslator.Services.Translation
{
    /// <summary>
    /// 文档处理器，负责处理Word文档的翻译
    /// </summary>
    public class DocumentProcessor
    {
        private readonly TranslationService _translationService;
        private readonly ILogger<DocumentProcessor> _logger;
        private readonly TermExtractor _termExtractor;
        private bool _useTerminology = true;
        private bool _preprocessTerms = true;
        private bool _exportPdf = false;
        private string _sourceLang = "zh";
        private string _targetLang = "en";
        private bool _isCnToForeign = true;
        private string _outputFormat = "bilingual"; // 输出格式：bilingual（双语对照）或 translation_only（仅翻译结果）
        private Action<double, string> _progressCallback;
        private int _retryCount = 3;
        private int _retryDelay = 1000; // 毫秒

        // 数学公式正则表达式模式
        private readonly List<Regex> _latexPatterns = new List<Regex>
        {
            new Regex(@"\$\$(.*?)\$\$", RegexOptions.Singleline), // 行间公式 $$...$$
            new Regex(@"\$(.*?)\$", RegexOptions.Singleline),      // 行内公式 $...$
            new Regex(@"\\begin\{equation\}(.*?)\\end\{equation\}", RegexOptions.Singleline), // equation环境
            new Regex(@"\\begin\{align\}(.*?)\\end\{align\}", RegexOptions.Singleline),       // align环境
            new Regex(@"\\begin\{eqnarray\}(.*?)\\end\{eqnarray\}", RegexOptions.Singleline)  // eqnarray环境
        };

        public DocumentProcessor(TranslationService translationService, ILogger<DocumentProcessor> logger)
        {
            _translationService = translationService ?? throw new ArgumentNullException(nameof(translationService));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _termExtractor = new TermExtractor();
        }

        /// <summary>
        /// 设置进度回调函数
        /// </summary>
        public void SetProgressCallback(Action<double, string> callback)
        {
            _progressCallback = callback;
        }

        /// <summary>
        /// 设置翻译选项
        /// </summary>
        public void SetTranslationOptions(bool useTerminology = true, bool preprocessTerms = true,
            bool exportPdf = false, string sourceLang = "zh", string targetLang = "en", string outputFormat = "bilingual")
        {
            _useTerminology = useTerminology;
            _preprocessTerms = preprocessTerms;
            _exportPdf = exportPdf;
            _sourceLang = sourceLang;
            _targetLang = targetLang;
            _outputFormat = outputFormat;
            _isCnToForeign = sourceLang == "zh" || (sourceLang == "auto" && targetLang != "zh");

            _logger.LogInformation($"翻译方向: {(_isCnToForeign ? "中文→外语" : "外语→中文")}");
            _logger.LogInformation($"输出格式: {(_outputFormat == "bilingual" ? "双语对照" : "仅翻译结果")}");
        }

        /// <summary>
        /// 处理文档翻译
        /// </summary>
        public async Task<string> ProcessDocumentAsync(string filePath, string targetLanguage,
            Dictionary<string, string> terminology)
        {
            // 更新进度：开始处理
            UpdateProgress(0.01, "开始处理文档...");

            // 检查文件是否存在
            if (!File.Exists(filePath))
            {
                _logger.LogError($"文件不存在: {filePath}");
                throw new FileNotFoundException("文件不存在");
            }

            // 在程序根目录下创建输出目录
            var outputDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "输出");
            if (!Directory.Exists(outputDir))
            {
                Directory.CreateDirectory(outputDir);
            }

            // 获取输出路径，添加时间戳避免文件名冲突
            var fileName = Path.GetFileNameWithoutExtension(filePath);
            var originalExtension = Path.GetExtension(filePath).ToLower();
            var timeStamp = DateTime.Now.ToString("yyyyMMddHHmmss");

            // 确保输出格式为Word文档格式
            var outputExtension = ".docx";
            var outputFileName = $"{fileName}_带翻译_{timeStamp}{outputExtension}";
            var outputPath = Path.Combine(outputDir, outputFileName);

            _logger.LogInformation($"Word处理器输出配置:");
            _logger.LogInformation($"  原始文件: {filePath}");
            _logger.LogInformation($"  原始扩展名: {originalExtension}");
            _logger.LogInformation($"  输出扩展名: {outputExtension}");
            _logger.LogInformation($"  输出路径: {outputPath}");

            // 更新进度：检查文件
            UpdateProgress(0.05, "检查文件权限...");

            try
            {
                // 复制文件到输出目录
                File.Copy(filePath, outputPath, true);

                // 更新进度：开始翻译
                UpdateProgress(0.1, "开始翻译文档内容...");

                // 处理Word文档
                await ProcessWordDocumentAsync(outputPath, terminology);

                // 更新进度：完成
                UpdateProgress(1.0, "翻译完成");

                _logger.LogInformation($"文档翻译完成，输出路径: {outputPath}");
                return outputPath;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "文档处理失败");
                throw;
            }
        }

        /// <summary>
        /// 处理Word文档
        /// </summary>
        private async Task ProcessWordDocumentAsync(string filePath, Dictionary<string, string> terminology)
        {
            using var document = WordprocessingDocument.Open(filePath, true);
            var body = document.MainDocumentPart.Document.Body;

            // 获取所有段落
            var paragraphs = body.Descendants<Paragraph>().ToList();
            var totalParagraphs = paragraphs.Count;
            var processedParagraphs = 0;

            _logger.LogInformation($"开始处理 {totalParagraphs} 个段落");

            foreach (var paragraph in paragraphs)
            {
                try
                {
                    await ProcessParagraphAsync(paragraph, terminology);
                    processedParagraphs++;

                    // 更新进度
                    var progress = 0.1 + (0.8 * processedParagraphs / totalParagraphs);
                    UpdateProgress(progress, $"正在翻译段落 {processedParagraphs}/{totalParagraphs}");
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, $"处理段落失败，跳过该段落");
                }
            }

            // 处理表格
            var tables = body.Descendants<Table>().ToList();
            if (tables.Any())
            {
                _logger.LogInformation($"开始处理 {tables.Count} 个表格");

                for (int i = 0; i < tables.Count; i++)
                {
                    try
                    {
                        await ProcessTableAsync(tables[i], terminology);

                        // 更新进度
                        var progress = 0.9 + (0.05 * (i + 1) / tables.Count);
                        UpdateProgress(progress, $"正在翻译表格 {i + 1}/{tables.Count}");
                    }
                    catch (Exception ex)
                    {
                        _logger.LogWarning(ex, $"处理表格失败，跳过该表格");
                    }
                }
            }

            // 保存文档
            document.MainDocumentPart.Document.Save();
        }

        /// <summary>
        /// 处理段落
        /// </summary>
        private async Task ProcessParagraphAsync(Paragraph paragraph, Dictionary<string, string> terminology)
        {
            var runs = paragraph.Descendants<Run>().ToList();
            if (!runs.Any()) return;

            // 提取段落文本
            var paragraphText = string.Join("", runs.Select(r => r.InnerText));
            if (string.IsNullOrWhiteSpace(paragraphText)) return;

            // 保护数学公式
            var (protectedText, mathPlaceholders) = ProtectMathFormulas(paragraphText);

            // 术语预替换：与Excel一致，翻译前在文本中直接替换术语
            string toTranslate = protectedText;
            Dictionary<string, string> termsForTranslator = terminology;
            if (_useTerminology && _preprocessTerms && terminology != null && terminology.Count > 0)
            {
                // 规范方向：键始终是“源语言术语”
                var termsForReplace = terminology;
                if (!_isCnToForeign)
                {
                    var reversed = new Dictionary<string, string>(StringComparer.Ordinal);
                    foreach (var kv in terminology)
                    {
                        var src = kv.Value; // 外语
                        var dst = kv.Key;   // 中文
                        if (string.IsNullOrWhiteSpace(src)) continue;
                        if (!reversed.ContainsKey(src)) reversed[src] = dst;
                    }
                    termsForReplace = reversed;
                }

                var before = toTranslate;
                toTranslate = _termExtractor.ReplaceTermsInText(toTranslate, termsForReplace, _isCnToForeign);
                var beforeSnippet = before.Substring(0, Math.Min(80, before.Length));
                var afterSnippet = toTranslate.Substring(0, Math.Min(80, toTranslate.Length));
                _logger.LogInformation($"[Word] 术语预替换已执行（{(_isCnToForeign ? "中文→外语" : "外语→中文")}）：'{beforeSnippet}' -> '{afterSnippet}'");

                // 预处理后，发给翻译器的术语表置空，避免二次干预
                termsForTranslator = null;
            }

            // 翻译文本
            var translatedText = await TranslateTextWithRetryAsync(toTranslate, termsForTranslator);
            if (string.IsNullOrEmpty(translatedText)) return;

            // 恢复数学公式
            translatedText = RestoreMathFormulas(translatedText, mathPlaceholders);

            // 更新段落内容
            UpdateParagraphText(paragraph, paragraphText, translatedText);
        }

        /// <summary>
        /// 处理表格
        /// </summary>
        private async Task ProcessTableAsync(Table table, Dictionary<string, string> terminology)
        {
            var cells = table.Descendants<TableCell>().ToList();

            foreach (var cell in cells)
            {
                await ProcessTableCellAsync(cell, terminology);
            }
        }

        /// <summary>
        /// 处理表格单元格，避免重复翻译
        /// </summary>
        private async Task ProcessTableCellAsync(TableCell cell, Dictionary<string, string> terminology)
        {
            var paragraphs = cell.Descendants<Paragraph>().ToList();
            if (!paragraphs.Any()) return;

            // 提取单元格的所有文本内容
            var cellText = string.Join(" ", paragraphs.Select(p => p.InnerText)).Trim();
            if (string.IsNullOrWhiteSpace(cellText)) return;

            // 检查是否已经包含翻译内容（自检过滤）
            if (IsAlreadyTranslated(cellText))
            {
                _logger.LogInformation($"检测到单元格已包含翻译内容，跳过: {cellText.Substring(0, Math.Min(50, cellText.Length))}...");
                return;
            }

            // 保护数学公式
            var (protectedText, mathPlaceholders) = ProtectMathFormulas(cellText);

            // 翻译文本
            var translatedText = await TranslateTextWithRetryAsync(protectedText, terminology);
            if (string.IsNullOrEmpty(translatedText)) return;

            // 恢复数学公式
            translatedText = RestoreMathFormulas(translatedText, mathPlaceholders);

            // 更新单元格内容，只在第一个有内容的段落中添加翻译
            UpdateTableCellText(paragraphs, cellText, translatedText);
        }

        /// <summary>
        /// 保护数学公式
        /// </summary>
        private (string protectedText, Dictionary<string, string> placeholders) ProtectMathFormulas(string text)
        {
            var placeholders = new Dictionary<string, string>();
            var protectedText = text;
            var placeholderIndex = 0;

            foreach (var pattern in _latexPatterns)
            {
                var matches = pattern.Matches(protectedText);
                foreach (Match match in matches)
                {
                    var placeholder = $"__MATH_PH_{placeholderIndex}__";
                    placeholders[placeholder] = match.Value;
                    protectedText = protectedText.Replace(match.Value, placeholder);
                    placeholderIndex++;
                }
            }

            return (protectedText, placeholders);
        }

        /// <summary>
        /// 恢复数学公式
        /// </summary>
        private string RestoreMathFormulas(string text, Dictionary<string, string> placeholders)
        {
            foreach (var (placeholder, formula) in placeholders)
            {
                text = text.Replace(placeholder, formula);
            }
            return text;
        }

        /// <summary>
        /// 带重试机制的翻译
        /// </summary>
        private async Task<string> TranslateTextWithRetryAsync(string text, Dictionary<string, string> terminology)
        {
            // 规范术语映射方向：确保键总是“源语言术语”，值为“目标语言术语”
            // - 中文→外语：术语库本身是 {中文: 外语}，可直接使用
            // - 外语→中文：需反转为 {外语: 中文}
            Dictionary<string, string> termsForTranslator = terminology;
            if (_useTerminology && terminology != null && terminology.Count > 0 && !_isCnToForeign)
            {
                var reversed = new Dictionary<string, string>(StringComparer.Ordinal);
                foreach (var kv in terminology)
                {
                    var src = kv.Value; // 外语
                    var dst = kv.Key;   // 中文
                    if (string.IsNullOrWhiteSpace(src)) continue;
                    if (!reversed.ContainsKey(src)) reversed[src] = dst;
                }
                termsForTranslator = reversed;
            }

            for (int attempt = 0; attempt < _retryCount; attempt++)
            {
                try
                {
                    // 使用规范后的术语映射
                    var termsForTranslatorLocal = termsForTranslator;
                    return await _translationService.TranslateTextAsync(text, termsForTranslatorLocal, _sourceLang, _targetLang);
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, $"翻译失败，尝试 {attempt + 1}/{_retryCount}");

                    if (attempt == _retryCount - 1)
                    {
                        _logger.LogError("翻译重试次数已用完，跳过该文本");
                        return string.Empty;
                    }

                    await Task.Delay(_retryDelay);
                }
            }

            return string.Empty;
        }

        /// <summary>
        /// 更新段落文本
        /// </summary>
        private void UpdateParagraphText(Paragraph paragraph, string originalText, string translatedText)
        {
            var clean = CleanTranslationText(translatedText);

            if (_outputFormat == "bilingual")
            {
                // 保留原段落所有格式与内容，仅在末尾追加换行 + 译文
                paragraph.AppendChild(new Run(new Break()));

                var translatedRun = new Run(new Text(clean));
                if (translatedRun.RunProperties == null)
                    translatedRun.RunProperties = new RunProperties();
                translatedRun.RunProperties.Color = new DocumentFormat.OpenXml.Wordprocessing.Color() { Val = "0066CC" };
                paragraph.AppendChild(translatedRun);
            }
            else
            {
                // 仅翻译结果模式：替换原内容
                var runs = paragraph.Descendants<Run>().ToList();
                foreach (var run in runs) run.Remove();
                var newRun = new Run(new Text(clean));
                paragraph.AppendChild(newRun);
            }
        }

        /// <summary>
        /// 更新进度
        /// </summary>
        private void UpdateProgress(double progress, string message)
        {
            try
            {
                _progressCallback?.Invoke(progress, message);
                _logger.LogInformation($"进度: {progress:P1} - {message}");
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "更新进度失败");
            }
        }

        /// <summary>
        /// 清洗译文，移除前缀/代码块/说明等，返回纯净译文
        /// </summary>
        private string CleanTranslationText(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return string.Empty;
            var s = text.Trim();

            s = Regex.Replace(s, @"^(译文|翻译|Translation|Translated|Result|输出|Output)\s*[:：]-?\s*", string.Empty, RegexOptions.IgnoreCase);
            s = Regex.Replace(s, @"^```[a-zA-Z0-9_-]*\s*", string.Empty);
            s = Regex.Replace(s, @"```\s*$", string.Empty);
            s = s.Trim().Trim('"', '\'', '“', '”', '‘', '’');
            s = Regex.Replace(s, @"(\n|\r)*【?注:.*$", string.Empty, RegexOptions.IgnoreCase);
            s = Regex.Replace(s, @"(\n|\r)*\(?Translated by.*$", string.Empty, RegexOptions.IgnoreCase);

            var lines = s.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
            var compact = new List<string>();
            foreach (var line in lines)
            {
                var t = line.Trim();
                if (t.Length == 0) continue;
                compact.Add(t);
            }
            return string.Join("\n", compact);
        }

        /// <summary>
        /// 检查文本是否已经包含翻译内容（自检过滤）
        /// </summary>
        private bool IsAlreadyTranslated(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return false;

            // 检查是否包含常见的双语对照模式特征
            var lines = text.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);

            // 如果只有一行，检查是否包含中英文混合（可能已翻译）
            if (lines.Length == 1)
            {
                return ContainsMixedLanguages(text);
            }

            // 如果有多行，检查是否符合双语对照格式
            if (lines.Length >= 2)
            {
                // 检查是否有明显的原文-译文模式
                for (int i = 0; i < lines.Length - 1; i++)
                {
                    var currentLine = lines[i].Trim();
                    var nextLine = lines[i + 1].Trim();

                    if (!string.IsNullOrEmpty(currentLine) && !string.IsNullOrEmpty(nextLine))
                    {
                        // 检查是否是中文-英文或英文-中文的组合
                        if (IsChineseText(currentLine) && IsEnglishText(nextLine) ||
                            IsEnglishText(currentLine) && IsChineseText(nextLine))
                        {
                            return true;
                        }
                    }
                }
            }

            return false;
        }

        /// <summary>
        /// 检查文本是否包含混合语言
        /// </summary>
        private bool ContainsMixedLanguages(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return false;

            bool hasChinese = false;
            bool hasEnglish = false;

            foreach (char c in text)
            {
                if (c >= 0x4e00 && c <= 0x9fff) // 中文字符范围
                {
                    hasChinese = true;
                }
                else if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'))
                {
                    hasEnglish = true;
                }

                if (hasChinese && hasEnglish)
                {
                    return true;
                }
            }

            return false;
        }

        /// <summary>
        /// 检查文本是否主要是中文
        /// </summary>
        private bool IsChineseText(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return false;

            int chineseCount = 0;
            int totalChars = 0;

            foreach (char c in text)
            {
                if (!char.IsWhiteSpace(c) && !char.IsPunctuation(c))
                {
                    totalChars++;
                    if (c >= 0x4e00 && c <= 0x9fff)
                    {
                        chineseCount++;
                    }
                }
            }

            return totalChars > 0 && (double)chineseCount / totalChars > 0.5;
        }

        /// <summary>
        /// 检查文本是否主要是英文
        /// </summary>
        private bool IsEnglishText(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return false;

            int englishCount = 0;
            int totalChars = 0;

            foreach (char c in text)
            {
                if (!char.IsWhiteSpace(c) && !char.IsPunctuation(c))
                {
                    totalChars++;
                    if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'))
                    {
                        englishCount++;
                    }
                }
            }

            return totalChars > 0 && (double)englishCount / totalChars > 0.5;
        }

        /// <summary>
        /// 更新表格单元格文本，避免重复翻译
        /// </summary>
        private void UpdateTableCellText(List<Paragraph> paragraphs, string originalText, string translatedText)
        {
            if (!paragraphs.Any()) return;

            // 找到第一个有内容的段落
            var targetParagraph = paragraphs.FirstOrDefault(p => !string.IsNullOrWhiteSpace(p.InnerText)) ?? paragraphs[0];
            var clean = CleanTranslationText(translatedText);

            if (_outputFormat == "bilingual")
            {
                // 保留原段落，只在第一个非空段落后追加译文
                targetParagraph.AppendChild(new Run(new Break()));
                var translatedRun = new Run(new Text(clean));
                if (translatedRun.RunProperties == null)
                    translatedRun.RunProperties = new RunProperties();
                translatedRun.RunProperties.Color = new DocumentFormat.OpenXml.Wordprocessing.Color() { Val = "0066CC" };
                targetParagraph.AppendChild(translatedRun);
            }
            else
            {
                // 仅翻译结果模式：清空所有段落，只在第一个段落写入译文
                foreach (var p in paragraphs)
                {
                    var runs = p.Descendants<Run>().ToList();
                    foreach (var run in runs) run.Remove();
                }
                var newRun = new Run(new Text(clean));
                targetParagraph.AppendChild(newRun);
            }
        }
    }
}
