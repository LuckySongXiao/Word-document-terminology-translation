@echo off
chcp 65001 > nul
echo ========================================
echo 启动C# WPF文档翻译助手
echo ========================================

:: 检查是否已构建
if not exist "publish\DocumentTranslator.exe" (
    echo 未找到可执行文件，正在构建...
    call build_csharp.bat
    if %errorlevel% neq 0 (
        echo 构建失败，请检查错误信息
        pause
        exit /b 1
    )
)

:: 检查Python环境
echo 检查Python环境...
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo 警告：未找到Python，某些功能可能无法使用
    echo 请确保已安装Python 3.7+并添加到PATH
)

:: 检查Python依赖
echo 检查Python依赖...
python -c "import requests, json, logging" > nul 2>&1
if %errorlevel% neq 0 (
    echo 警告：Python依赖不完整，正在尝试安装...
    pip install -r requirements.txt
)

:: 启动程序
echo.
echo 启动C# WPF文档翻译助手...
echo ========================================
cd publish
start DocumentTranslator.exe

echo.
echo 程序已启动！
echo 如果遇到问题，请查看日志文件：
echo - translation.log (Python翻译日志)
echo - application.log (C#应用程序日志)
echo.
pause
