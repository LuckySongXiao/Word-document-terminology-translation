@echo off
chcp 65001 >nul
echo ================================================================
echo 多格式文档翻译助手 - 一键打包脚本
echo ================================================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8或更高版本
    pause
    exit /b 1
)

echo [信息] 检测到Python环境
python --version

echo.
echo [信息] 开始构建过程...
echo.

:: 运行构建脚本
python build_complete.py

if errorlevel 1 (
    echo.
    echo [错误] 构建失败，请查看错误信息
    pause
    exit /b 1
)

echo.
echo ================================================================
echo 构建完成！
echo ================================================================
echo.
echo 构建结果位于 release 目录中
echo 可以将生成的文件夹或ZIP包分发给用户使用
echo.

:: 询问是否打开发布目录
set /p choice="是否打开发布目录？(y/n): "
if /i "%choice%"=="y" (
    explorer release
)

pause
