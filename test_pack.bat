@echo off
chcp 65001 >nul

echo ================================================================
echo 测试打包脚本
echo ================================================================
echo.

:: 切换到脚本目录
cd /d "%~dp0"

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python未找到
    pause
    exit /b 1
)

:: 运行测试脚本
python test_pack.py

pause
