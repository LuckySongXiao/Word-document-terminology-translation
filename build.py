#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多格式文档翻译助手 - 构建脚本
支持一键打包成EXE可执行文件
"""

import PyInstaller.__main__
import os
import shutil
import sys
import site
import platform
import pkg_resources
import subprocess
import json
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def get_installed_packages():
    """获取当前环境中安装的所有包"""
    try:
        # 使用pip list获取所有已安装的包
        result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'],
                              capture_output=True, text=True, check=True)
        packages = json.loads(result.stdout)
        return {pkg['name'].lower(): pkg['version'] for pkg in packages}
    except Exception as e:
        logger.warning(f"无法获取已安装包列表: {e}")
        return {}

def get_required_packages():
    """获取项目所需的所有包"""
    required_packages = {
        # 核心Web框架
        'fastapi',
        'uvicorn',
        'python-multipart',
        'websockets',

        # AI和翻译相关
        'openai',
        'ollama',
        'requests',
        'httpx',

        # 文档处理
        'python-docx',
        'PyMuPDF',
        'python-pptx',
        'openpyxl',
        'PyPDF2',
        'pdf2image',

        # 图像处理
        'Pillow',
        'opencv-python',

        # 数据处理
        'pandas',
        'numpy',
        'jieba',

        # 网络和HTTP
        'aiohttp',
        'certifi',

        # 工具库
        'pydantic',
        'jinja2',
        'click',
        'colorama',
        'tqdm',

        # 打包相关
        'pyinstaller',
        'pyinstaller-hooks-contrib',

        # 其他必需依赖
        'charset-normalizer',
        'idna',
        'urllib3',
        'six',
        'python-dateutil',
        'pytz',
        'setuptools',
        'wheel',

        # Windows特定
        'pywin32',
        'psutil',
        'chardet',
        'cryptography',
    }
    return required_packages

def check_dependencies():
    """检查并安装缺失的依赖"""
    logger.info("检查项目依赖...")
    installed = get_installed_packages()
    required = get_required_packages()

    missing = [pkg for pkg in required if pkg.lower() not in installed]

    if missing:
        logger.info(f"发现缺失的依赖: {', '.join(missing)}")
        logger.info("正在安装缺失的依赖...")
        for package in missing:
            try:
                logger.info(f"安装 {package}...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', package],
                             check=True, capture_output=True, text=True)
                logger.info(f"✓ {package} 安装成功")
            except subprocess.CalledProcessError as e:
                logger.warning(f"✗ 安装 {package} 失败: {e}")
    else:
        logger.info("✓ 所有依赖已满足")

def get_package_paths():
    """获取所有依赖包的路径"""
    package_paths = []
    installed = get_installed_packages()

    for dist in pkg_resources.working_set:
        if dist.key.lower() in installed:
            try:
                # 获取包的位置
                location = dist.location
                if location and os.path.exists(location):
                    if os.path.isfile(location):
                        package_paths.append((location, '.'))
                    else:
                        for root, _, files in os.walk(location):
                            for file in files:
                                if file.endswith('.dll') or file.endswith('.pyd'):
                                    full_path = os.path.join(root, file)
                                    rel_path = os.path.relpath(root, location)
                                    package_paths.append((full_path, rel_path))
            except Exception as e:
                print(f"警告: 处理包 {dist.key} 时出错: {e}")

    return package_paths

def clean_dist():
    """清理之前的构建文件"""
    logger.info("清理之前的构建文件...")
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            logger.info(f"删除目录: {dir_name}")
            shutil.rmtree(dir_name)

    # 清理spec文件
    spec_files = [
        'word_AI术语翻译助手.spec',
        '多格式文档-AI双语翻译助手.spec',
        'launcher.spec'
    ]
    for spec_file in spec_files:
        if os.path.exists(spec_file):
            logger.info(f"删除spec文件: {spec_file}")
            os.remove(spec_file)

    logger.info("✓ 清理完成")

def copy_resources(dist_path):
    """复制必要的资源文件"""
    logger.info("复制资源文件...")

    # 创建data目录
    data_dir = os.path.join(dist_path, 'data')
    os.makedirs(data_dir, exist_ok=True)

    # 复制术语库文件
    if os.path.exists('data/terminology.json'):
        shutil.copy2('data/terminology.json', os.path.join(data_dir, 'terminology.json'))
        logger.info("✓ 复制术语库文件")

    # 复制配置文件
    if os.path.exists('config.json'):
        shutil.copy2('config.json', os.path.join(dist_path, 'config.json'))
        logger.info("✓ 复制配置文件")

    # 复制图标文件
    if os.path.exists('logo.ico'):
        shutil.copy2('logo.ico', os.path.join(dist_path, 'logo.ico'))
        logger.info("✓ 复制图标文件")

    # 复制Web静态文件
    web_static_dir = os.path.join(dist_path, 'web', 'static')
    if os.path.exists('web/static'):
        os.makedirs(web_static_dir, exist_ok=True)
        shutil.copytree('web/static', web_static_dir, dirs_exist_ok=True)
        logger.info("✓ 复制Web静态文件")

    # 复制Web模板文件
    web_templates_dir = os.path.join(dist_path, 'web', 'templates')
    if os.path.exists('web/templates'):
        os.makedirs(web_templates_dir, exist_ok=True)
        shutil.copytree('web/templates', web_templates_dir, dirs_exist_ok=True)
        logger.info("✓ 复制Web模板文件")

def get_python_dlls():
    """获取Python DLL文件路径"""
    python_dlls = []
    if platform.system() == 'Windows':
        python_path = os.path.dirname(sys.executable)
        for file in os.listdir(python_path):
            if file.lower().startswith('python') and file.lower().endswith('.dll'):
                python_dlls.append(os.path.join(python_path, file))
    return python_dlls

def embed_resources():
    """将资源文件嵌入到临时目录"""
    temp_dir = os.path.join('build', 'temp_resources')
    os.makedirs(temp_dir, exist_ok=True)

    # 复制并处理资源文件
    if os.path.exists('data/terminology.json'):
        os.makedirs(os.path.join(temp_dir, 'data'), exist_ok=True)
        shutil.copy2('data/terminology.json', os.path.join(temp_dir, 'data', 'terminology.json'))

    if os.path.exists('config.json'):
        shutil.copy2('config.json', os.path.join(temp_dir, 'config.json'))

    if os.path.exists('logo.ico'):
        shutil.copy2('logo.ico', os.path.join(temp_dir, 'logo.ico'))

    return temp_dir

def build_launcher_exe():
    """构建启动器EXE文件"""
    logger.info("=" * 60)
    logger.info("开始构建启动器EXE文件")
    logger.info("=" * 60)

    # 检查并安装依赖
    check_dependencies()

    # 清理旧文件
    clean_dist()

    # 创建临时资源目录
    temp_resources = embed_resources()

    try:
        # PyInstaller参数 - 启动器
        launcher_params = [
            'launcher.py',  # 启动器文件
            '--name=多格式文档翻译助手-启动器',
            '--icon=logo.ico',
            '--windowed',  # GUI应用，不显示控制台
            '--onefile',  # 生成单个文件
            '--clean',
            '--noconfirm',
            # 添加资源文件
            f'--add-data=logo.ico;.',
            # 添加隐藏导入
            '--hidden-import=tkinter',
            '--hidden-import=tkinter.ttk',
            '--hidden-import=tkinter.messagebox',
            '--hidden-import=webbrowser',
            '--hidden-import=socket',
            '--hidden-import=subprocess',
            '--hidden-import=threading',
            '--hidden-import=pathlib',
            # 排除不需要的模块
            '--exclude-module=matplotlib',
            '--exclude-module=numpy',
            '--exclude-module=pandas',
            '--exclude-module=PIL',
            '--exclude-module=cv2',
        ]

        logger.info("开始打包启动器...")
        PyInstaller.__main__.run(launcher_params)

        launcher_exe = os.path.join('dist', '多格式文档翻译助手-启动器.exe')
        if os.path.exists(launcher_exe):
            logger.info(f"✓ 启动器构建完成: {os.path.abspath(launcher_exe)}")
        else:
            raise Exception("启动器构建失败：未找到生成的EXE文件")

    except Exception as e:
        logger.error(f"构建启动器失败: {e}")
        raise
    finally:
        # 清理临时文件
        if os.path.exists('runtime_hook.py'):
            os.remove('runtime_hook.py')

def build_main_exe():
    """构建主程序EXE文件"""
    logger.info("=" * 60)
    logger.info("开始构建主程序EXE文件")
    logger.info("=" * 60)

    # 创建临时资源目录
    temp_resources = embed_resources()

    try:
        # PyInstaller参数 - 主程序
        main_params = [
            'launcher.py',  # 使用启动器作为入口点
            '--name=多格式文档翻译助手',
            '--icon=logo.ico',
            '--windowed',  # GUI应用
            '--onedir',  # 生成目录形式，包含所有依赖
            '--clean',
            '--noconfirm',
            # 添加必要的数据文件
            f'--add-data={os.path.join(temp_resources, "data/terminology.json")};data',
            f'--add-data={os.path.join(temp_resources, "config.json")};.',
            f'--add-data={os.path.join(temp_resources, "logo.ico")};.',
            # 添加整个项目目录
            '--add-data=services;services',
            '--add-data=utils;utils',
            '--add-data=web;web',
            '--add-data=main.py;.',
            '--add-data=web_server.py;.',
            # 添加必要的隐藏导入
            '--hidden-import=pandas',
            '--hidden-import=openpyxl',
            '--hidden-import=python-docx',
            '--hidden-import=docx',
            '--hidden-import=cryptography',
            '--hidden-import=requests',
            '--hidden-import=chardet',
            '--hidden-import=psutil',
            '--hidden-import=win32api',
            '--hidden-import=win32con',
            '--hidden-import=win32security',
            '--hidden-import=win32com',
            '--hidden-import=win32com.client',
            '--hidden-import=pythoncom',
            '--hidden-import=pywintypes',
            '--hidden-import=services.translator',
            '--hidden-import=services.ollama_translator',
            '--hidden-import=services.zhipuai_translator',
            '--hidden-import=services.siliconflow_translator',
            '--hidden-import=services.base_translator',
            '--hidden-import=services.excel_processor',
            '--hidden-import=services.document_processor',
            '--hidden-import=services.pdf_processor',
            '--hidden-import=fastapi',
            '--hidden-import=uvicorn',
            '--hidden-import=websockets',
            '--hidden-import=jinja2',
            '--hidden-import=aiofiles',
            # 添加运行时钩子
            '--runtime-hook=runtime_hook.py',
            # 排除不需要的模块
            '--exclude-module=matplotlib',
            '--exclude-module=notebook',
            '--exclude-module=jupyter',
            # 优化设置
            '--noupx',  # 不使用UPX压缩
        ]

        # 创建运行时钩子文件
        with open('runtime_hook.py', 'w', encoding='utf-8') as f:
            f.write("""
