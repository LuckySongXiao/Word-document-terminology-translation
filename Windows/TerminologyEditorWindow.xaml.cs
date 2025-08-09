using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using Microsoft.Win32;
using Newtonsoft.Json;
using System.ComponentModel;

namespace DocumentTranslator.Windows
{
    public partial class TerminologyEditorWindow : Window
    {
        private readonly string _terminologyPath;
        private Dictionary<string, Dictionary<string, object>> _terminology;
        private ObservableCollection<TerminologyItem> _terminologyItems;
        private TerminologyItem _currentItem;
        private bool _isModified = false;

        public TerminologyEditorWindow()
        {
            InitializeComponent();
            _terminologyPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data", "terminology.json");
            _terminologyItems = new ObservableCollection<TerminologyItem>();

            LoadTerminology();
            UpdateTermCount();

            // 在窗口加载完成后初始化筛选
            this.Loaded += (s, e) => ApplyFilters();
        }

        #region 数据模型
        public class TerminologyItem : INotifyPropertyChanged
        {
            private string _chineseTerm;
            private string _category;
            private Dictionary<string, TermTranslation> _translations;

            public string ChineseTerm
            {
                get => _chineseTerm;
                set { _chineseTerm = value; OnPropertyChanged(); OnPropertyChanged(nameof(PreviewText)); }
            }

            public string Category
            {
                get => _category;
                set { _category = value; OnPropertyChanged(); }
            }

            public Dictionary<string, TermTranslation> Translations
            {
                get => _translations ?? (_translations = new Dictionary<string, TermTranslation>());
                set { _translations = value; OnPropertyChanged(); OnPropertyChanged(nameof(PreviewText)); }
            }

            public string PreviewText
            {
                get
                {
                    var preview = new List<string>();
                    if (Translations.ContainsKey("英语") && !string.IsNullOrEmpty(Translations["英语"].Term))
                        preview.Add($"EN: {Translations["英语"].Term}");
                    if (Translations.ContainsKey("日语") && !string.IsNullOrEmpty(Translations["日语"].Term))
                        preview.Add($"JP: {Translations["日语"].Term}");
                    return string.Join(" | ", preview.Take(2));
                }
            }

            public event PropertyChangedEventHandler PropertyChanged;
            protected virtual void OnPropertyChanged([System.Runtime.CompilerServices.CallerMemberName] string propertyName = null)
            {
                PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
            }
        }

        public class TermTranslation
        {
            public string Term { get; set; } = "";
            public string Note { get; set; } = "";
        }
        #endregion

