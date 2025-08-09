using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.DependencyInjection;
using DocumentTranslator.Services.Translation;
using DocumentTranslator.Services.Logging;

namespace DocumentTranslator
{
    public partial class MainWindow : Window
    {
        private readonly Dictionary<string, string> _languageMap;
        private readonly TranslationService _translationService;
        private readonly DocumentProcessorFactory _documentProcessorFactory;
        private readonly TermExtractor _termExtractor;
        private readonly ConfigurationManager _configurationManager;
        private readonly ILogger<MainWindow> _logger;
        private string _currentEngine = "siliconflow";
        private bool _isTranslating = false;

        public MainWindow()
        {
            InitializeComponent();

            // 初始化依赖注入容器
            var services = new ServiceCollection();
            ConfigureServices(services);
            var serviceProvider = services.BuildServiceProvider();

            // 获取服务实例
            _translationService = serviceProvider.GetRequiredService<TranslationService>();
            _documentProcessorFactory = serviceProvider.GetRequiredService<DocumentProcessorFactory>();
            _termExtractor = serviceProvider.GetRequiredService<TermExtractor>();
            _configurationManager = serviceProvider.GetRequiredService<ConfigurationManager>();
            _logger = serviceProvider.GetRequiredService<ILogger<MainWindow>>();

            _languageMap = new Dictionary<string, string>
            {
                {"英语", "en"}, {"日语", "ja"}, {"韩语", "ko"}, {"法语", "fr"},
                {"德语", "de"}, {"西班牙语", "es"}, {"意大利语", "it"}, {"俄语", "ru"}
            };

            InitializeUI();
            LogMessage("🟢 系统初始化完成");
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
                builder.AddProvider(new CompositeLoggerProvider(LogMessage));
                builder.SetMinimumLevel(LogLevel.Information);
            });

