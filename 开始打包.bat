@echo off
chcp 65001 >nul
echo ================================================================
echo 多格式文档翻译助手 - 打包选择器
echo ================================================================
echo.
echo 请选择打包方案:
echo.
echo 1. 简易打包 (推荐) - Python脚本，避免编码问题
echo 2. 超简单打包 - 最基础的打包方式
echo 3. 快速打包 - 基于当前环境，速度快
echo 4. Conda环境打包 - 专为conda环境优化
echo 5. 虚拟环境完整打包 - 包含完整虚拟环境
echo 6. 查看打包说明文档
echo 7. 退出
echo.

set /p choice=请输入选择 (1-7):

if "%choice%"=="1" goto easy
if "%choice%"=="2" goto ultra
if "%choice%"=="3" goto quick
if "%choice%"=="4" goto conda
if "%choice%"=="5" goto venv
if "%choice%"=="6" goto docs
if "%choice%"=="7" goto exit
goto invalid

:easy
echo.
echo 启动简易打包...
call easy_pack.bat
goto end

:ultra
echo.
echo 启动超简单打包...
call ultra_simple_pack.bat
goto end

:quick
echo.
echo 启动快速打包...
call quick_build.bat
goto end

:conda
echo.
echo 启动Conda环境打包...
call conda_build.bat
goto end

:venv
echo.
echo 启动虚拟环境完整打包...
call pack_with_venv.bat
goto end

:docs
echo.
echo 打开打包说明文档...
start 打包使用说明.md
pause
goto end

:invalid
echo.
echo 无效选择，请重新运行
pause
exit /b 1

:exit
echo.
echo 退出打包程序
exit /b 0

:end
echo.
echo 打包流程结束
pause
