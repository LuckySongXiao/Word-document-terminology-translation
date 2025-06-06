@echo off
chcp 65001 >nul
echo ================================================================
echo 多格式文档翻译助手 - 虚拟环境打包
echo ================================================================
echo.

cd /d "D:\AI_project\文档术语翻译V3"

echo 当前目录: %CD%
echo.

echo 检查Python环境...
python --version
if errorlevel 1 (
    echo Python未安装或不在PATH中
    pause
    exit /b 1
)

echo.
echo 检查虚拟环境...
python -c "import sys; print('虚拟环境:', hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))" 2>nul

echo.
echo 开始虚拟环境打包...
echo 注意: 这将复制整个虚拟环境，可能需要较长时间
echo.

python pack_with_venv.py

if errorlevel 1 (
    echo.
    echo 打包失败！
    pause
    exit /b 1
)

echo.
echo ================================================================
echo 虚拟环境打包完成！
echo ================================================================
echo.
echo 结果:
echo - 打包目录: packed_release\
echo - ZIP文件: 多格式文档翻译助手_v3.0_*.zip
echo.
echo 可以将ZIP文件分发给用户，解压后直接运行
echo.

set /p choice=是否打开打包目录？(y/n):
if /i "%choice%"=="y" (
    explorer packed_release
)

pause
