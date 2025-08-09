@echo off
chcp 65001 > nul
echo ========================================
echo 构建C# WPF文档翻译助手
echo ========================================

:: 检查.NET SDK
echo 检查.NET SDK...
dotnet --version > nul 2>&1
if %errorlevel% neq 0 (
    echo 错误：未找到.NET SDK，请先安装.NET 6.0或更高版本
    echo 下载地址：https://dotnet.microsoft.com/download
    pause
    exit /b 1
)

echo .NET SDK版本：
dotnet --version

:: 还原NuGet包
echo.
echo 还原NuGet包...
dotnet restore
if %errorlevel% neq 0 (
    echo 错误：NuGet包还原失败
    pause
    exit /b 1
)

:: 构建项目
echo.
echo 构建项目...
dotnet build --configuration Release
if %errorlevel% neq 0 (
    echo 错误：项目构建失败
    pause
    exit /b 1
)

:: 发布项目
echo.
echo 发布项目...
dotnet publish --configuration Release --output "./publish" --self-contained true --runtime win-x64
if %errorlevel% neq 0 (
    echo 错误：项目发布失败
    pause
    exit /b 1
)

:: 复制Python脚本和资源文件
echo.
echo 复制资源文件...
if not exist ".\publish\python_scripts" mkdir ".\publish\python_scripts"
copy ".\python_scripts\*.py" ".\publish\python_scripts\" > nul
copy ".\services\*.py" ".\publish\services\" > nul 2>&1
copy ".\utils\*.py" ".\publish\utils\" > nul 2>&1
copy ".\data\*.json" ".\publish\data\" > nul 2>&1
copy ".\API_config\*.json" ".\publish\API_config\" > nul 2>&1
copy ".\logo.ico" ".\publish\" > nul 2>&1

echo.
echo ========================================
echo 构建完成！
echo ========================================
echo 可执行文件位置：.\publish\DocumentTranslator.exe
echo.
echo 注意：运行前请确保：
echo 1. 已安装Python 3.7+
echo 2. 已安装必要的Python包（requirements.txt）
echo 3. 配置了相应的API密钥
echo.
pause
