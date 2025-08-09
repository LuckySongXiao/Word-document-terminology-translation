using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Logging;
using OfficeOpenXml;

namespace DocumentTranslator.Services.Translation
{
    /// <summary>
    /// Excel文档处理器，负责处理Excel文档的翻译
    /// </summary>
    public class ExcelProcessor
    {
        private readonly TranslationService _translationService;
        private readonly ILogger<ExcelProcessor> _logger;
        private readonly TermExtractor _termExtractor;
        private bool _useTerminology = true;
        private bool _preprocessTerms = true;
        private string _sourceLang = "zh";
        private string _targetLang = "en";
        private string _targetLanguageName = "英语";
        private string _terminologyLanguageName = "英语"; // 用于术语库检索的语言键（可由名称/代码归一化）
        private bool _isCnToForeign = true;
        private string _outputFormat = "bilingual"; // 输出格式：bilingual（双语对照）或 translation_only（仅翻译结果）
        private Action<double, string> _progressCallback;
        private int _retryCount = 3;
        private int _retryDelay = 1000; // 毫秒

        /// <summary>
        /// 解析术语库使用的语言键：
        /// - 中文→外语：直接使用 UI 传入的目标语言名称（如“英语”）
        /// - 外语→中文：根据源语言代码映射到术语库顶层键（如 en→“英语”）
        /// </summary>
        private string ResolveTerminologyLanguageName(string targetLanguageName, string targetLangCode)
        {
            if (_isCnToForeign)
                return targetLanguageName;

            // 外语→中文：根据源语言代码映射
            var codeToName = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
            {
                ["en"] = "英语",
                ["ja"] = "日语",
                ["ko"] = "韩语",
                ["fr"] = "法语",
                ["de"] = "德语",
                ["es"] = "西班牙语",
                ["it"] = "意大利语",
                ["ru"] = "俄语",
            };
            if (codeToName.TryGetValue(_sourceLang ?? string.Empty, out var name))
                return name;

            // 兜底：返回传入名称以避免空值
            return targetLanguageName;
        }


        public ExcelProcessor(TranslationService translationService, ILogger<ExcelProcessor> logger)
        {
            _translationService = translationService ?? throw new ArgumentNullException(nameof(translationService));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _termExtractor = new TermExtractor();

            // 设置EPPlus许可证上下文为非商业用途
            ExcelPackage.LicenseContext = LicenseContext.NonCommercial;
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
            string sourceLang = "zh", string targetLang = "en", string outputFormat = "bilingual")
        {
            _useTerminology = useTerminology;
            _preprocessTerms = preprocessTerms;
            _sourceLang = sourceLang;
            _targetLang = targetLang;
            _outputFormat = outputFormat;
            _isCnToForeign = sourceLang == "zh" || (sourceLang == "auto" && targetLang != "zh");

            _logger.LogInformation($"翻译方向: {(_isCnToForeign ? "中文→外语" : "外语→中文")}");
            _logger.LogInformation($"输出格式: {(_outputFormat == "bilingual" ? "双语对照" : "仅翻译结果")}");



        }

        /// <summary>
        /// 处理Excel文档翻译
        /// </summary>
        public async Task<string> ProcessDocumentAsync(string filePath, string targetLanguage,
            Dictionary<string, string> terminology)
        {
            // 更新进度：开始处理
            UpdateProgress(0.01, "开始处理Excel文档...");

            // 检查文件是否存在
            if (!File.Exists(filePath))
            {
                _logger.LogError($"文件不存在: {filePath}");
                throw new FileNotFoundException("文件不存在");
            }

            // 检查文件扩展名
            var extension = Path.GetExtension(filePath).ToLower();
            if (extension != ".xlsx" && extension != ".xls")
            {
                throw new ArgumentException($"不支持的Excel文件格式: {extension}，仅支持 .xlsx 和 .xls 格式");
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

            // 保持原始文件的扩展名，确保输出格式与输入格式一致
            var outputExtension = originalExtension == ".xls" ? ".xls" : ".xlsx";
            var outputFileName = $"{fileName}_带翻译_{timeStamp}{outputExtension}";
            var outputPath = Path.Combine(outputDir, outputFileName);

            _logger.LogInformation($"Excel处理器输出配置:");
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
                UpdateProgress(0.1, "开始翻译Excel内容...");

                // 处理Excel文档
                _targetLanguageName = targetLanguage;
                _terminologyLanguageName = ResolveTerminologyLanguageName(_targetLanguageName, _targetLang);
                var termsCount = _termExtractor.GetTermsForLanguage(_terminologyLanguageName)?.Count ?? 0;
                _logger.LogInformation($"术语库语言键: '{_terminologyLanguageName}', 词条数: {termsCount}");
                await ProcessExcelDocumentAsync(outputPath, terminology);

                // 更新进度：完成
                UpdateProgress(1.0, "翻译完成");

                _logger.LogInformation($"Excel文档翻译完成，输出路径: {outputPath}");
                return outputPath;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Excel文档处理失败");
                throw;
            }
        }