            // 注册服务
            services.AddSingleton<ConfigurationManager>();
            services.AddSingleton<TranslationService>();
            services.AddSingleton<DocumentProcessor>();
            services.AddSingleton<ExcelProcessor>();
            services.AddSingleton<DocumentProcessorFactory>();
            services.AddSingleton<TermExtractor>();
        }

        private void InitializeUI()
        {
            // 设置默认选中的引擎
            UpdateEngineSelection("zhipuai");

            // 初始化模型列表
            RefreshModels(null, null);

            // 绑定翻译方向切换事件
            ChineseToForeign.Checked += OnTranslationDirectionChanged;
            ForeignToChinese.Checked += OnTranslationDirectionChanged;

            // 绑定语言选择变化事件
            LanguageCombo.SelectionChanged += OnLanguageSelectionChanged;

            // 绑定输出格式切换事件
            BilingualOutput.Checked += OnOutputFormatChanged;
            TranslationOnlyOutput.Checked += OnOutputFormatChanged;

            // 设置窗口图标和标题
            this.Title = "多格式文档翻译助手 v3.1";

            // 初始化翻译方向显示
            UpdateTranslationDirection();

            LogMessage("📊 界面初始化完成");
        }

        private void LogMessage(string message)
        {
            Dispatcher.Invoke(() =>
            {
                var timestamp = DateTime.Now.ToString("HH:mm:ss");
                LogTextBox.AppendText($"[{timestamp}] {message}\n");
                LogTextBox.ScrollToEnd();
            });
        }

        private void UpdateEngineSelection(string engine)
        {
            _currentEngine = engine;
            
            // 重置所有按钮样式
            ZhipuButton.Background = System.Windows.Media.Brushes.LightGray;
            OllamaButton.Background = System.Windows.Media.Brushes.LightGray;
            SiliconFlowButton.Background = System.Windows.Media.Brushes.LightGray;
            IntranetButton.Background = System.Windows.Media.Brushes.LightGray;
            
            // 高亮选中的按钮
            switch (engine)
            {
                case "zhipuai":
                    ZhipuButton.Background = System.Windows.Media.Brushes.LightBlue;
                    break;
                case "ollama":
                    OllamaButton.Background = System.Windows.Media.Brushes.LightBlue;
                    break;
                case "siliconflow":
                    SiliconFlowButton.Background = System.Windows.Media.Brushes.LightBlue;
                    break;
                case "intranet":
                    IntranetButton.Background = System.Windows.Media.Brushes.LightBlue;
                    break;
            }
            
            LogMessage($"🔄 切换到 {engine} 引擎");
        }

        // 文件选择
        private void SelectFile(object sender, RoutedEventArgs e)
        {
            var openFileDialog = new OpenFileDialog
            {
                Title = "选择要翻译的文档",
                Filter = "Word文档 (*.docx)|*.docx|PDF文档 (*.pdf)|*.pdf|Excel文档 (*.xlsx;*.xls)|*.xlsx;*.xls|PowerPoint文档 (*.pptx)|*.pptx|所有支持格式|*.docx;*.pdf;*.xlsx;*.xls;*.pptx|所有文件 (*.*)|*.*"
            };

            if (openFileDialog.ShowDialog() == true)
            {
                FilePathText.Text = openFileDialog.FileName;
                var fileInfo = new FileInfo(openFileDialog.FileName);

                // 检查文件格式是否支持
                var extension = Path.GetExtension(openFileDialog.FileName).ToLower();
                var supportedFormats = new[] { ".docx", ".pdf", ".xlsx", ".xls", ".pptx" };

                if (supportedFormats.Contains(extension))
                {
                    StatusText.Text = $"📄 已选择文档 ({fileInfo.Length / 1024.0:F1} KB)";
                    LogMessage($"📁 选择文件: {openFileDialog.FileName}");

                    // 根据文件类型显示特定提示
                    switch (extension)
                    {
                        case ".docx":
                            LogMessage("📝 Word文档 - 支持完整格式保留和双语对照");
                            break;
                        case ".pdf":
                            LogMessage("📑 PDF文档 - 将提取文本内容进行翻译");
                            break;
                        case ".xlsx":
                        case ".xls":
                            LogMessage("📊 Excel文档 - 支持表格内容翻译");
                            break;
                        case ".pptx":
                            LogMessage("📽️ PowerPoint文档 - 支持幻灯片内容翻译");
                            break;
                    }
                }
                else
                {
                    StatusText.Text = "⚠️ 不支持的文件格式";
                    LogMessage($"❌ 不支持的文件格式: {extension}");
                    MessageBox.Show($"不支持的文件格式: {extension}\n\n支持的格式包括:\n• Word文档 (.docx)\n• PDF文档 (.pdf)\n• Excel文档 (.xlsx, .xls)\n• PowerPoint文档 (.pptx)",
                                  "文件格式错误", MessageBoxButton.OK, MessageBoxImage.Warning);
                    FilePathText.Text = "";
                }
            }
        }

        private void ClearFile(object sender, RoutedEventArgs e)
        {
            FilePathText.Text = "";
            StatusText.Text = "🟢 系统就绪";
            LogMessage("🗑️ 已清除文件选择");
        }

        // 引擎选择
        private void SelectZhipuAI(object sender, RoutedEventArgs e)
        {
            UpdateEngineSelection("zhipuai");
        }

        private void SelectOllama(object sender, RoutedEventArgs e)
        {
            UpdateEngineSelection("ollama");
        }

        private void SelectSiliconFlow(object sender, RoutedEventArgs e)
        {
            UpdateEngineSelection("siliconflow");
        }

        private void SelectIntranet(object sender, RoutedEventArgs e)
        {
            UpdateEngineSelection("intranet");
        }

        // 模型刷新
        private async void RefreshModels(object sender, RoutedEventArgs e)
        {
            ModelCombo.Items.Clear();

            try
            {
                // 使用翻译服务获取可用模型
                var models = await _translationService.GetAvailableModelsAsync(_currentEngine);

                if (models.Any())
                {
                    foreach (var model in models)
                    {
                        ModelCombo.Items.Add(model);
                    }
                    ModelCombo.SelectedIndex = 0;
                    LogMessage($"🔄 已刷新 {_currentEngine} 模型列表，共 {models.Count} 个模型");
                }
                else
                {
                    // 如果无法获取模型列表，使用默认模型
                    AddDefaultModels();
                    LogMessage($"⚠️ 无法获取 {_currentEngine} 模型列表，使用默认模型");
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, $"刷新 {_currentEngine} 模型列表失败");
                AddDefaultModels();
                LogMessage($"❌ 刷新 {_currentEngine} 模型列表失败，使用默认模型");
            }
        }

        /// <summary>
        /// 添加默认模型列表
        /// </summary>
        private void AddDefaultModels()
        {
            switch (_currentEngine)
            {
                case "zhipuai":
                    ModelCombo.Items.Add("glm-4-flash-250414");
                    ModelCombo.Items.Add("GLM-4-Flash");
                    ModelCombo.Items.Add("GLM-Z1-Flash");
                    ModelCombo.Items.Add("GLM-4.1V-Thinking-Flash");
                    break;
                case "ollama":
                    ModelCombo.Items.Add("qwen3:7b");
                    ModelCombo.Items.Add("llama3.1:8b");
                    break;
                case "siliconflow":
                    ModelCombo.Items.Add("deepseek-ai/DeepSeek-V3");
                    ModelCombo.Items.Add("Qwen/Qwen2.5-72B-Instruct");
                    break;
                case "intranet":
                    ModelCombo.Items.Add("deepseek-r1-70b");
                    ModelCombo.Items.Add("qwen2.5-72b");
                    break;
            }

            if (ModelCombo.Items.Count > 0)
            {
                ModelCombo.SelectedIndex = 0;
            }
        }

        // 连接测试
        private async void TestConnection(object sender, RoutedEventArgs e)
        {
            TestStatusText.Text = "🔄 测试中...";
            TestStatusText.Foreground = System.Windows.Media.Brushes.Blue;

            try
            {
                var selectedModel = ModelCombo.SelectedItem?.ToString() ?? "default-model";

                // 切换到指定的翻译器
                _translationService.CurrentTranslatorType = _currentEngine;

                // 使用C#翻译服务进行连接测试
                var result = await _translationService.CurrentTranslator?.TestConnectionAsync();

                if (result == true)

                if (result)
                {
                    TestStatusText.Text = "✅ 测试成功";
                    TestStatusText.Foreground = System.Windows.Media.Brushes.Green;
                    TranslateButton.IsEnabled = true;
                    LogMessage($"✅ {_currentEngine} 连接测试成功");
                }
                else
                {
                    TestStatusText.Text = "❌ 测试失败";
                    TestStatusText.Foreground = System.Windows.Media.Brushes.Red;
                    TranslateButton.IsEnabled = false;
                    LogMessage($"❌ {_currentEngine} 连接测试失败");
                }
            }
            catch (Exception ex)
            {
                TestStatusText.Text = "❌ 测试异常";
                TestStatusText.Foreground = System.Windows.Media.Brushes.Red;
                TranslateButton.IsEnabled = false;
                LogMessage($"❌ {_currentEngine} 连接测试异常: {ex.Message}");
            }
        }

        // 开始翻译
        private async void StartTranslation(object sender, RoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(FilePathText.Text))
            {
                MessageBox.Show("请先选择要翻译的文件！", "警告", MessageBoxButton.OK, MessageBoxImage.Warning);
                return;
            }

            if (_isTranslating)
            {
                return;
            }

            _isTranslating = true;
            TranslateButton.IsEnabled = false;
            TranslationProgress.Visibility = Visibility.Visible;
            ProgressText.Visibility = Visibility.Visible;

            try
            {
                // 验证文件格式
                if (!ValidateFileFormat(FilePathText.Text))
                {
                    return;
                }

                LogMessage("🚀 开始翻译任务");
                StatusText.Text = "🔄 正在翻译中...";

                // 准备翻译请求
                var selectedLanguage = ((ComboBoxItem)LanguageCombo.SelectedItem)?.Content?.ToString() ?? "英语";
                var selectedModel = ModelCombo.SelectedItem?.ToString() ?? "glm-4-flash-250414";

                // 确定输出格式
                var outputFormat = BilingualOutput.IsChecked == true ? "bilingual" : "translation_only";

                // 改进的语言代码处理逻辑
                string sourceLanguage, targetLanguageCode, targetLanguageName;

                if (ChineseToForeign.IsChecked == true)
                {
                    // 中文 → 外语
                    sourceLanguage = "zh";
                    targetLanguageCode = _languageMap.GetValueOrDefault(selectedLanguage, "en");
                    targetLanguageName = selectedLanguage;
                }
                else
                {
                    // 外语 → 中文
                    sourceLanguage = _languageMap.GetValueOrDefault(selectedLanguage, "en");
                    targetLanguageCode = "zh";
                    targetLanguageName = "中文";
                }

                LogMessage($"🔧 翻译配置详情:");
                LogMessage($"   📁 文件: {Path.GetFileName(FilePathText.Text)}");
                LogMessage($"   🤖 引擎: {_currentEngine}");
                LogMessage($"   🎯 模型: {selectedModel}");
                LogMessage($"   🌐 翻译方向: {sourceLanguage} → {targetLanguageCode}");
                LogMessage($"   📋 输出格式: {outputFormat}");
                LogMessage($"   📚 使用术语库: {(UseTerminology.IsChecked == true ? "是" : "否")}");
                LogMessage($"   ⚡ 术语预处理: {(PreprocessTerms.IsChecked == true ? "是" : "否")}");
                LogMessage($"   📑 导出PDF: {(ExportPDF.IsChecked == true ? "是" : "否")}");

                // 创建适当的文档处理器
                LogMessage("🔍 正在分析文件类型并创建处理器...");
                var documentProcessor = _documentProcessorFactory.CreateProcessor(FilePathText.Text);
                LogMessage($"✅ 文档处理器创建成功");

                // 设置翻译器和文档处理器选项
                LogMessage("⚙️ 配置翻译器和处理器选项...");
                _translationService.CurrentTranslatorType = _currentEngine;
                documentProcessor.SetTranslationOptions(
                    useTerminology: UseTerminology.IsChecked == true,
                    preprocessTerms: PreprocessTerms.IsChecked == true,
                    exportPdf: ExportPDF.IsChecked == true,
                    sourceLang: sourceLanguage,
                    targetLang: targetLanguageCode,
                    outputFormat: outputFormat
                );
                LogMessage("✅ 处理器选项配置完成");

                // 设置进度回调
                var startTime = DateTime.Now;
                documentProcessor.SetProgressCallback((progress, message) =>
                {
                    Dispatcher.Invoke(() =>
                    {
                        TranslationProgress.Value = progress * 100;

                        // 计算预估剩余时间
                        var elapsed = DateTime.Now - startTime;
                        var estimatedTotal = progress > 0 ? TimeSpan.FromMilliseconds(elapsed.TotalMilliseconds / progress) : TimeSpan.Zero;
                        var remaining = estimatedTotal - elapsed;

                        var progressText = $"翻译进度: {progress * 100:F0}%";
                        if (progress > 0.05 && remaining.TotalSeconds > 0)
                        {
                            progressText += $" (预计剩余: {remaining:mm\\:ss})";
                        }

                        ProgressText.Text = progressText;
                        StatusText.Text = $"🔄 {message}";
                        LogMessage($"📊 进度: {progress * 100:F0}% - {message}");

                        // 更新状态栏
                        StatusBarText.Text = $"正在翻译... {progress * 100:F0}%";
                    });
                });

                // 加载术语库
                var terminology = new Dictionary<string, string>();
                if (UseTerminology.IsChecked == true)
                {
                    // 直接加载术语库：一律使用“UI选中的外语名称”作为术语库顶层键
                    // - 中文→外语：selectedLanguage 即目标外语
                    // - 外语→中文：selectedLanguage 即源外语
                    var terminologyLanguageName = selectedLanguage;
                    terminology = _termExtractor.GetTermsForLanguage(terminologyLanguageName);
                    LogMessage($"📚 已加载术语库（{terminologyLanguageName}）：{terminology.Count} 条");
                }

                // 调用C#翻译服务
                var outputPath = await documentProcessor.ProcessDocumentAsync(
                    FilePathText.Text,
                    targetLanguageName,
                    terminology
                );

                if (!string.IsNullOrEmpty(outputPath))
                {
                    var totalTime = DateTime.Now - startTime;
                    TranslationProgress.Value = 100;
                    ProgressText.Text = $"翻译进度: 100% (耗时: {totalTime:mm\\:ss})";
                    StatusText.Text = "✅ 翻译完成！";
                    StatusBarText.Text = "翻译完成";

                    LogMessage($"🎉 翻译任务完成！");
                    LogMessage($"   📁 输出文件: {outputPath}");
                    LogMessage($"   ⏱️ 总耗时: {totalTime:hh\\:mm\\:ss}");
                    LogMessage($"   📊 输出格式: {(BilingualOutput.IsChecked == true ? "双语对照" : "仅翻译结果")}");

                    var message = $"翻译完成！\n\n📁 输出文件：{outputPath}\n⏱️ 耗时：{totalTime:hh\\:mm\\:ss}";
                    if (ExportPDF.IsChecked == true)
                    {
                        message += $"\n📑 同时生成了PDF版本";
                    }

                    MessageBox.Show(message, "翻译成功", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                else
                {
                    throw new Exception("翻译失败：未生成输出文件");
                }
            }
            catch (Exception ex)
            {
                TranslationProgress.Value = 0;
                ProgressText.Text = "翻译进度: 0%";
                StatusText.Text = "❌ 翻译失败";

                // 详细的异常分析
                LogMessage($"❌ 翻译异常: {ex.GetType().Name} - {ex.Message}");
                if (ex.InnerException != null)
                {
                    LogMessage($"   内部异常: {ex.InnerException.Message}");
                }

                var suggestion = GetExceptionSuggestion(ex);
                var fullMessage = $"翻译失败：{ex.Message}";
                if (!string.IsNullOrEmpty(suggestion))
                {
                    fullMessage += $"\n\n💡 建议：{suggestion}";
                }

                MessageBox.Show(fullMessage, "翻译失败", MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                _isTranslating = false;
                TranslateButton.IsEnabled = true;
                TranslationProgress.Visibility = Visibility.Collapsed;
                ProgressText.Visibility = Visibility.Collapsed;
            }
        }

        // 菜单事件
        private void OpenZhipuSettings(object sender, RoutedEventArgs e)
        {
            LogMessage("⚙️ 打开智谱AI设置");
            OpenEngineConfig("zhipuai");
        }

        private void OpenOllamaSettings(object sender, RoutedEventArgs e)
        {
            LogMessage("⚙️ 打开Ollama设置");
            OpenEngineConfig("ollama");
        }

        private void OpenSiliconFlowSettings(object sender, RoutedEventArgs e)
        {
            LogMessage("⚙️ 打开硅基流动设置");
            OpenEngineConfig("siliconflow");
        }

        private void OpenIntranetSettings(object sender, RoutedEventArgs e)
        {
            LogMessage("⚙️ 打开内网OpenAI设置");
            OpenEngineConfig("intranet");
        }

        private void OpenEngineConfig(string engineType)
        {
            try
            {
                var configWindow = new Windows.EngineConfigWindow
                {
                    Owner = this
                };
                configWindow.ShowDialog();
                LogMessage($"✅ {engineType} 配置窗口已关闭");
            }
            catch (Exception ex)
            {
                LogMessage($"❌ 打开配置窗口失败: {ex.Message}");
                MessageBox.Show($"打开配置窗口失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void ShowLicenseInfo(object sender, RoutedEventArgs e)
        {
            LogMessage("ℹ️ 显示授权信息");
            MessageBox.Show("授权信息：已授权\n到期时间：2025-12-31", "授权信息", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void ShowAbout(object sender, RoutedEventArgs e)
        {
            MessageBox.Show("多格式文档翻译助手 v3.1\n\n支持Word、PDF、Excel等多种格式的智能文档翻译工具\n\nCopyright © 2025", 
                          "关于", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void OpenTerminologyEditor(object sender, RoutedEventArgs e)
        {
            LogMessage("📝 打开术语库编辑器");
            try
            {
                var editorWindow = new Windows.TerminologyEditorWindow
                {
                    Owner = this
                };
                editorWindow.ShowDialog();
                LogMessage("✅ 术语库编辑器已关闭");
            }
            catch (Exception ex)
            {
                LogMessage($"❌ 打开术语库编辑器失败: {ex.Message}");
                MessageBox.Show($"打开术语库编辑器失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void CopyLog(object sender, RoutedEventArgs e)
        {
            try
            {
                if (!string.IsNullOrEmpty(LogTextBox.Text))
                {
                    Clipboard.SetText(LogTextBox.Text);
                    LogMessage("📋 日志已复制到剪贴板");
                }
                else
                {
                    MessageBox.Show("日志为空，无法复制", "提示", MessageBoxButton.OK, MessageBoxImage.Information);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"复制日志失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void SaveLog(object sender, RoutedEventArgs e)
        {
            try
            {
                var saveFileDialog = new SaveFileDialog
                {
                    Title = "保存日志文件",
                    Filter = "文本文件 (*.txt)|*.txt|日志文件 (*.log)|*.log|所有文件 (*.*)|*.*",
                    FileName = $"translation_log_{DateTime.Now:yyyyMMdd_HHmmss}.txt"
                };

                if (saveFileDialog.ShowDialog() == true)
                {
                    File.WriteAllText(saveFileDialog.FileName, LogTextBox.Text);
                    LogMessage($"💾 日志已保存到: {saveFileDialog.FileName}");
                    MessageBox.Show("✅ 日志保存成功！", "保存完成", MessageBoxButton.OK, MessageBoxImage.Information);
                }
            }
            catch (Exception ex)
            {
                LogMessage($"❌ 保存日志失败: {ex.Message}");
                MessageBox.Show($"保存日志失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void ClearLog(object sender, RoutedEventArgs e)
        {
            var result = MessageBox.Show("确定要清除所有日志吗？", "确认清除",
                                       MessageBoxButton.YesNo, MessageBoxImage.Question);

            if (result == MessageBoxResult.Yes)
            {
                LogTextBox.Clear();
                LogMessage("🗑️ 日志已清除");
            }
        }

        private void OpenOutputDirectory(object sender, RoutedEventArgs e)
        {
            try
            {
                // 获取输出目录路径
                var outputDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "输出");

                // 如果输出目录不存在，则创建它
                if (!Directory.Exists(outputDir))
                {
                    Directory.CreateDirectory(outputDir);
                    LogMessage($"📁 创建输出目录: {outputDir}");
                }

                // 使用Windows资源管理器打开目录
                System.Diagnostics.Process.Start("explorer.exe", outputDir);
                LogMessage($"📁 已打开输出目录: {outputDir}");
            }
            catch (Exception ex)
            {
                LogMessage($"❌ 打开输出目录失败: {ex.Message}");
                MessageBox.Show($"打开输出目录失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        // 翻译方向切换事件处理
        private void OnTranslationDirectionChanged(object sender, RoutedEventArgs e)
        {
            UpdateTranslationDirection();
        }

        // 语言选择变化事件处理
        private void OnLanguageSelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            UpdateTranslationDirection();
        }

        // 更新翻译方向和语言代码映射
        private void UpdateTranslationDirection()
        {
            if (LanguageCombo.SelectedItem == null) return;

            var selectedLanguage = ((ComboBoxItem)LanguageCombo.SelectedItem).Content.ToString();
            var isChineseToForeign = ChineseToForeign.IsChecked == true;

            if (isChineseToForeign)
            {
                // 中文 → 外语
                StatusText.Text = $"🔄 翻译方向: 中文 → {selectedLanguage}";
                LogMessage($"🔄 设置翻译方向: 中文 → {selectedLanguage}");
            }
            else
            {
                // 外语 → 中文
                StatusText.Text = $"🔄 翻译方向: {selectedLanguage} → 中文";
                LogMessage($"🔄 设置翻译方向: {selectedLanguage} → 中文");
            }

            // 更新输出格式提示
            UpdateOutputFormatHint();
        }

        // 输出格式切换事件处理
        private void OnOutputFormatChanged(object sender, RoutedEventArgs e)
        {
            UpdateOutputFormatHint();
        }

        // 更新输出格式提示
        private void UpdateOutputFormatHint()
        {
            var outputFormat = BilingualOutput.IsChecked == true ? "双语对照" : "仅翻译结果";
            var description = BilingualOutput.IsChecked == true
                ? "原文和译文并排显示，便于对比检查"
                : "仅显示翻译结果，文档更简洁";

            LogMessage($"📋 输出格式: {outputFormat} - {description}");
        }

        // 验证文件格式支持
        private bool ValidateFileFormat(string filePath)
        {
            var extension = Path.GetExtension(filePath).ToLower();
            var supportedFormats = new Dictionary<string, string>
            {
                { ".docx", "Word文档" },
                { ".pdf", "PDF文档" },
                { ".xlsx", "Excel工作簿" },
                { ".xls", "Excel工作簿(旧版)" },
                { ".pptx", "PowerPoint演示文稿" }
            };

            if (supportedFormats.ContainsKey(extension))
            {
                LogMessage($"✅ 文件格式验证通过: {supportedFormats[extension]} ({extension})");
                return true;
            }
            else
            {
                var supportedList = string.Join(", ", supportedFormats.Values);
                LogMessage($"❌ 不支持的文件格式: {extension}");
                MessageBox.Show($"不支持的文件格式: {extension}\n\n支持的格式包括:\n{supportedList}",
                              "文件格式错误", MessageBoxButton.OK, MessageBoxImage.Warning);
                return false;
            }
        }





        // 错误建议方法
        private static string GetErrorSuggestion(string errorMessage)
        {
            if (string.IsNullOrEmpty(errorMessage)) return "";

            var lowerError = errorMessage.ToLower();

            if (lowerError.Contains("api") && lowerError.Contains("key"))
                return "请检查API密钥是否正确配置，可通过菜单栏的设置选项进行配置";

            if (lowerError.Contains("network") || lowerError.Contains("connection") || lowerError.Contains("timeout"))
                return "请检查网络连接是否正常，或尝试切换到其他翻译引擎";

            if (lowerError.Contains("quota") || lowerError.Contains("limit"))
                return "API配额已用完，请检查账户余额或等待配额重置";

            if (lowerError.Contains("model") || lowerError.Contains("不支持"))
                return "当前模型可能不可用，请尝试切换到其他模型";

            if (lowerError.Contains("file") || lowerError.Contains("文件"))
                return "请检查文件是否存在且未被其他程序占用";

            if (lowerError.Contains("python"))
                return "Python环境可能有问题，请确保Python已正确安装并配置";

            return "请检查配置设置，或尝试重新启动程序";
        }

        private static string GetExceptionSuggestion(Exception ex)
        {
            var exceptionType = ex.GetType().Name;

            switch (exceptionType)
            {
                case "HttpRequestException":
                    return "网络请求失败，请检查网络连接或API服务状态";
                case "TaskCanceledException":
                    return "请求超时，请检查网络连接或尝试增加超时时间";
                case "FileNotFoundException":
                    return "文件未找到，请确认文件路径正确且文件存在";
                case "UnauthorizedAccessException":
                    return "文件访问被拒绝，请检查文件权限或关闭占用文件的程序";
                case "JsonException":
                    return "数据解析错误，可能是API返回格式异常";
                case "ArgumentException":
                    return "参数错误，请检查输入的配置参数是否正确";
                default:
                    return GetErrorSuggestion(ex.Message);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            // 清理资源
            _translationService?.StopCurrentOperations();
            base.OnClosed(e);
        }
    }

    /// <summary>
    /// 翻译请求类（简化版，用于兼容性）
    /// </summary>
    public class TranslationRequest
    {
        public string FilePath { get; set; }
        public string TargetLanguage { get; set; }
        public string TargetLanguageCode { get; set; }
        public string SourceLanguage { get; set; }
        public string Engine { get; set; }
        public string Model { get; set; }
        public bool UseTerminology { get; set; }
        public bool PreprocessTerms { get; set; }
        public bool ExportPDF { get; set; }
        public string OutputFormat { get; set; }
    }

    /// <summary>
    /// 翻译结果类（简化版，用于兼容性）
    /// </summary>
    public class TranslationResult
    {
        public bool Success { get; set; }
        public string OutputPath { get; set; }
        public string ErrorMessage { get; set; }
        public int Progress { get; set; }
        public string StatusMessage { get; set; }
    }
}
