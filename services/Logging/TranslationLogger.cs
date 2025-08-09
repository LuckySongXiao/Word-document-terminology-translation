using System;
using System.IO;
using Microsoft.Extensions.Logging;

namespace DocumentTranslator.Services.Logging
{
    /// <summary>
    /// 翻译专用日志记录器，与Python版本兼容
    /// </summary>
    public class TranslationLogger : ILogger
    {
        private readonly string _categoryName;
        private readonly string _logFilePath;
        private readonly object _lock = new object();

        public TranslationLogger(string categoryName)
        {
            _categoryName = categoryName;
            _logFilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "translation_app.log");
        }

        public IDisposable BeginScope<TState>(TState state) => null;

        public bool IsEnabled(LogLevel logLevel) => logLevel >= LogLevel.Information;

        public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception exception, Func<TState, Exception, string> formatter)
        {
            if (!IsEnabled(logLevel))
                return;

            var message = formatter(state, exception);
            if (string.IsNullOrEmpty(message))
                return;

            var logEntry = FormatLogEntry(logLevel, message, exception);
            WriteToFile(logEntry);
        }

        /// <summary>
        /// 格式化日志条目，与Python版本保持一致
        /// </summary>
        private string FormatLogEntry(LogLevel logLevel, string message, Exception exception)
        {
            var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss,fff");
            var levelName = GetLevelName(logLevel);
            var categoryShort = GetShortCategoryName(_categoryName);

            var logEntry = $"{timestamp} - {levelName} - {categoryShort} - {message}";

            if (exception != null)
            {
                logEntry += Environment.NewLine + $"异常详情: {exception}";
            }

            return logEntry;
        }

        /// <summary>
        /// 获取日志级别名称
        /// </summary>
        private string GetLevelName(LogLevel logLevel)
        {
            return logLevel switch
            {
                LogLevel.Trace => "TRACE",
                LogLevel.Debug => "DEBUG",
                LogLevel.Information => "INFO",
                LogLevel.Warning => "WARNING",
                LogLevel.Error => "ERROR",
                LogLevel.Critical => "CRITICAL",
                _ => "INFO"
            };
        }

        /// <summary>
        /// 获取简短的类别名称
        /// </summary>
        private string GetShortCategoryName(string categoryName)
        {
            if (string.IsNullOrEmpty(categoryName))
                return "Unknown";

            // 提取类名
            var lastDotIndex = categoryName.LastIndexOf('.');
            if (lastDotIndex >= 0 && lastDotIndex < categoryName.Length - 1)
            {
                return categoryName.Substring(lastDotIndex + 1);
            }

            return categoryName;
        }

        /// <summary>
        /// 写入日志文件
        /// </summary>
        private void WriteToFile(string logEntry)
        {
            try
            {
                lock (_lock)
                {
                    File.AppendAllText(_logFilePath, logEntry + Environment.NewLine);
                }
            }
            catch
            {
                // 忽略日志写入错误，避免影响主程序
            }
        }
    }

    /// <summary>
    /// 翻译日志记录器提供程序
    /// </summary>
    public class TranslationLoggerProvider : ILoggerProvider
    {
        public ILogger CreateLogger(string categoryName)
        {
            return new TranslationLogger(categoryName);
        }

        public void Dispose()
        {
            // 无需释放资源
        }
    }

    /// <summary>
    /// 实时日志记录器，用于UI显示
    /// </summary>
    public class RealtimeLogger : ILogger
    {
        private readonly string _categoryName;
        private readonly Action<string> _logCallback;

        public RealtimeLogger(string categoryName, Action<string> logCallback)
        {
            _categoryName = categoryName;
            _logCallback = logCallback;
        }

        public IDisposable BeginScope<TState>(TState state) => null;

        public bool IsEnabled(LogLevel logLevel) => logLevel >= LogLevel.Information;

        public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception exception, Func<TState, Exception, string> formatter)
        {
            if (!IsEnabled(logLevel))
                return;

            var message = formatter(state, exception);
            if (string.IsNullOrEmpty(message))
                return;

            var timestamp = DateTime.Now.ToString("HH:mm:ss");
            var levelName = GetLevelName(logLevel);
            var logEntry = $"[{timestamp}] {levelName}: {message}";

            _logCallback?.Invoke(logEntry);
        }

        private string GetLevelName(LogLevel logLevel)
        {
            return logLevel switch
            {
                LogLevel.Information => "信息",
                LogLevel.Warning => "警告",
                LogLevel.Error => "错误",
                LogLevel.Critical => "严重",
                _ => "信息"
            };
        }
    }

    /// <summary>
    /// 实时日志记录器提供程序
    /// </summary>
    public class RealtimeLoggerProvider : ILoggerProvider
    {
        private readonly Action<string> _logCallback;

        public RealtimeLoggerProvider(Action<string> logCallback)
        {
            _logCallback = logCallback;
        }

        public ILogger CreateLogger(string categoryName)
        {
            return new RealtimeLogger(categoryName, _logCallback);
        }

        public void Dispose()
        {
            // 无需释放资源
        }
    }

    /// <summary>
    /// 组合日志记录器，同时写入文件和实时显示
    /// </summary>
    public class CompositeLogger : ILogger
    {
        private readonly ILogger _fileLogger;
        private readonly ILogger _realtimeLogger;

        public CompositeLogger(string categoryName, Action<string> logCallback)
        {
            _fileLogger = new TranslationLogger(categoryName);
            _realtimeLogger = new RealtimeLogger(categoryName, logCallback);
        }

        public IDisposable BeginScope<TState>(TState state) => null;

        public bool IsEnabled(LogLevel logLevel) => _fileLogger.IsEnabled(logLevel) || _realtimeLogger.IsEnabled(logLevel);

        public void Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception exception, Func<TState, Exception, string> formatter)
        {
            _fileLogger.Log(logLevel, eventId, state, exception, formatter);
            _realtimeLogger.Log(logLevel, eventId, state, exception, formatter);
        }
    }

    /// <summary>
    /// 组合日志记录器提供程序
    /// </summary>
    public class CompositeLoggerProvider : ILoggerProvider
    {
        private readonly Action<string> _logCallback;

        public CompositeLoggerProvider(Action<string> logCallback)
        {
            _logCallback = logCallback;
        }

        public ILogger CreateLogger(string categoryName)
        {
            return new CompositeLogger(categoryName, _logCallback);
        }

        public void Dispose()
        {
            // 无需释放资源
        }
    }

    /// <summary>
    /// 日志扩展方法
    /// </summary>
    public static class LoggerExtensions
    {
        /// <summary>
        /// 记录翻译开始
        /// </summary>
        public static void LogTranslationStart(this ILogger logger, string text, string sourceLang, string targetLang)
        {
            logger.LogInformation($"开始翻译: {sourceLang} -> {targetLang}, 文本长度: {text?.Length ?? 0}");
        }

        /// <summary>
        /// 记录翻译完成
        /// </summary>
        public static void LogTranslationComplete(this ILogger logger, string result, TimeSpan duration)
        {
            logger.LogInformation($"翻译完成, 结果长度: {result?.Length ?? 0}, 耗时: {duration.TotalSeconds:F2}秒");
        }

        /// <summary>
        /// 记录翻译失败
        /// </summary>
        public static void LogTranslationFailed(this ILogger logger, Exception exception, string text)
        {
            logger.LogError(exception, $"翻译失败, 文本长度: {text?.Length ?? 0}");
        }

        /// <summary>
        /// 记录进度更新
        /// </summary>
        public static void LogProgress(this ILogger logger, double progress, string message)
        {
            logger.LogInformation($"进度: {progress:P1} - {message}");
        }

        /// <summary>
        /// 记录术语应用
        /// </summary>
        public static void LogTerminologyApplied(this ILogger logger, int termCount, string language)
        {
            logger.LogInformation($"应用术语: {termCount} 个 {language} 术语");
        }

        /// <summary>
        /// 记录API调用
        /// </summary>
        public static void LogApiCall(this ILogger logger, string service, string model, string endpoint)
        {
            logger.LogInformation($"API调用: {service} - {model} - {endpoint}");
        }

        /// <summary>
        /// 记录配置加载
        /// </summary>
        public static void LogConfigurationLoaded(this ILogger logger, string configType, int itemCount)
        {
            logger.LogInformation($"配置加载: {configType}, 项目数: {itemCount}");
        }
    }
}