        /// <summary>
        /// 处理Excel文档
        /// </summary>
        private async Task ProcessExcelDocumentAsync(string filePath, Dictionary<string, string> terminology)
        {
            using var package = new ExcelPackage(new FileInfo(filePath));
            var worksheets = package.Workbook.Worksheets;
            var totalWorksheets = worksheets.Count;

            _logger.LogInformation($"开始处理 {totalWorksheets} 个工作表");

            for (int i = 0; i < totalWorksheets; i++)
            {
                var worksheet = worksheets[i];
                try
                {
                    await ProcessWorksheetAsync(worksheet, terminology);

                    // 更新进度
                    var progress = 0.1 + (0.8 * (i + 1) / totalWorksheets);
                    UpdateProgress(progress, $"正在翻译工作表 {i + 1}/{totalWorksheets}: {worksheet.Name}");
                }
                catch (Exception ex)
                {
                    _logger.LogWarning(ex, $"处理工作表失败，跳过该工作表: {worksheet.Name}");
                }
            }

            // 保存文档
            await package.SaveAsync();
        }

        /// <summary>
        /// 处理工作表
        /// </summary>
        private async Task ProcessWorksheetAsync(ExcelWorksheet worksheet, Dictionary<string, string> terminology)
        {
            if (worksheet.Dimension == null)
            {
                _logger.LogInformation($"工作表 {worksheet.Name} 为空，跳过处理");
                return;
            }

            var startRow = worksheet.Dimension.Start.Row;
            var endRow = worksheet.Dimension.End.Row;
            var startCol = worksheet.Dimension.Start.Column;
            var endCol = worksheet.Dimension.End.Column;

            _logger.LogInformation($"处理工作表 {worksheet.Name}，范围: {startRow}-{endRow} 行, {startCol}-{endCol} 列");

            var totalCells = (endRow - startRow + 1) * (endCol - startCol + 1);
            var processedCells = 0;

            for (int row = startRow; row <= endRow; row++)
            {
                for (int col = startCol; col <= endCol; col++)
                {
                    try
                    {
                        await ProcessCellAsync(worksheet, row, col, terminology);
                        processedCells++;

                        // 每处理100个单元格更新一次进度
                        if (processedCells % 100 == 0)
                        {
                            var cellProgress = (double)processedCells / totalCells * 0.1;
                            UpdateProgress(0.1 + cellProgress, $"处理单元格 {processedCells}/{totalCells}");
                        }
                    }
                    catch (Exception ex)
                    {
                        _logger.LogWarning(ex, $"处理单元格失败，跳过该单元格: {row},{col}");
                    }
                }
            }
        }

