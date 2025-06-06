@echo off
chcp 65001 >nul

echo ================================================================
echo 多格式文档翻译助手 - 简易打包启动器
echo ================================================================
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"
echo 当前目录: %CD%
echo.

:: 检查Python
echo 检查Python环境...
python --version
if errorlevel 1 (
    echo [错误] Python未找到，请检查Python安装
    echo 请确保Python已安装并添加到PATH环境变量
    pause
    exit /b 1
)

:: 检查Python脚本是否存在
if not exist "easy_pack.py" (
    echo [错误] 未找到 easy_pack.py 文件
    echo 请确保在正确的目录中运行此脚本
    pause
    exit /b 1
)

echo.
echo 启动Python打包脚本...
echo.

:: 运行Python脚本并捕获输出
python easy_pack.py
set PYTHON_EXIT_CODE=%errorlevel%

echo.
if %PYTHON_EXIT_CODE% equ 0 (
    echo Python脚本执行成功
) else (
    echo [错误] Python脚本执行失败，退出代码: %PYTHON_EXIT_CODE%
    echo.
    echo 可能的原因:
    echo 1. Python环境问题
    echo 2. 缺少必要的依赖包
    echo 3. 文件权限问题
    echo 4. 磁盘空间不足
    echo.
    echo 建议:
    echo 1. 检查Python环境是否正常
    echo 2. 尝试手动运行: python easy_pack.py
    echo 3. 查看详细错误信息
)

echo.
pause