import os
import sys

def _append_paths():
    if hasattr(sys, '_MEIPASS'):
        os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']

_append_paths()
""")

        logger.info("开始打包主程序...")
        PyInstaller.__main__.run(main_params)

        # 获取生成的EXE文件路径
        exe_path = os.path.join('dist', '多格式文档翻译助手', '多格式文档翻译助手.exe')
        if os.path.exists(exe_path):
            logger.info(f"✓ 主程序构建完成: {os.path.abspath(exe_path)}")
        else:
            raise Exception("主程序构建失败：未找到生成的EXE文件")

    except Exception as e:
        logger.error(f"构建主程序失败: {e}")
        raise
    finally:
        # 清理临时文件
        if os.path.exists('runtime_hook.py'):
            os.remove('runtime_hook.py')

def build_all():
    """构建完整的应用程序包"""
    logger.info("=" * 60)
    logger.info("开始构建完整的应用程序包")
    logger.info("=" * 60)

    try:
        # 1. 构建启动器
        build_launcher_exe()

        # 2. 构建主程序
        # build_main_exe()  # 暂时注释掉，只构建启动器

        logger.info("=" * 60)
        logger.info("✓ 构建完成！")
        logger.info("=" * 60)

        # 显示构建结果
        dist_dir = os.path.abspath('dist')
        logger.info(f"构建输出目录: {dist_dir}")

        if os.path.exists(dist_dir):
            logger.info("构建的文件:")
            for item in os.listdir(dist_dir):
                item_path = os.path.join(dist_dir, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path) / (1024 * 1024)  # MB
                    logger.info(f"  - {item} ({size:.1f} MB)")
                else:
                    logger.info(f"  - {item}/ (目录)")

    except Exception as e:
        logger.error(f"构建失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    build_all()