        /// <summary>
        /// 处理单元格
        /// </summary>
        private async Task ProcessCellAsync(ExcelWorksheet worksheet, int row, int col, Dictionary<string, string> terminology)
        {
            // 用于读取/写入内容的“单一单元格”（左上角）
            var contentCell = worksheet.Cells[row, col];
            // 用于样式应用的区域（合并单元格时为整块区域，否则为单一单元格）
            ExcelRange styleRange = contentCell;

            // 合并单元格处理：仅在合并区域左上角单元格执行翻译与写入
            if (contentCell.Merge && worksheet.MergedCells != null && worksheet.MergedCells.Count > 0)
            {
                ExcelAddress mergedRange = null;
                foreach (var mergedAddress in worksheet.MergedCells)
                {
                    var rng = new ExcelAddress(mergedAddress);
                    if (row >= rng.Start.Row && row <= rng.End.Row && col >= rng.Start.Column && col <= rng.End.Column)
                    {
                        mergedRange = rng;
                        break;
                    }
                }
                if (mergedRange != null)
                {
                    // 不是左上角的单元格就跳过，避免重复处理
                    if (!(row == mergedRange.Start.Row && col == mergedRange.Start.Column))
                    {
                        return;
                    }
                    styleRange = worksheet.Cells[mergedRange.Start.Row, mergedRange.Start.Column, mergedRange.End.Row, mergedRange.End.Column];
                }
            }

            // 读取原始值（保持类型）
            var raw = contentCell.Value;
            if (raw == null)
                return;

            // 跳过公式、纯数值/日期/时间等非文本内容
            if (!string.IsNullOrEmpty(contentCell.Formula))
                return;
            if (raw is double || raw is float || raw is decimal || raw is int || raw is long || raw is short)
                return;
            if (raw is DateTime || raw is TimeSpan)
                return;

            var cellText = raw.ToString();
            if (string.IsNullOrWhiteSpace(cellText))
                return;

            // 短标点/代码类文本跳过（如“/”, "-", "N/A"等）
            if (ShouldSkipCellText(cellText))
                return;

            // 检查是否已经包含翻译内容（自检过滤）
            if (IsAlreadyTranslated(cellText))
            {
                _logger.LogDebug($"检测到单元格已包含翻译内容，跳过: {cellText.Substring(0, Math.Min(50, cellText.Length))}...");
                return;
            }

            // 术语预处理：根据全局设置与目标语言，提取本单元格相关术语
            // 规范术语映射方向：确保键总是“源语言术语”，值为“目标语言术语”
            Dictionary<string, string> termsToUse = terminology ?? new Dictionary<string, string>();
            if (_useTerminology && termsToUse.Count > 0 && !_isCnToForeign)
            {
                var reversed = new Dictionary<string, string>(StringComparer.Ordinal);
                foreach (var kv in termsToUse)
                {
                    var src = kv.Value; // 外语
                    var dst = kv.Key;   // 中文
                    if (string.IsNullOrWhiteSpace(src)) continue;
                    if (!reversed.ContainsKey(src)) reversed[src] = dst;
                }
                termsToUse = reversed;
            }
            if (_useTerminology)
            {
                var extracted = _termExtractor.ExtractRelevantTerms(cellText, _terminologyLanguageName, _sourceLang, _targetLang);
                if (extracted != null && extracted.Any())
                {
                    // 日志：术语提取结果（仅示例前3项）
                    var samplePairs = string.Join(", ", extracted.Take(3).Select(kv => $"{kv.Key}->{kv.Value}"));
                    _logger.LogInformation($"术语提取：匹配 {extracted.Count} 个术语，示例: {samplePairs}");

                    // 合并外部传入的术语与提取术语
                    foreach (var kv in extracted)
                    {
                        if (!termsToUse.ContainsKey(kv.Key)) termsToUse[kv.Key] = kv.Value;
                    }

                    if (_preprocessTerms)
                    {
                        // 让长术语优先匹配（后续翻译器会按长度降序处理）
                        termsToUse = _termExtractor.PreprocessTerms(termsToUse).ToDictionary(k => k.Key, v => v.Value);
                        _logger.LogInformation($"术语预处理已启用：将优先匹配长术语（当前可用术语 {termsToUse.Count} 个）");
                    }
                }
                else
                {
                    if (_preprocessTerms)
                    {
                        _logger.LogInformation("术语预处理：本单元格未匹配到术语，跳过预替换");
                        var textSnippet = (cellText ?? string.Empty).Trim();
                        if (textSnippet.Length > 120) textSnippet = textSnippet.Substring(0, 120) + "...";
                        _logger.LogInformation($"术语预处理：文本片段: '{textSnippet}'");
                    }

                    // 若未命中提取，且开启预处理，退化为对整本术语库进行直接预替换（可能更慢，但覆盖更全）
                    if (_preprocessTerms)
                    {
                        var fullDict = _termExtractor.GetTermsForLanguage(_terminologyLanguageName);
                        if (fullDict != null && fullDict.Count > 0)
                        {
                            foreach (var kv in fullDict)
                            {
                                if (!termsToUse.ContainsKey(kv.Key)) termsToUse[kv.Key] = kv.Value;
                            }
                            _logger.LogInformation($"术语预处理：未命中提取，改用全量术语库（{fullDict.Count} 条）进行预替换");
                        }
                    }
                }
            }

            // 若仍没有任何术语可用，记录一次说明，便于诊断
            if (_useTerminology && _preprocessTerms && (termsToUse == null || !termsToUse.Any()))
            {
                _logger.LogInformation("术语预处理：本单元格未找到任何可用于替换的术语，直接进入翻译");
                var textSnippet2 = (cellText ?? string.Empty).Trim();
                if (textSnippet2.Length > 120) textSnippet2 = textSnippet2.Substring(0, 120) + "...";
                _logger.LogInformation($"术语预处理：文本片段: '{textSnippet2}'");
            }

            // 翻译文本（优先处理中文单位 → 英文单位）
            string translatedText;
            if (TryTranslateStandaloneUnit(cellText, out var unitTranslation))
            {
                translatedText = unitTranslation;
            }
            else
            {
                var normalized = NormalizeUnitsNearNumbers(cellText);

                // 术语预替换：像 Word 一样在翻译前对文本进行术语预处理（直接替换为目标术语）
                string toTranslate = normalized;
                if (_useTerminology && _preprocessTerms && termsToUse != null && termsToUse.Any())
                {
                    var before = normalized;
                    toTranslate = _termExtractor.ReplaceTermsInText(normalized, termsToUse, _isCnToForeign);
                    var beforeSnippet = before.Substring(0, Math.Min(80, before.Length));
                    var afterSnippet = toTranslate.Substring(0, Math.Min(80, toTranslate.Length));
                    _logger.LogInformation($"术语预替换已执行（{(_isCnToForeign ? "中文→外语" : "外语→中文")}）：'{beforeSnippet}' -> '{afterSnippet}'");
                }

                // 若已预替换，则不再向翻译器传入术语表，避免二次干预；否则保留术语表供翻译器做占位符策略
                var terminologyForTranslator = (_useTerminology && !_preprocessTerms) ? termsToUse : null;

                translatedText = await TranslateTextWithRetryAsync(toTranslate, terminologyForTranslator);
                if (string.IsNullOrEmpty(translatedText))
                    return;
            }

            // 更新单元格（若是合并区域，则对整个区域开启WrapText；仅在左上角写入内容）
            UpdateCellText(styleRange, cellText, translatedText);
        }