        #region 数据加载和保存
        private void LoadTerminology()
        {
            try
            {
                if (File.Exists(_terminologyPath))
                {
                    var json = File.ReadAllText(_terminologyPath);
                    _terminology = JsonConvert.DeserializeObject<Dictionary<string, Dictionary<string, object>>>(json)
                                  ?? new Dictionary<string, Dictionary<string, object>>();
                }
                else
                {
                    // 创建数据目录
                    var dataDir = Path.GetDirectoryName(_terminologyPath);
                    if (!Directory.Exists(dataDir))
                    {
                        Directory.CreateDirectory(dataDir);
                    }

                    _terminology = new Dictionary<string, Dictionary<string, object>>();
                }

                RefreshTerminologyList();
                StatusText.Text = $"已加载 {_terminologyItems.Count} 条术语";
            }
            catch (Exception ex)
            {
                MessageBox.Show($"加载术语库失败: {ex.Message}\n\n详细信息: {ex.StackTrace}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                _terminology = new Dictionary<string, Dictionary<string, object>>();
                StatusText.Text = "术语库加载失败，已创建空白术语库";
            }
        }

        private void RefreshTerminologyList()
        {
            _terminologyItems.Clear();

            foreach (var language in _terminology.Keys)
            {
                if (_terminology[language] is Dictionary<string, object> terms)
                {
                    foreach (var term in terms.Keys)
                    {
                        var existingItem = _terminologyItems.FirstOrDefault(x => x.ChineseTerm == term);
                        if (existingItem == null)
                        {
                            existingItem = new TerminologyItem { ChineseTerm = term };
                            _terminologyItems.Add(existingItem);
                        }

                        if (!existingItem.Translations.ContainsKey(language))
                        {
                            existingItem.Translations[language] = new TermTranslation();
                        }

                        // 处理不同的数据格式
                        var termValue = terms[term];
                        if (termValue is string simpleTranslation)
                        {
                            existingItem.Translations[language].Term = simpleTranslation;
                        }
                        else if (termValue is Newtonsoft.Json.Linq.JObject complexTranslation)
                        {
                            existingItem.Translations[language].Term = complexTranslation["term"]?.ToString() ?? "";
                            existingItem.Translations[language].Note = complexTranslation["note"]?.ToString() ?? "";
                        }
                        else if (termValue != null)
                        {
                            // 尝试转换为字符串
                            existingItem.Translations[language].Term = termValue.ToString();
                        }
                    }
                }
            }

            // 按中文术语排序
            var sortedItems = _terminologyItems.OrderBy(x => x.ChineseTerm).ToList();
            _terminologyItems.Clear();
            foreach (var item in sortedItems)
            {
                _terminologyItems.Add(item);
            }

            UpdateTermCount();

            // 如果已经初始化完成，重新应用筛选
            if (IsLoaded)
            {
                ApplyFilters();
            }
        }

        private void SaveTerminology(object sender, RoutedEventArgs e)
        {
            try
            {
                // 保存当前编辑的术语
                if (_currentItem != null)
                {
                    SaveCurrentTermToData();
                }

                // 重建术语库数据结构
                var newTerminology = new Dictionary<string, Dictionary<string, object>>();

                foreach (var item in _terminologyItems)
                {
                    foreach (var translation in item.Translations)
                    {
                        var language = translation.Key;
                        var termData = translation.Value;

                        if (!newTerminology.ContainsKey(language))
                        {
                            newTerminology[language] = new Dictionary<string, object>();
                        }

                        if (!string.IsNullOrEmpty(termData.Term))
                        {
                            if (string.IsNullOrEmpty(termData.Note))
                            {
                                newTerminology[language][item.ChineseTerm] = termData.Term;
                            }
                            else
                            {
                                newTerminology[language][item.ChineseTerm] = new
                                {
                                    term = termData.Term,
                                    note = termData.Note
                                };
                            }
                        }
                    }
                }

                _terminology = newTerminology;

                // 保存到文件
                Directory.CreateDirectory(Path.GetDirectoryName(_terminologyPath));
                var json = JsonConvert.SerializeObject(_terminology, Formatting.Indented);
                File.WriteAllText(_terminologyPath, json);

                _isModified = false;
                StatusText.Text = "术语库保存成功";
                MessageBox.Show("✅ 术语库保存成功！", "保存完成", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"保存术语库失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        #endregion

        #region 术语编辑
        private void TermSelected(object sender, SelectionChangedEventArgs e)
        {
            if (TermListBox.SelectedItem is TerminologyItem selectedItem)
            {
                // 保存当前编辑的术语
                if (_currentItem != null && _currentItem != selectedItem)
                {
                    SaveCurrentTermToData();
                }

                _currentItem = selectedItem;
                LoadTermToEditor(selectedItem);
            }
        }

        private void LoadTermToEditor(TerminologyItem item)
        {
            ChineseTermBox.Text = item.ChineseTerm;
            CategoryBox.Text = item.Category ?? "";

            // 加载各语言翻译
            LoadLanguageTranslation(item, "英语", EnglishTermBox, EnglishNoteBox);
            LoadLanguageTranslation(item, "日语", JapaneseTermBox, JapaneseNoteBox);
            LoadLanguageTranslation(item, "韩语", KoreanTermBox, KoreanNoteBox);
            LoadLanguageTranslation(item, "法语", FrenchTermBox, FrenchNoteBox);
            LoadLanguageTranslation(item, "德语", GermanTermBox, GermanNoteBox);
            LoadLanguageTranslation(item, "西班牙语", SpanishTermBox, SpanishNoteBox);
            LoadLanguageTranslation(item, "意大利语", ItalianTermBox, ItalianNoteBox);
            LoadLanguageTranslation(item, "俄语", RussianTermBox, RussianNoteBox);
        }

        private void LoadLanguageTranslation(TerminologyItem item, string language, TextBox termBox, TextBox noteBox)
        {
            if (item.Translations.ContainsKey(language))
            {
                termBox.Text = item.Translations[language].Term;
                noteBox.Text = item.Translations[language].Note;
            }
            else
            {
                termBox.Text = "";
                noteBox.Text = "";
            }
        }

        private void SaveCurrentTerm(object sender, RoutedEventArgs e)
        {
            if (_currentItem != null)
            {
                SaveCurrentTermToData();
                StatusText.Text = "当前术语已保存";
                _isModified = true;
            }
        }

        private void SaveCurrentTermToData()
        {
            if (_currentItem == null) return;

            _currentItem.ChineseTerm = ChineseTermBox.Text;
            _currentItem.Category = CategoryBox.Text;

            // 保存各语言翻译
            SaveLanguageTranslation(_currentItem, "英语", EnglishTermBox, EnglishNoteBox);
            SaveLanguageTranslation(_currentItem, "日语", JapaneseTermBox, JapaneseNoteBox);
            SaveLanguageTranslation(_currentItem, "韩语", KoreanTermBox, KoreanNoteBox);
            SaveLanguageTranslation(_currentItem, "法语", FrenchTermBox, FrenchNoteBox);
            SaveLanguageTranslation(_currentItem, "德语", GermanTermBox, GermanNoteBox);
            SaveLanguageTranslation(_currentItem, "西班牙语", SpanishTermBox, SpanishNoteBox);
            SaveLanguageTranslation(_currentItem, "意大利语", ItalianTermBox, ItalianNoteBox);
            SaveLanguageTranslation(_currentItem, "俄语", RussianTermBox, RussianNoteBox);
        }

        private void SaveLanguageTranslation(TerminologyItem item, string language, TextBox termBox, TextBox noteBox)
        {
            if (!item.Translations.ContainsKey(language))
            {
                item.Translations[language] = new TermTranslation();
            }

            item.Translations[language].Term = termBox.Text;
            item.Translations[language].Note = noteBox.Text;
        }

        private void AddNewTerm(object sender, RoutedEventArgs e)
        {
            var newItem = new TerminologyItem
            {
                ChineseTerm = "新术语",
                Category = "技术术语"
            };

            _terminologyItems.Add(newItem);

            // 重新应用筛选以显示新术语
            ApplyFilters();

            // 选择新添加的术语
            if (_filteredItems != null)
            {
                var newItemInFiltered = _filteredItems.FirstOrDefault(x => x.ChineseTerm == "新术语");
                if (newItemInFiltered != null)
                {
                    TermListBox.SelectedItem = newItemInFiltered;
                }
            }

            ChineseTermBox.Focus();
            ChineseTermBox.SelectAll();

            UpdateTermCount();
            _isModified = true;
            StatusText.Text = "已添加新术语，请编辑内容";
        }

        private void DeleteCurrentTerm(object sender, RoutedEventArgs e)
        {
            if (_currentItem != null)
            {
                var result = MessageBox.Show($"确定要删除术语 '{_currentItem.ChineseTerm}' 吗？",
                                           "确认删除", MessageBoxButton.YesNo, MessageBoxImage.Warning);

                if (result == MessageBoxResult.Yes)
                {
                    _terminologyItems.Remove(_currentItem);
                    _currentItem = null;

                    // 重新应用筛选
                    ApplyFilters();

                    // 清空编辑器
                    ChineseTermBox.Text = "";
                    CategoryBox.Text = "";
                    ClearAllLanguageBoxes();

                    UpdateTermCount();
                    _isModified = true;
                    StatusText.Text = "术语已删除";
                }
            }
        }

        private void ResetCurrentTerm(object sender, RoutedEventArgs e)
        {
            if (_currentItem != null)
            {
                LoadTermToEditor(_currentItem);
                StatusText.Text = "已重置当前术语";
            }
        }

        private void ClearAllLanguageBoxes()
        {
            EnglishTermBox.Text = "";
            EnglishNoteBox.Text = "";
            JapaneseTermBox.Text = "";
            JapaneseNoteBox.Text = "";
            KoreanTermBox.Text = "";
            KoreanNoteBox.Text = "";
            FrenchTermBox.Text = "";
            FrenchNoteBox.Text = "";
            GermanTermBox.Text = "";
            GermanNoteBox.Text = "";
            SpanishTermBox.Text = "";
            SpanishNoteBox.Text = "";
            ItalianTermBox.Text = "";
            ItalianNoteBox.Text = "";
            RussianTermBox.Text = "";
            RussianNoteBox.Text = "";
        }
        #endregion

        #region 搜索和筛选
        private ObservableCollection<TerminologyItem> _filteredItems;

        private void SearchTerms(object sender, TextChangedEventArgs e)
        {
            ApplyFilters();
        }

        private void FilterByLanguage(object sender, SelectionChangedEventArgs e)
        {
            ApplyFilters();
        }

        private void ApplyFilters()
        {
            // 确保UI控件已初始化
            if (SearchBox == null || LanguageFilter == null || StatusText == null)
                return;

            var searchText = SearchBox.Text?.ToLower() ?? "";
            var selectedLanguage = ((ComboBoxItem)LanguageFilter.SelectedItem)?.Content?.ToString();

            var filteredItems = _terminologyItems.Where(item =>
            {
                // 语言筛选
                if (selectedLanguage != "全部" && !string.IsNullOrEmpty(selectedLanguage))
                {
                    if (!item.Translations.ContainsKey(selectedLanguage) ||
                        string.IsNullOrEmpty(item.Translations[selectedLanguage].Term))
                    {
                        return false;
                    }
                }

                // 文本搜索
                if (string.IsNullOrEmpty(searchText))
                {
                    return true;
                }

                // 搜索中文术语
                if (item.ChineseTerm?.ToLower().Contains(searchText) == true)
                {
                    return true;
                }

                // 搜索各语言翻译
                foreach (var translation in item.Translations.Values)
                {
                    if (translation.Term?.ToLower().Contains(searchText) == true ||
                        translation.Note?.ToLower().Contains(searchText) == true)
                    {
                        return true;
                    }
                }

                return false;
            }).ToList();

            // 更新过滤后的集合
            if (_filteredItems == null)
            {
                _filteredItems = new ObservableCollection<TerminologyItem>();
                TermListBox.ItemsSource = _filteredItems;
            }

            _filteredItems.Clear();
            foreach (var item in filteredItems)
            {
                _filteredItems.Add(item);
            }

            StatusText.Text = $"找到 {filteredItems.Count} 条匹配的术语";
        }

        private void UpdateTermCount()
        {
            TermCountText.Text = $"(共 {_terminologyItems.Count} 条术语)";
        }
        #endregion

        #region 导入导出
        private void ImportTerms(object sender, RoutedEventArgs e)
        {
            var openFileDialog = new OpenFileDialog
            {
                Title = "导入术语库",
                Filter = "Markdown文件 (*.md)|*.md|JSON文件 (*.json)|*.json|CSV文件 (*.csv)|*.csv|所有文件 (*.*)|*.*"
            };

            if (openFileDialog.ShowDialog() == true)
            {
                try
                {
                    var extension = Path.GetExtension(openFileDialog.FileName).ToLower();

                    if (extension == ".md")
                    {
                        ImportFromMarkdown(openFileDialog.FileName);
                    }
                    else if (extension == ".json")
                    {
                        ImportFromJson(openFileDialog.FileName);
                    }
                    else if (extension == ".csv")
                    {
                        ImportFromCsv(openFileDialog.FileName);
                    }
                    else
                    {
                        MessageBox.Show("不支持的文件格式", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                    }
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"导入失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        private void ImportFromMarkdown(string filePath)
        {
            var lines = File.ReadAllLines(filePath);
            var importCount = 0;
            var currentLanguage = "";

            foreach (var line in lines)
            {
                var trimmedLine = line.Trim();

                // 检查是否是语言标题
                if (trimmedLine.StartsWith("## ") && trimmedLine.Contains("术语"))
                {
                    if (trimmedLine.Contains("英语")) currentLanguage = "英语";
                    else if (trimmedLine.Contains("日语")) currentLanguage = "日语";
                    else if (trimmedLine.Contains("韩语")) currentLanguage = "韩语";
                    else if (trimmedLine.Contains("法语")) currentLanguage = "法语";
                    else if (trimmedLine.Contains("德语")) currentLanguage = "德语";
                    else if (trimmedLine.Contains("西班牙语")) currentLanguage = "西班牙语";
                    else if (trimmedLine.Contains("意大利语")) currentLanguage = "意大利语";
                    else if (trimmedLine.Contains("俄语")) currentLanguage = "俄语";
                    continue;
                }

                // 检查是否是术语行（格式：- 中文术语 -> 外语术语）
                if (trimmedLine.StartsWith("- ") && trimmedLine.Contains(" -> ") && !string.IsNullOrEmpty(currentLanguage))
                {
                    var parts = trimmedLine.Substring(2).Split(new[] { " -> " }, StringSplitOptions.None);
                    if (parts.Length == 2)
                    {
                        var chineseTerm = parts[0].Trim();
                        var foreignTerm = parts[1].Trim();

                        if (!string.IsNullOrEmpty(chineseTerm) && !string.IsNullOrEmpty(foreignTerm))
                        {
                            var existingItem = _terminologyItems.FirstOrDefault(x => x.ChineseTerm == chineseTerm);
                            if (existingItem == null)
                            {
                                existingItem = new TerminologyItem
                                {
                                    ChineseTerm = chineseTerm,
                                    Category = "技术术语"
                                };
                                _terminologyItems.Add(existingItem);
                            }

                            existingItem.Translations[currentLanguage] = new TermTranslation { Term = foreignTerm };
                            importCount++;
                        }
                    }
                }
            }

            UpdateTermCount();
            _isModified = true;
            StatusText.Text = $"成功从Markdown导入 {importCount} 条术语";
            MessageBox.Show($"✅ 成功从Markdown导入 {importCount} 条术语！", "导入完成", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void ImportFromJson(string filePath)
        {
            var json = File.ReadAllText(filePath);
            var importedTerminology = JsonConvert.DeserializeObject<Dictionary<string, Dictionary<string, object>>>(json);

            if (importedTerminology != null)
            {
                // 合并术语库
                foreach (var language in importedTerminology.Keys)
                {
                    if (!_terminology.ContainsKey(language))
                    {
                        _terminology[language] = new Dictionary<string, object>();
                    }

                    foreach (var term in importedTerminology[language])
                    {
                        _terminology[language][term.Key] = term.Value;
                    }
                }

                RefreshTerminologyList();
                _isModified = true;
                StatusText.Text = $"成功导入术语库，当前共 {_terminologyItems.Count} 条术语";
                MessageBox.Show("✅ 术语库导入成功！", "导入完成", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        }

        private void ImportFromCsv(string filePath)
        {
            var lines = File.ReadAllLines(filePath);
            if (lines.Length < 2) return;

            var headers = lines[0].Split(',');
            var chineseIndex = Array.IndexOf(headers, "中文");
            var englishIndex = Array.IndexOf(headers, "英语");

            if (chineseIndex == -1 || englishIndex == -1)
            {
                MessageBox.Show("CSV文件必须包含'中文'和'英语'列", "格式错误", MessageBoxButton.OK, MessageBoxImage.Error);
                return;
            }

            var importCount = 0;
            for (int i = 1; i < lines.Length; i++)
            {
                var values = lines[i].Split(',');
                if (values.Length > Math.Max(chineseIndex, englishIndex))
                {
                    var chineseTerm = values[chineseIndex].Trim();
                    var englishTerm = values[englishIndex].Trim();

                    if (!string.IsNullOrEmpty(chineseTerm) && !string.IsNullOrEmpty(englishTerm))
                    {
                        var existingItem = _terminologyItems.FirstOrDefault(x => x.ChineseTerm == chineseTerm);
                        if (existingItem == null)
                        {
                            existingItem = new TerminologyItem { ChineseTerm = chineseTerm };
                            _terminologyItems.Add(existingItem);
                        }

                        existingItem.Translations["英语"] = new TermTranslation { Term = englishTerm };
                        importCount++;
                    }
                }
            }

            UpdateTermCount();
            _isModified = true;
            StatusText.Text = $"成功导入 {importCount} 条术语";
            MessageBox.Show($"✅ 成功导入 {importCount} 条术语！", "导入完成", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void ExportTerms(object sender, RoutedEventArgs e)
        {
            var saveFileDialog = new SaveFileDialog
            {
                Title = "导出术语库",
                Filter = "Markdown文件 (*.md)|*.md|JSON文件 (*.json)|*.json|CSV文件 (*.csv)|*.csv",
                FileName = $"terminology_export_{DateTime.Now:yyyyMMdd_HHmmss}"
            };

            if (saveFileDialog.ShowDialog() == true)
            {
                try
                {
                    var extension = Path.GetExtension(saveFileDialog.FileName).ToLower();

                    if (extension == ".md")
                    {
                        ExportToMarkdown(saveFileDialog.FileName);
                    }
                    else if (extension == ".json")
                    {
                        ExportToJson(saveFileDialog.FileName);
                    }
                    else if (extension == ".csv")
                    {
                        ExportToCsv(saveFileDialog.FileName);
                    }

                    StatusText.Text = "术语库导出成功";
                    MessageBox.Show("✅ 术语库导出成功！", "导出完成", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"导出失败: {ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        private void ExportToMarkdown(string filePath)
        {
            var markdown = new List<string>();

            // 添加标题
            markdown.Add("# 术语库");
            markdown.Add("");
            markdown.Add($"导出时间: {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
            markdown.Add($"术语总数: {_terminologyItems.Count}");
            markdown.Add("");

            // 按语言分组导出
            var languages = new[] { "英语", "日语", "韩语", "法语", "德语", "西班牙语", "意大利语", "俄语" };

            foreach (var language in languages)
            {
                var termsInLanguage = _terminologyItems
                    .Where(item => item.Translations.ContainsKey(language) &&
                                  !string.IsNullOrEmpty(item.Translations[language].Term))
                    .OrderBy(item => item.ChineseTerm)
                    .ToList();

                if (termsInLanguage.Any())
                {
                    markdown.Add($"## {language}术语");
                    markdown.Add("");

                    foreach (var item in termsInLanguage)
                    {
                        var translation = item.Translations[language];
                        markdown.Add($"- {item.ChineseTerm} -> {translation.Term}");

                        // 如果有备注，添加备注
                        if (!string.IsNullOrEmpty(translation.Note))
                        {
                            markdown.Add($"  > 备注: {translation.Note}");
                        }
                    }

                    markdown.Add("");
                }
            }

            // 添加分类统计
            markdown.Add("## 分类统计");
            markdown.Add("");
            var categoryStats = _terminologyItems
                .GroupBy(item => item.Category ?? "未分类")
                .OrderByDescending(g => g.Count())
                .ToList();

            foreach (var category in categoryStats)
            {
                markdown.Add($"- {category.Key}: {category.Count()} 条");
            }

            File.WriteAllLines(filePath, markdown, Encoding.UTF8);
        }

        private void ExportToJson(string filePath)
        {
            // 保存当前编辑的术语
            if (_currentItem != null)
            {
                SaveCurrentTermToData();
            }

            // 重建术语库数据结构
            var exportTerminology = new Dictionary<string, Dictionary<string, object>>();

            foreach (var item in _terminologyItems)
            {
                foreach (var translation in item.Translations)
                {
                    var language = translation.Key;
                    var termData = translation.Value;

                    if (!exportTerminology.ContainsKey(language))
                    {
                        exportTerminology[language] = new Dictionary<string, object>();
                    }

                    if (!string.IsNullOrEmpty(termData.Term))
                    {
                        if (string.IsNullOrEmpty(termData.Note))
                        {
                            exportTerminology[language][item.ChineseTerm] = termData.Term;
                        }
                        else
                        {
                            exportTerminology[language][item.ChineseTerm] = new
                            {
                                term = termData.Term,
                                note = termData.Note
                            };
                        }
                    }
                }
            }

            var json = JsonConvert.SerializeObject(exportTerminology, Formatting.Indented);
            File.WriteAllText(filePath, json);
        }

        private void ExportToCsv(string filePath)
        {
            var csv = new List<string> { "中文,英语,日语,韩语,法语,德语,西班牙语,意大利语,俄语,分类" };

            foreach (var item in _terminologyItems)
            {
                var row = new List<string>
                {
                    item.ChineseTerm,
                    GetTranslationTerm(item, "英语"),
                    GetTranslationTerm(item, "日语"),
                    GetTranslationTerm(item, "韩语"),
                    GetTranslationTerm(item, "法语"),
                    GetTranslationTerm(item, "德语"),
                    GetTranslationTerm(item, "西班牙语"),
                    GetTranslationTerm(item, "意大利语"),
                    GetTranslationTerm(item, "俄语"),
                    item.Category ?? ""
                };

                csv.Add(string.Join(",", row.Select(x => $"\"{x}\"")));
            }

            File.WriteAllLines(filePath, csv);
        }

        private string GetTranslationTerm(TerminologyItem item, string language)
        {
            return item.Translations.ContainsKey(language) ? item.Translations[language].Term : "";
        }
        #endregion

        #region 其他功能
        private void ShowBatchOperations(object sender, RoutedEventArgs e)
        {
            MessageBox.Show("批量操作功能开发中...\n\n计划功能：\n• 批量删除\n• 批量导入\n• 批量翻译\n• 重复项检查",
                          "批量操作", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void ShowSettings(object sender, RoutedEventArgs e)
        {
            MessageBox.Show("设置功能开发中...\n\n计划功能：\n• 界面主题\n• 自动保存\n• 备份设置\n• 快捷键配置",
                          "设置", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void ShowHelp(object sender, RoutedEventArgs e)
        {
            var helpText = @"📝 术语库编辑器使用帮助

🔧 基本操作：
• 点击左侧术语列表选择要编辑的术语
• 在右侧编辑器中修改术语内容
• 点击'保存术语'保存当前编辑
• 点击'保存'按钮保存整个术语库

🔍 搜索功能：
• 在搜索框中输入关键词
• 支持搜索中文术语和各语言翻译
• 使用语言筛选器按语言筛选

📁 导入导出：
• 支持JSON和CSV格式
• JSON格式保留完整的术语结构
• CSV格式便于Excel编辑

💡 小贴士：
• 术语会自动按中文拼音排序
• 支持多语言同时编辑
• 可以为每个翻译添加备注";

            MessageBox.Show(helpText, "帮助", MessageBoxButton.OK, MessageBoxImage.Information);
        }

        private void CloseWindow(object sender, RoutedEventArgs e)
        {
            if (_isModified)
            {
                var result = MessageBox.Show("术语库已修改，是否保存？", "确认关闭",
                                           MessageBoxButton.YesNoCancel, MessageBoxImage.Question);

                if (result == MessageBoxResult.Yes)
                {
                    SaveTerminology(sender, e);
                }
                else if (result == MessageBoxResult.Cancel)
                {
                    return;
                }
            }

            this.Close();
        }

        protected override void OnClosing(CancelEventArgs e)
        {
            if (_isModified)
            {
                var result = MessageBox.Show("术语库已修改，是否保存？", "确认关闭",
                                           MessageBoxButton.YesNoCancel, MessageBoxImage.Question);

                if (result == MessageBoxResult.Yes)
                {
                    SaveTerminology(null, null);
                }
                else if (result == MessageBoxResult.Cancel)
                {
                    e.Cancel = true;
                    return;
                }
            }

            base.OnClosing(e);
        }
        #endregion
    }
}
