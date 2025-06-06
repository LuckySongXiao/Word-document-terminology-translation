@echo off
chcp 65001 >nul

echo ================================================================
echo 多格式文档翻译助手 - 超简单打包
echo ================================================================
echo.

cd /d "D:\AI_project\文档术语翻译V3"
echo 当前目录: %CD%
echo.

echo 检查Python...
python --version
if errorlevel 1 (
    echo Python未找到，请检查安装
    pause
    exit /b 1
)

echo.
echo 安装PyInstaller...
pip install pyinstaller

echo.
echo 清理旧文件...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo.
echo 开始打包...
pyinstaller --onedir --windowed --icon=logo.ico --name=多格式文档翻译助手 --add-data=data;data --add-data=web;web --add-data=API_config;API_config --add-data=config.json;. launcher.py

if errorlevel 1 (
    echo 打包失败
    pause
    exit /b 1
)

echo.
echo 打包完成！
echo 结果在 dist\多格式文档翻译助手\ 目录

echo.
set /p open=打开结果目录？(y/n): 
if /i "%open%"=="y" explorer "dist\多格式文档翻译助手"

pause
