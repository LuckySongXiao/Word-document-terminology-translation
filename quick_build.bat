@echo off
chcp 65001 >nul
echo ================================================================
echo 多格式文档翻译助手 - 快速打包
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
echo 检查PyInstaller...
python -c "import PyInstaller; print('PyInstaller版本:', PyInstaller.__version__)" 2>nul
if errorlevel 1 (
    echo 安装PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo PyInstaller安装失败
        pause
        exit /b 1
    )
)

echo.
echo 开始打包...
echo.

python -m PyInstaller --name="多格式文档翻译助手" --icon=logo.ico --windowed --onedir --add-data="data;data" --add-data="web;web" --add-data="API_config;API_config" --add-data="config.json;." --hidden-import=services.translator --hidden-import=services.ollama_translator --hidden-import=services.zhipuai_translator --hidden-import=services.siliconflow_translator --hidden-import=services.base_translator --hidden-import=services.excel_processor --hidden-import=services.document_processor --hidden-import=services.pdf_processor --hidden-import=utils.terminology --hidden-import=utils.api_config --hidden-import=web.api --hidden-import=web.realtime_logger --hidden-import=fastapi --hidden-import=uvicorn --hidden-import=websockets --hidden-import=starlette --hidden-import=jinja2 --hidden-import=aiofiles --hidden-import=docx --hidden-import=openpyxl --hidden-import=PyMuPDF --hidden-import=fitz --hidden-import=pandas --hidden-import=numpy --hidden-import=openai --hidden-import=ollama --hidden-import=requests --hidden-import=httpx --hidden-import=aiohttp --hidden-import=tkinter --hidden-import=tkinter.ttk --hidden-import=tkinter.messagebox --clean --noconfirm launcher.py

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
copy "README.md" "dist\多格式文档翻译助手\" >nul 2>&1
copy "使用说明.md" "dist\多格式文档翻译助手\" >nul 2>&1
copy "BUILD_README.md" "dist\多格式文档翻译助手\" >nul 2>&1

:: 创建快速开始文件
echo 创建快速开始文件...
echo 多格式文档翻译助手 v3.0 > "dist\多格式文档翻译助手\快速开始.txt"
echo. >> "dist\多格式文档翻译助手\快速开始.txt"
echo 使用方法: >> "dist\多格式文档翻译助手\快速开始.txt"
echo 1. 双击 "多格式文档翻译助手.exe" 启动程序 >> "dist\多格式文档翻译助手\快速开始.txt"
echo 2. 程序会自动启动Web服务器并打开浏览器 >> "dist\多格式文档翻译助手\快速开始.txt"
echo 3. 在Web界面中配置API密钥和术语库 >> "dist\多格式文档翻译助手\快速开始.txt"
echo 4. 上传文档开始翻译 >> "dist\多格式文档翻译助手\快速开始.txt"
echo. >> "dist\多格式文档翻译助手\快速开始.txt"
echo 支持格式: Word、PDF、Excel、TXT >> "dist\多格式文档翻译助手\快速开始.txt"
echo 支持翻译引擎: 智谱AI、Ollama、硅基流动 >> "dist\多格式文档翻译助手\快速开始.txt"
echo. >> "dist\多格式文档翻译助手\快速开始.txt"
echo 局域网访问: 其他设备可通过 http://[主机IP]:8000 访问 >> "dist\多格式文档翻译助手\快速开始.txt"

echo.
echo 打包完成！可以将 dist\多格式文档翻译助手\ 目录分发给用户使用
echo.

set /p choice=是否打开构建目录？(y/n):
if /i "%choice%"=="y" (
    explorer "dist\多格式文档翻译助手"
)

pause
