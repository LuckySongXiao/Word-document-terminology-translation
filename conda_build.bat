@echo off
chcp 65001 >nul
echo ================================================================
echo 多格式文档翻译助手 - Conda环境打包
echo ================================================================
echo.

cd /d "D:\AI_project\文档术语翻译V3"

echo 当前目录: %CD%
echo.

:: 检查conda环境
if "%CONDA_DEFAULT_ENV%"=="" (
    echo 错误: 未检测到conda环境
    echo 请先激活conda环境: conda activate word
    pause
    exit /b 1
)

echo 当前conda环境: %CONDA_DEFAULT_ENV%
echo Python路径: %CONDA_PREFIX%

echo.
echo 检查Python环境...
python --version
if errorlevel 1 (
    echo Python未安装或不在PATH中
    pause
    exit /b 1
)

echo.
echo 检查PyInstaller...
python -c "import PyInstaller; print('PyInstaller版本:', PyInstaller.__version__)" 2>nul
if errorlevel 1 (
    echo 安装PyInstaller...
    conda install pyinstaller -y
    if errorlevel 1 (
        echo 尝试使用pip安装...
        pip install pyinstaller
        if errorlevel 1 (
            echo PyInstaller安装失败
            pause
            exit /b 1
        )
    )
)

echo.
echo 开始打包...
echo 注意: 这可能需要几分钟时间
echo.

:: 复制spec文件模板
echo 创建PyInstaller配置文件...
copy app_template.spec app.spec >nul
if errorlevel 1 (
    echo 配置文件创建失败
    pause
    exit /b 1
)
echo 配置文件创建完成

echo.
echo 执行打包...
python -m PyInstaller app.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo 打包失败！
    pause
    exit /b 1
)

echo.
echo ================================================================
echo 打包完成！
echo ================================================================
echo.
echo 结果位于 dist\多格式文档翻译助手\ 目录
echo.

:: 复制额外文件
echo 复制额外文件...
if exist "README.md" copy "README.md" "dist\多格式文档翻译助手\" >nul 2>&1
if exist "使用说明.md" copy "使用说明.md" "dist\多格式文档翻译助手\" >nul 2>&1
if exist "BUILD_README.md" copy "BUILD_README.md" "dist\多格式文档翻译助手\" >nul 2>&1

:: 创建快速开始文件
echo 创建快速开始文件...
(
echo 多格式文档翻译助手 v3.0
echo.
echo 使用方法:
echo 1. 双击 "多格式文档翻译助手.exe" 启动程序
echo 2. 程序会自动启动Web服务器并打开浏览器
echo 3. 在Web界面中配置API密钥和术语库
echo 4. 上传文档开始翻译
echo.
echo 支持格式: Word、PDF、Excel、TXT
echo 支持翻译引擎: 智谱AI、Ollama、硅基流动
echo.
echo 局域网访问: 其他设备可通过 http://[主机IP]:8000 访问
) > "dist\多格式文档翻译助手\快速开始.txt"

echo.
echo 打包完成！可以将 dist\多格式文档翻译助手\ 目录分发给用户使用
echo.

set /p choice=是否打开构建目录？(y/n):
if /i "%choice%"=="y" explorer "dist\多格式文档翻译助手"

pause
