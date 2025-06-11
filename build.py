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
import subprocess
import json
import logging

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



def build_final_exe():
    """构建最终的多文档术语翻译器.exe文件"""
    logger.info("=" * 60)
    logger.info("开始构建多文档术语翻译器.exe")
    logger.info("=" * 60)

    # 检查并安装依赖
    check_dependencies()

    # 清理旧文件
    clean_dist()

    # 确保必要的目录存在
    os.makedirs('build', exist_ok=True)

    try:
        # PyInstaller参数 - 最终版本
        final_params = [
            'launcher.py',  # 使用启动器作为入口点
            '--name=多文档术语翻译器',  # 最终的程序名称
            '--icon=logo.ico',
            '--console',  # 改为控制台模式，支持Web服务器启动
            '--onefile',  # 生成单个文件
            '--clean',
            '--noconfirm',
            # 添加必要的数据文件
            '--add-data=data/terminology.json;data',
            '--add-data=config.json;.',
            '--add-data=logo.ico;.',
            '--add-data=API_config;API_config',
            # 添加整个项目目录
            '--add-data=services;services',
            '--add-data=utils;utils',
            '--add-data=web;web',
            '--add-data=ui;ui',
            '--add-data=main.py;.',
            '--add-data=web_server.py;.',
            # 添加必要的隐藏导入
            '--hidden-import=tkinter',
            '--hidden-import=tkinter.ttk',
            '--hidden-import=tkinter.messagebox',
            '--hidden-import=webbrowser',
            '--hidden-import=socket',
            '--hidden-import=subprocess',
            '--hidden-import=threading',
            '--hidden-import=pathlib',
            '--hidden-import=pandas',
            '--hidden-import=openpyxl',
            '--hidden-import=python-docx',
            '--hidden-import=docx',
            '--hidden-import=PyMuPDF',
            '--hidden-import=fitz',
            '--hidden-import=python-pptx',
            '--hidden-import=pptx',
            '--hidden-import=cryptography',
            '--hidden-import=requests',
            '--hidden-import=chardet',
            '--hidden-import=psutil',
            '--hidden-import=services.translator',
            '--hidden-import=services.ollama_translator',
            '--hidden-import=services.zhipuai_translator',
            '--hidden-import=services.siliconflow_translator',
            '--hidden-import=services.base_translator',
            '--hidden-import=services.excel_processor',
            '--hidden-import=services.document_processor',
            '--hidden-import=services.pdf_processor',
            '--hidden-import=services.ppt_processor',
            '--hidden-import=services.intranet_translator',
            '--hidden-import=utils.terminology',
            '--hidden-import=utils.api_config',
            '--hidden-import=utils.license',
            '--hidden-import=utils.ui_logger',
            '--hidden-import=fastapi',
            '--hidden-import=uvicorn',
            '--hidden-import=websockets',
            '--hidden-import=jinja2',
            '--hidden-import=aiofiles',
            '--hidden-import=starlette',
            '--hidden-import=pydantic',
            '--hidden-import=openai',
            '--hidden-import=ollama',
            '--hidden-import=httpx',
            '--hidden-import=PIL',
            '--hidden-import=Pillow',
            '--hidden-import=numpy',
            '--hidden-import=jieba',
            # 排除不需要的模块
            '--exclude-module=matplotlib',
            '--exclude-module=notebook',
            '--exclude-module=jupyter',
            '--exclude-module=IPython',
            '--exclude-module=scipy',
            '--exclude-module=sklearn',
            '--exclude-module=tensorflow',
            '--exclude-module=torch',
            # 优化设置
            '--noupx',  # 不使用UPX压缩，避免兼容性问题
        ]

        logger.info("开始打包最终程序...")
        PyInstaller.__main__.run(final_params)

        final_exe = os.path.join('dist', '多文档术语翻译器.exe')
        if os.path.exists(final_exe):
            size = os.path.getsize(final_exe) / (1024 * 1024)  # MB
            logger.info(f"✓ 最终程序构建完成: {os.path.abspath(final_exe)} ({size:.1f} MB)")
        else:
            raise Exception("最终程序构建失败：未找到生成的EXE文件")

    except Exception as e:
        logger.error(f"构建最终程序失败: {e}")
        raise
    finally:
        # 清理临时文件
        if os.path.exists('runtime_hook.py'):
            os.remove('runtime_hook.py')



def build_all():
    """构建最终的多文档术语翻译器.exe"""
    logger.info("=" * 60)
    logger.info("开始构建多文档术语翻译器")
    logger.info("=" * 60)

    try:
        # 构建最终的可执行文件
        build_final_exe()

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

        # 提示用户
        final_exe = os.path.join(dist_dir, '多文档术语翻译器.exe')
        if os.path.exists(final_exe):
            logger.info("=" * 60)
            logger.info("🎉 打包成功！")
            logger.info(f"可执行文件位置: {final_exe}")
            logger.info("您可以直接运行这个EXE文件来使用多文档术语翻译器")
            logger.info("=" * 60)

    except Exception as e:
        logger.error(f"构建失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    build_all()