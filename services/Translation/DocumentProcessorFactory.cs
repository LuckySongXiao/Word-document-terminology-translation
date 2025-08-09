using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace DocumentTranslator.Services.Translation
{
    /// <summary>
    /// 文档处理器工厂，根据文件类型创建相应的处理器
    /// </summary>
    public class DocumentProcessorFactory
    {
        private readonly TranslationService _translationService;
        private readonly ILogger<DocumentProcessorFactory> _logger;
        private readonly ILoggerFactory _loggerFactory;

        public DocumentProcessorFactory(TranslationService translationService, ILogger<DocumentProcessorFactory> logger, ILoggerFactory loggerFactory)
        {
            _translationService = translationService ?? throw new ArgumentNullException(nameof(translationService));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _loggerFactory = loggerFactory ?? throw new ArgumentNullException(nameof(loggerFactory));
        }

        /// <summary>
        /// 根据文件类型创建相应的处理器
        /// </summary>
        /// <param name="filePath">文件路径</param>
        /// <returns>文档处理器接口</returns>
        /// <exception cref="ArgumentException">不支持的文件类型</exception>
        public IDocumentProcessor CreateProcessor(string filePath)
        {
            if (string.IsNullOrWhiteSpace(filePath))
                throw new ArgumentException("文件路径不能为空", nameof(filePath));

            if (!File.Exists(filePath))
                throw new FileNotFoundException($"文件不存在: {filePath}");

            var extension = Path.GetExtension(filePath).ToLower();
            var fileName = Path.GetFileName(filePath);
            var fileSize = new FileInfo(filePath).Length;

            _logger.LogInformation($"=== 文档处理器创建诊断 ===");
            _logger.LogInformation($"文件路径: {filePath}");
            _logger.LogInformation($"文件名: {fileName}");
            _logger.LogInformation($"文件扩展名: {extension}");
            _logger.LogInformation($"文件大小: {fileSize} 字节 ({fileSize / 1024.0:F2} KB)");

            // 验证文件内容类型（通过文件头）
            try
            {
                var actualFileType = DetectFileTypeByContent(filePath);
                _logger.LogInformation($"通过文件头检测的实际类型: {actualFileType}");

                if (actualFileType != extension)
                {
                    _logger.LogWarning($"⚠️ 文件扩展名与实际内容不匹配！扩展名: {extension}, 实际类型: {actualFileType}");
                }
            }
            catch (Exception ex)
            {
                _logger.LogWarning($"无法检测文件内容类型: {ex.Message}");
            }

            var processorType = extension switch
            {
                ".docx" => "Word文档处理器",
                ".xlsx" or ".xls" => "Excel文档处理器",
                ".pdf" => "PDF文档处理器（未实现）",
                ".pptx" => "PowerPoint文档处理器（未实现）",
                _ => "未知处理器"
            };

            _logger.LogInformation($"选择的处理器类型: {processorType}");
            _logger.LogInformation($"=== 诊断信息结束 ===");

            return extension switch
            {
                ".docx" => CreateWordProcessor(),
                ".xlsx" or ".xls" => CreateExcelProcessor(),
                ".pdf" => throw new NotImplementedException("PDF处理器尚未实现"),
                ".pptx" => throw new NotImplementedException("PowerPoint处理器尚未实现"),
                _ => throw new ArgumentException($"不支持的文件类型: {extension}，目前仅支持 .docx, .xlsx, .xls 文件")
            };
        }

        /// <summary>
        /// 通过文件头检测实际文件类型
        /// </summary>
        private string DetectFileTypeByContent(string filePath)
        {
            using var stream = File.OpenRead(filePath);
            var buffer = new byte[8];
            stream.Read(buffer, 0, 8);

            // ZIP文件头 (Office文档都是ZIP格式)
            if (buffer[0] == 0x50 && buffer[1] == 0x4B)
            {
                // 进一步检查Office文档类型
                try
                {
                    using var archive = new System.IO.Compression.ZipArchive(stream, System.IO.Compression.ZipArchiveMode.Read);

                    // 检查是否包含Word文档特有的文件
                    if (archive.Entries.Any(e => e.FullName.Contains("word/")))
                        return ".docx";

                    // 检查是否包含Excel文档特有的文件
                    if (archive.Entries.Any(e => e.FullName.Contains("xl/")))
                        return ".xlsx";

                    // 检查是否包含PowerPoint文档特有的文件
                    if (archive.Entries.Any(e => e.FullName.Contains("ppt/")))
                        return ".pptx";
                }
                catch
                {
                    // 如果无法解析ZIP，返回通用ZIP标识
                    return ".zip";
                }
            }

            // PDF文件头
            if (buffer[0] == 0x25 && buffer[1] == 0x50 && buffer[2] == 0x44 && buffer[3] == 0x46)
                return ".pdf";

            // 旧版Excel文件头
            if (buffer[0] == 0xD0 && buffer[1] == 0xCF)
                return ".xls";

            return "unknown";
        }

        /// <summary>
        /// 创建Word文档处理器
        /// </summary>
        private IDocumentProcessor CreateWordProcessor()
        {
            var logger = _loggerFactory.CreateLogger<DocumentProcessor>();
            return new DocumentProcessorAdapter(new DocumentProcessor(_translationService, logger));
        }

        /// <summary>
        /// 创建Excel文档处理器
        /// </summary>
        private IDocumentProcessor CreateExcelProcessor()
        {
            var logger = _loggerFactory.CreateLogger<ExcelProcessor>();
            return new ExcelProcessorAdapter(new ExcelProcessor(_translationService, logger));
        }
    }

    /// <summary>
    /// 文档处理器接口
    /// </summary>
    public interface IDocumentProcessor
    {
        void SetProgressCallback(Action<double, string> callback);
        void SetTranslationOptions(bool useTerminology = true, bool preprocessTerms = true,
            bool exportPdf = false, string sourceLang = "zh", string targetLang = "en", string outputFormat = "bilingual");
        Task<string> ProcessDocumentAsync(string filePath, string targetLanguage, 
            System.Collections.Generic.Dictionary<string, string> terminology);
    }

    /// <summary>
    /// Word文档处理器适配器
    /// </summary>
    public class DocumentProcessorAdapter : IDocumentProcessor
    {
        private readonly DocumentProcessor _processor;

        public DocumentProcessorAdapter(DocumentProcessor processor)
        {
            _processor = processor ?? throw new ArgumentNullException(nameof(processor));
        }

        public void SetProgressCallback(Action<double, string> callback)
        {
            _processor.SetProgressCallback(callback);
        }

        public void SetTranslationOptions(bool useTerminology = true, bool preprocessTerms = true,
            bool exportPdf = false, string sourceLang = "zh", string targetLang = "en", string outputFormat = "bilingual")
        {
            _processor.SetTranslationOptions(useTerminology, preprocessTerms, exportPdf, sourceLang, targetLang, outputFormat);
        }

        public Task<string> ProcessDocumentAsync(string filePath, string targetLanguage, 
            System.Collections.Generic.Dictionary<string, string> terminology)
        {
            return _processor.ProcessDocumentAsync(filePath, targetLanguage, terminology);
        }
    }

    /// <summary>
    /// Excel文档处理器适配器
    /// </summary>
    public class ExcelProcessorAdapter : IDocumentProcessor
    {
        private readonly ExcelProcessor _processor;

        public ExcelProcessorAdapter(ExcelProcessor processor)
        {
            _processor = processor ?? throw new ArgumentNullException(nameof(processor));
        }

        public void SetProgressCallback(Action<double, string> callback)
        {
            _processor.SetProgressCallback(callback);
        }

        public void SetTranslationOptions(bool useTerminology = true, bool preprocessTerms = true,
            bool exportPdf = false, string sourceLang = "zh", string targetLang = "en", string outputFormat = "bilingual")
        {
            // Excel处理器不支持PDF导出，忽略exportPdf参数
            _processor.SetTranslationOptions(useTerminology, preprocessTerms, sourceLang, targetLang, outputFormat);
        }

        public Task<string> ProcessDocumentAsync(string filePath, string targetLanguage, 
            System.Collections.Generic.Dictionary<string, string> terminology)
        {
            return _processor.ProcessDocumentAsync(filePath, targetLanguage, terminology);
        }
    }
}