            // 简单启发式：跳过无需翻译的短文本/符号/代码样式内容
            static bool ShouldSkipCellText(string s)
            {
                if (string.IsNullOrWhiteSpace(s)) return true;
                var t = s.Trim();
                // 单字符：若为中文或单位名，不跳过，避免漏译“台”“件”“米”等
                if (t.Length == 1)
                {
                    // 在单位词典中，必须翻译
                    if (ZhUnitMap.ContainsKey(t)) return false;
                    // 单个中文汉字，保留给后续翻译流程
                    if (System.Text.RegularExpressions.Regex.IsMatch(t, @"^[\u4e00-\u9fff]$")) return false;
                    // 其它单字符（多为符号）跳过
                    return true;
                }
                // 常见跳过标记
                string[] skipTokens = { "N/A", "NA", "--", "-", "/", "\\", "#", "*", "√", "×", "—" };
                if (Array.Exists(skipTokens, k => string.Equals(k, t, StringComparison.OrdinalIgnoreCase))) return true;
                // 纯数字或数字+单位（如 12, 3.14, 100%）
                if (System.Text.RegularExpressions.Regex.IsMatch(t, @"^[0-9]+(\.[0-9]+)?%?$")) return true;
                return false;
            }


        /// <summary>
        /// 带重试机制的翻译
        /// </summary>
        private async Task<string> TranslateTextWithRetryAsync(string text, Dictionary<string, string> terminology)
        {
            // 构建严格提示词：仅返回译文、保持占位符、保留数字单位、禁止解释
            string basePrompt = BuildExcelPrompt();

            for (int attempt = 0; attempt < _retryCount; attempt++)
            {
                try
                {
                    var prompt = attempt == 0 ? basePrompt : basePrompt + "\n请注意：仅输出目标语言译文，不要包含原文、括号注释或任何额外解释。保持 [[T001]] 这类占位符原样。";
                    var result = await _translationService.TranslateTextAsync(text, terminology, _sourceLang, _targetLang, prompt);

                    // 译文净化与质量校验
                    var clean = CleanTranslationText(result);
                    if (string.IsNullOrWhiteSpace(clean))
                        throw new Exception("译文为空");

                    // 若译文与原文在去空白后一致，则视为无效
                    if (string.Equals(RemoveSpaces(text), RemoveSpaces(clean), StringComparison.Ordinal))
                        throw new Exception("译文与原文近似一致");

                    return clean;
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

        private string BuildExcelPrompt()
        {
            return "请将以下Excel单元格文本精准翻译为目标语言，严格要求：\n" +
                   "1) 仅返回纯净译文，不要原文，不要解释或附加说明；\n" +
                   "2) 保持数字、量纲、单位、公式、代码与占位符(如 [[T001]])原样；\n" +
                   "3) 保持简洁与专业，不增加括号注释；\n" +
                   "4) 名称/部件号/代号等不应意译；\n" +
                   "5) 若术语存在，请优先采用术语库对应译法。";
        }

        // 简单单位词典（可扩展）
        private static readonly Dictionary<string, string> ZhUnitMap = new(StringComparer.Ordinal)
        {
            ["台"] = "units",
            ["只"] = "pcs",
            ["件"] = "pcs",
            ["个"] = "pcs",
            ["套"] = "sets",
            ["桶"] = "barrels",
            ["吨"] = "tons",
            ["千克"] = "kg",
            ["公斤"] = "kg",
            ["克"] = "g",
            ["米"] = "m",
            ["厘米"] = "cm",
            ["毫米"] = "mm",
            ["升"] = "L",
            ["毫升"] = "mL",
            ["小时"] = "h",
            ["分钟"] = "min",
            ["秒"] = "s"
        };

        // 若单元格为“纯单位词”或“纯数字+单位”，直接进行单位翻译
        private static bool TryTranslateStandaloneUnit(string text, out string translated)
        {
            translated = null;
            if (string.IsNullOrWhiteSpace(text)) return false;
            var t = text.Trim();
            // 纯数字直接返回 false（不翻译）
            if (System.Text.RegularExpressions.Regex.IsMatch(t, @"^[0-9]+(\.[0-9]+)?$")) return false;

            // 纯单位词
            if (ZhUnitMap.TryGetValue(t, out var unit))
            {
                translated = unit;
                return true;
            }

            // 数字 + 单位（可包含空格）
            var m = System.Text.RegularExpressions.Regex.Match(t, @"^([0-9]+(?:\.[0-9]+)?)\s*([一二三四五六七八九十百千万亿]?)([台只件个套桶吨千克公斤克米厘米毫米升毫升小时分钟秒])$");
            if (m.Success)
            {
                var number = m.Groups[1].Value;
                var zhUnit = m.Groups[3].Value;
                if (ZhUnitMap.TryGetValue(zhUnit, out var enUnit))
                {
                    translated = $"{number} {enUnit}";
                    return true;
                }
            }
            return false;
        }

        // 规范化：将“数字+中文单位”附近加空格，便于LLM理解，不改变纯数字
        private static string NormalizeUnitsNearNumbers(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return text;
            var s = text;
            // 例："10台设备" → "10 台设备"；"5吨" → "5 吨"
            s = System.Text.RegularExpressions.Regex.Replace(s, @"([0-9]+(?:\.[0-9]+)?)([台只件个套桶吨千克公斤克米厘米毫米升毫升小时分钟秒])", "$1 $2");
            return s;
        }


        private static string RemoveSpaces(string s) => string.IsNullOrEmpty(s) ? s : System.Text.RegularExpressions.Regex.Replace(s, @"\s+", "");

        /// <summary>
        /// 更新单元格文本
        /// </summary>
        private void UpdateCellText(ExcelRange cell, string originalText, string translatedText)
        {
            // 纯净化译文，去除模型可能添加的多余标记
            var clean = CleanTranslationText(translatedText);

            // 获取顶端单元格（若为合并区域则取左上角单元格），用于写入内容
            var ws = cell.Worksheet;
            var topLeftCell = ws.Cells[cell.Start.Row, cell.Start.Column];

            if (_outputFormat == "bilingual")
            {
                // 双语对照模式：使用富文本分行显示，增强可读性
                // 原文保留原样；译文使用斜体和颜色区分
                try
                {
                    topLeftCell.RichText.Clear();
                    var rt1 = topLeftCell.RichText.Add(originalText ?? string.Empty);
                    // 颜色与字体保持默认，减少对原始视觉的干扰
                    topLeftCell.RichText.Add(Environment.NewLine);
                    var rt2 = topLeftCell.RichText.Add(clean);
                    rt2.Italic = true;
                    // 轻微区分色（深蓝），避免打印可读性问题
                    rt2.Color = System.Drawing.Color.FromArgb(0, 102, 204);
                }
                catch
                {
                    // 若富文本写入失败，则退回到简单换行文本
                    topLeftCell.Value = $"{originalText}{Environment.NewLine}{clean}";
                }
            }
            else
            {
                // 仅翻译结果模式：只写入纯净译文
                topLeftCell.Value = clean;
            }

            // 开启自动换行，确保“译文换行”在单元格内显示为新行
            var style = cell.Style; // 对整个区域（含合并区域）生效
            style.WrapText = true;
            style.ShrinkToFit = false;
            style.VerticalAlignment = OfficeOpenXml.Style.ExcelVerticalAlignment.Top;
        }

        /// <summary>
        /// 清洗模型返回的译文，移除前后缀、代码块、无用标记与多余空白，返回“纯净译文”
        /// </summary>
        private string CleanTranslationText(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return string.Empty;
            var s = text.Trim();

            // 1) 去除常见前缀
            // 如："译文:", "翻译:", "Translation:", "Translated:", "Result:" 等
            s = Regex.Replace(s, @"^(译文|翻译|Translation|Translated|Result|输出|Output)\s*[:：]-?\s*", string.Empty, RegexOptions.IgnoreCase);

            // 2) 去除Markdown代码块标记
            // ```xxx ... ``` 或 ``` ... ```
            s = Regex.Replace(s, @"^```[a-zA-Z0-9_-]*\s*", string.Empty);
            s = Regex.Replace(s, @"```\s*$", string.Empty);

            // 3) 去除多余的行首尾引号和括号
            s = s.Trim().Trim('"', '\'', '“', '”', '‘', '’');

            // 4) 去除常见提示性后缀（例如模型附加的说明文字）
            s = Regex.Replace(s, @"(\n|\r)*【?注:.*$", string.Empty, RegexOptions.IgnoreCase);
            s = Regex.Replace(s, @"(\n|\r)*\(?Translated by.*$", string.Empty, RegexOptions.IgnoreCase);

            // 5) 统一换行，去掉多余空白行
            var lines = s.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
            var compact = new List<string>();
            foreach (var line in lines)
            {
                var t = line.Trim();
                if (t.Length == 0) continue; // 去掉空行
                compact.Add(t);
            }
            s = string.Join("\n", compact);

            return s;
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
        /// 检查文本是否已经包含翻译内容（自检过滤）
        /// </summary>
        private bool IsAlreadyTranslated(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return false;

            // 去除常见的“已翻译标记”与噪声
            var s = CleanTranslationText(text);

            // 检查是否包含常见的双语对照模式特征
            var lines = s.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);

            // 如果只有一行，避免过度敏感：不再仅凭中英混排判定已翻译，防止漏译
            if (lines.Length == 1)
            {
                return false;
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

            // 辅助：粗略判断中文/英文占比
            static bool IsChineseText(string s) => !string.IsNullOrEmpty(s) && s.Any(c => c >= 0x4e00 && c <= 0x9fff);
            static bool IsEnglishText(string s) => !string.IsNullOrEmpty(s) && s.Any(c => (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z'));

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
    }
}
