@echo off
chcp 65001 >nul
title 多格式文档翻译助手 - 简单打包

echo ================================================================
echo 多格式文档翻译助手 - 简单打包
echo ================================================================
echo.

:: 切换到项目目录
cd /d "D:\AI_project\文档术语翻译V3"
echo 当前目录: %CD%
echo.

:: 检查Python
echo 检查Python环境...
python --version
if errorlevel 1 (
    echo [错误] Python未找到
    pause
    exit /b 1
)

:: 检查conda环境
if not "%CONDA_DEFAULT_ENV%"=="" (
    echo 当前conda环境: %CONDA_DEFAULT_ENV%
) else (
    echo 未检测到conda环境
)
echo.

:: 安装PyInstaller
echo 检查PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo 安装PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller安装失败
        pause
        exit /b 1
    )
)

:: 清理旧文件
echo 清理旧文件...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del *.spec

echo.
echo 开始打包...
echo.

:: 执行打包
python -m PyInstaller ^
    --name=多格式文档翻译助手 ^
    --icon=logo.ico ^
    --windowed ^
    --onedir ^
    --add-data=data;data ^
    --add-data=web;web ^
    --add-data=API_config;API_config ^
    --add-data=config.json;. ^
    --hidden-import=services.translator ^
    --hidden-import=services.ollama_translator ^
    --hidden-import=services.zhipuai_translator ^
    --hidden-import=services.siliconflow_translator ^
    --hidden-import=services.base_translator ^
    --hidden-import=services.excel_processor ^
    --hidden-import=services.document_processor ^
    --hidden-import=services.pdf_processor ^
    --hidden-import=utils.terminology ^
    --hidden-import=utils.api_config ^
    --hidden-import=web.api ^
    --hidden-import=web.realtime_logger ^
    --hidden-import=fastapi ^
    --hidden-import=uvicorn ^
    --hidden-import=websockets ^
    --hidden-import=starlette ^
    --hidden-import=jinja2 ^
    --hidden-import=aiofiles ^
    --hidden-import=docx ^
    --hidden-import=openpyxl ^
    --hidden-import=PyMuPDF ^
    --hidden-import=fitz ^
    --hidden-import=pandas ^
    --hidden-import=numpy ^
    --hidden-import=openai ^
    --hidden-import=ollama ^
    --hidden-import=requests ^
    --hidden-import=httpx ^
    --hidden-import=aiohttp ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.ttk ^
    --hidden-import=tkinter.messagebox ^
    --clean ^
    --noconfirm ^
    launcher.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ================================================================
echo 打包成功！
echo ================================================================
echo.

:: 检查结果
if exist "dist\多格式文档翻译助手" (
    echo 结果位于: dist\多格式文档翻译助手\
    
    :: 复制文档
    echo 复制文档文件...
    if exist README.md copy README.md "dist\多格式文档翻译助手\" >nul
    if exist 使用说明.md copy 使用说明.md "dist\多格式文档翻译助手\" >nul
    
    :: 创建使用说明
    echo 创建使用说明...
    echo 多格式文档翻译助手 v3.0 > "dist\多格式文档翻译助手\使用说明.txt"
    echo. >> "dist\多格式文档翻译助手\使用说明.txt"
    echo 双击 "多格式文档翻译助手.exe" 启动程序 >> "dist\多格式文档翻译助手\使用说明.txt"
    echo 程序会自动打开Web界面 >> "dist\多格式文档翻译助手\使用说明.txt"
    
    echo.
    echo 打包完成！
    echo.
    
    set /p open=是否打开结果目录？(y/n): 
    if /i "%open%"=="y" explorer "dist\多格式文档翻译助手"
    
) else (
    echo [错误] 未找到打包结果
)

pause
