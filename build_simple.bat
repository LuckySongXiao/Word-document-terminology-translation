@echo off
chcp 65001 >nul
echo ================================================================
echo 多格式文档翻译助手 - 简化打包脚本
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
echo [信息] 开始简化构建过程...
echo [信息] 基于当前环境直接打包，不重新安装依赖
echo.

:: 运行简化构建脚本
python build_simple.py

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
echo 构建结果位于 dist 目录中
echo 可以将生成的文件夹分发给用户使用
echo.

:: 询问是否打开发布目录
set /p choice="是否打开构建目录？(y/n): "
if /i "%choice%"=="y" (
    explorer dist
)

pause
