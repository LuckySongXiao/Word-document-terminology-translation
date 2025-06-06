@echo off
chcp 65001 >nul
title 文档术语翻译助手 - 内网模式启动器

echo.
echo ========================================
echo 🌐 文档术语翻译助手 - 内网模式启动器
echo ========================================
echo.

echo 📋 内网模式特性：
echo    ✅ 跳过外部API连接检查
echo    ✅ 避免网络超时错误
echo    ✅ 优先使用本地Ollama服务
echo    ✅ 支持内网翻译API
echo.

echo 🚀 正在启动内网模式...

:: 设置内网模式环境变量
set INTRANET_MODE=true
set OFFLINE_MODE=false

:: 查找可执行文件
set "EXE_FILE="
for %%f in (*.exe) do (
    if /i "%%~nf" neq "内网模式启动器" (
        set "EXE_FILE=%%f"
        goto :found_exe
    )
)

:found_exe
if "%EXE_FILE%"=="" (
    echo ❌ 未找到可执行文件
    echo 请确保此批处理文件与程序exe文件在同一目录
    pause
    exit /b 1
)

echo 📁 找到程序文件: %EXE_FILE%
echo 🔧 环境变量已设置: INTRANET_MODE=true
echo.

echo 🚀 启动程序...
echo.

:: 启动程序
start "" "%EXE_FILE%"

echo ✅ 程序已在内网模式下启动
echo.
echo 💡 提示：
echo    • 程序将跳过外部API连接检查
echo    • 如果需要使用翻译功能，请确保本地Ollama服务已启动
echo    • 控制台窗口会显示详细的运行信息
echo.

timeout /t 3 /nobreak >nul
exit
