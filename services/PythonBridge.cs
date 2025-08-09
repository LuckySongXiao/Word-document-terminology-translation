using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace DocumentTranslator.Services
{
    public class PythonBridge
    {
        private readonly string _pythonPath;
        private readonly string _scriptPath;

        public PythonBridge()
        {
            // 查找Python可执行文件
            _pythonPath = FindPythonExecutable();
            _scriptPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "python_scripts");

            // 记录使用的Python路径
            System.Diagnostics.Debug.WriteLine($"PythonBridge: 使用Python路径: {_pythonPath}");
        }

        private string FindPythonExecutable()
        {
            // 优先使用conda word环境的Python
            string[] possiblePaths = {
                @"C:\ProgramData\anaconda3\envs\word\python.exe",  // conda word环境（优先）
                @"C:\Users\" + Environment.UserName + @"\anaconda3\envs\word\python.exe",  // 用户conda word环境
                @"C:\ProgramData\anaconda3\python.exe",  // 基础conda环境
                @"C:\Users\" + Environment.UserName + @"\anaconda3\python.exe",  // 用户conda环境
                "python",  // 系统PATH中的python
                "python3",
                @"C:\Python\python.exe",
                @"C:\Python39\python.exe",
                @"C:\Python310\python.exe",
                @"C:\Python311\python.exe",
                @"C:\Python312\python.exe",
                @"C:\Python313\python.exe"
            };

            foreach (var path in possiblePaths)
            {
                try
                {
                    var process = new Process
                    {
                        StartInfo = new ProcessStartInfo
                        {
                            FileName = path,
                            Arguments = "--version",
                            UseShellExecute = false,
                            RedirectStandardOutput = true,
                            RedirectStandardError = true,
                            CreateNoWindow = true
                        }
                    };

                    process.Start();
                    process.WaitForExit(5000);

                    if (process.ExitCode == 0)
                    {
                        // 验证是否包含必要的包
                        if (ValidatePythonEnvironment(path))
                        {
                            return path;
                        }
                    }
                }
                catch
                {
                    // 继续尝试下一个路径
                }
            }

            throw new Exception("未找到合适的Python可执行文件。请确保已安装conda word环境或包含必要依赖的Python环境。");
        }

        private bool ValidatePythonEnvironment(string pythonPath)
        {
            try
            {
                // 测试关键模块是否可用
                var testScript = "import requests, openai, zhipuai, docx, openpyxl; print('OK')";
                var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = pythonPath,
                        Arguments = $"-c \"{testScript}\"",
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        CreateNoWindow = true
                    }
                };

                process.Start();
                process.WaitForExit(10000);

                return process.ExitCode == 0 && process.StandardOutput.ReadToEnd().Contains("OK");
            }
            catch
            {
                return false;
            }
        }

        public async Task<TranslationResult> TranslateDocumentAsync(TranslationRequest request)
        {
            try
            {
                // 创建临时配置文件
                var configPath = Path.GetTempFileName();
                var configJson = JsonConvert.SerializeObject(request, Formatting.Indented);
                await File.WriteAllTextAsync(configPath, configJson, Encoding.UTF8);

                // 调用Python翻译脚本
                var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = _pythonPath,
                        Arguments = $"\"{Path.Combine(_scriptPath, "translate_document.py")}\" \"{configPath}\"",
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        CreateNoWindow = true,
                        StandardOutputEncoding = Encoding.UTF8,
                        StandardErrorEncoding = Encoding.UTF8,
                        WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory
                    }
                };

                var output = new StringBuilder();
                var error = new StringBuilder();

                process.OutputDataReceived += (sender, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        output.AppendLine(e.Data);
                };

                process.ErrorDataReceived += (sender, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        error.AppendLine(e.Data);
                };

                process.Start();
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();

                await process.WaitForExitAsync();

                // 清理临时文件
                try { File.Delete(configPath); } catch { }

                if (process.ExitCode == 0)
                {
                    var resultJson = output.ToString();
                    return JsonConvert.DeserializeObject<TranslationResult>(resultJson);
                }
                else
                {
                    throw new Exception($"Python脚本执行失败: {error}");
                }
            }
            catch (Exception ex)
            {
                return new TranslationResult
                {
                    Success = false,
                    ErrorMessage = ex.Message
                };
            }
        }

        public async Task<TranslationResult> TranslateDocumentWithProgressAsync(TranslationRequest request,
            Action<int, string> progressCallback)
        {
            try
            {
                // 创建临时配置文件
                var configPath = Path.GetTempFileName();
                var configJson = JsonConvert.SerializeObject(request, Formatting.Indented);
                await File.WriteAllTextAsync(configPath, configJson, Encoding.UTF8);

                // 调用Python翻译脚本
                var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = _pythonPath,
                        Arguments = $"\"{Path.Combine(_scriptPath, "translate_document.py")}\" \"{configPath}\"",
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        CreateNoWindow = true,
                        StandardOutputEncoding = Encoding.UTF8,
                        StandardErrorEncoding = Encoding.UTF8,
                        WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory
                    }
                };

                var output = new StringBuilder();
                var error = new StringBuilder();
                var finalResult = new TranslationResult();

                process.OutputDataReceived += (sender, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                    {
                        output.AppendLine(e.Data);

                        // 尝试解析最终结果
                        try
                        {
                            var result = JsonConvert.DeserializeObject<TranslationResult>(e.Data);
                            if (result != null && result.Success)
                            {
                                finalResult = result;
                            }
                        }
                        catch
                        {
                            // 不是最终结果，忽略
                        }
                    }
                };

                process.ErrorDataReceived += (sender, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                    {
                        error.AppendLine(e.Data);

                        // 尝试解析进度信息
                        try
                        {
                            var progressData = JsonConvert.DeserializeObject<dynamic>(e.Data);
                            if (progressData?.type == "progress")
                            {
                                var progress = (int)(progressData.progress ?? 0);
                                var message = progressData.message?.ToString() ?? "";
                                progressCallback?.Invoke(progress, message);
                            }
                        }
                        catch
                        {
                            // 不是进度信息，作为错误处理
                        }
                    }
                };

                process.Start();
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();

                await process.WaitForExitAsync();

                // 清理临时文件
                try { File.Delete(configPath); } catch { }

                if (process.ExitCode == 0)
                {
                    // 如果有最终结果，返回它；否则尝试解析输出
                    if (finalResult.Success)
                    {
                        return finalResult;
                    }

                    var resultJson = output.ToString().Trim();
                    if (!string.IsNullOrEmpty(resultJson))
                    {
                        // 尝试解析最后一行作为结果
                        var lines = resultJson.Split('\n');
                        for (int i = lines.Length - 1; i >= 0; i--)
                        {
                            if (!string.IsNullOrWhiteSpace(lines[i]))
                            {
                                try
                                {
                                    return JsonConvert.DeserializeObject<TranslationResult>(lines[i]);
                                }
                                catch
                                {
                                    continue;
                                }
                            }
                        }
                    }

                    throw new Exception("无法解析翻译结果");
                }
                else
                {
                    var errorMessage = error.ToString();
                    throw new Exception($"Python脚本执行失败: {errorMessage}");
                }
            }
            catch (Exception ex)
            {
                return new TranslationResult
                {
                    Success = false,
                    ErrorMessage = ex.Message
                };
            }
        }

        public async Task<bool> TestConnectionAsync(string engine, string model)
        {
            try
            {
                var testRequest = new
                {
                    action = "test_connection",
                    engine = engine,
                    model = model
                };

                var configPath = Path.GetTempFileName();
                var configJson = JsonConvert.SerializeObject(testRequest, Formatting.Indented);
                await File.WriteAllTextAsync(configPath, configJson, Encoding.UTF8);

                var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = _pythonPath,
                        Arguments = $"\"{Path.Combine(_scriptPath, "test_connection.py")}\" \"{configPath}\"",
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        CreateNoWindow = true,
                        WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory
                    }
                };

                var output = new StringBuilder();
                var error = new StringBuilder();

                process.OutputDataReceived += (sender, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        output.AppendLine(e.Data);
                };

                process.ErrorDataReceived += (sender, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                        error.AppendLine(e.Data);
                };

                process.Start();
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();

                await process.WaitForExitAsync();

                // 记录详细信息用于调试
                var outputText = output.ToString();
                var errorText = error.ToString();

                System.Diagnostics.Debug.WriteLine($"Python测试连接 - 引擎: {engine}, 模型: {model}");
                System.Diagnostics.Debug.WriteLine($"退出码: {process.ExitCode}");
                System.Diagnostics.Debug.WriteLine($"标准输出: {outputText}");
                System.Diagnostics.Debug.WriteLine($"标准错误: {errorText}");

                // 清理临时文件
                try { File.Delete(configPath); } catch { }

                return process.ExitCode == 0;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"TestConnectionAsync异常: {ex.Message}");
                return false;
            }
        }

        private string GetLanguageCode(string languageName)
        {
            var languageMap = new Dictionary<string, string>
            {
                {"英语", "en"}, {"日语", "ja"}, {"韩语", "ko"}, {"法语", "fr"},
                {"德语", "de"}, {"西班牙语", "es"}, {"意大利语", "it"}, {"俄语", "ru"}
            };

            return languageMap.GetValueOrDefault(languageName, "en");
        }
    }

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

    public class TranslationResult
    {
        public bool Success { get; set; }
        public string OutputPath { get; set; }
        public string ErrorMessage { get; set; }
        public int Progress { get; set; }
        public string StatusMessage { get; set; }
    }
}

// 扩展方法，用于等待进程完成
public static class ProcessExtensions
{
    public static Task WaitForExitAsync(this Process process)
    {
        var tcs = new TaskCompletionSource<bool>();
        process.EnableRaisingEvents = true;
        process.Exited += (sender, args) => tcs.TrySetResult(true);
        if (process.HasExited)
            tcs.TrySetResult(true);
        return tcs.Task;
    }
}
