# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('data/terminology.json', 'data'), ('config.json', '.'), ('logo.ico', '.'), ('API_config', 'API_config'), ('services', 'services'), ('utils', 'utils'), ('web', 'web'), ('ui', 'ui'), ('main.py', '.'), ('web_server.py', '.')],
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'webbrowser', 'socket', 'subprocess', 'threading', 'pathlib', 'pandas', 'openpyxl', 'python-docx', 'docx', 'PyMuPDF', 'fitz', 'python-pptx', 'pptx', 'cryptography', 'requests', 'chardet', 'psutil', 'services.translator', 'services.ollama_translator', 'services.zhipuai_translator', 'services.siliconflow_translator', 'services.base_translator', 'services.excel_processor', 'services.document_processor', 'services.pdf_processor', 'services.ppt_processor', 'services.intranet_translator', 'utils.terminology', 'utils.api_config', 'utils.license', 'utils.ui_logger', 'fastapi', 'uvicorn', 'websockets', 'jinja2', 'aiofiles', 'starlette', 'pydantic', 'openai', 'ollama', 'httpx', 'PIL', 'Pillow', 'numpy', 'jieba'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'notebook', 'jupyter', 'IPython', 'scipy', 'sklearn', 'tensorflow', 'torch'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='多文档术语翻译器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)
