@echo off
chcp 65001 >nul

echo ================================================================
echo 多格式文档翻译助手 v3.1 - 最终封装
echo ================================================================
echo.
echo 本次封装包含所有最新改进:
echo ✅ 启动器不自动关闭功能
echo ✅ 实时后台信息显示
echo ✅ 服务器控制按钮
echo ✅ 改进的UI布局
echo ✅ 增强的日志显示
echo ✅ 编码问题修复
echo ✅ 完整的错误处理
echo.

cd /d "%~dp0"
echo 当前目录: %CD%
echo.

echo 检查Python环境...
python --version
if errorlevel 1 (
    echo [错误] Python未找到，请检查Python安装
    echo 请确保Python已安装并添加到PATH环境变量
    pause
    exit /b 1
)

echo.
echo 开始最终封装...
python final_build.py

if errorlevel 1 (
    echo.
    echo [错误] 封装失败
    pause
    exit /b 1
)

echo.
echo ================================================================
echo 封装完成！
echo ================================================================
echo.
echo 输出目录: dist\多格式文档翻译助手-最新版\
echo 可执行文件: 多格式文档翻译助手-最新版.exe
echo.
echo 请测试以下功能:
echo 1. 启动器是否正常启动
echo 2. 是否显示实时日志信息
echo 3. 控制按钮是否正常工作
echo 4. Web服务器是否正常启动
echo 5. 翻译功能是否正常
echo.

set /p choice=是否打开构建目录？(y/n): 
if /i "%choice%"=="y" (
    explorer "dist\多格式文档翻译助手-最新版"
)

pause
