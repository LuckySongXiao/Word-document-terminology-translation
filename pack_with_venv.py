#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多格式文档翻译助手 - 虚拟环境打包脚本
将整个项目和虚拟环境一起打包成可分发的形式
"""

import os
import sys
import shutil
import zipfile
import logging
from pathlib import Path
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pack.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class VenvPacker:
    def __init__(self):
        self.project_root = Path(__file__).parent
        # 检测conda环境
        if 'CONDA_DEFAULT_ENV' in os.environ:
            # conda环境
            conda_env_name = os.environ['CONDA_DEFAULT_ENV']
            if 'CONDA_PREFIX' in os.environ:
                self.venv_path = Path(os.environ['CONDA_PREFIX'])
            else:
                # 尝试从Python路径推断
                self.venv_path = Path(sys.executable).parent.parent
            logger.info(f"检测到conda环境: {conda_env_name}")
        else:
            # 普通虚拟环境
            self.venv_path = Path(sys.executable).parent.parent

        self.pack_dir = self.project_root / "packed_release"
        self.version = "3.0"
        self.build_date = datetime.now().strftime("%Y%m%d")

    def clean_pack_dir(self):
        """清理打包目录"""
        logger.info("清理打包目录...")

        if self.pack_dir.exists():
            logger.info(f"删除目录: {self.pack_dir}")
            shutil.rmtree(self.pack_dir)

        self.pack_dir.mkdir(exist_ok=True)
        logger.info("✓ 清理完成")

    def check_environment(self):
        """检查环境"""
        logger.info("检查环境...")

        logger.info(f"Python版本: {sys.version}")
        logger.info(f"Python路径: {sys.executable}")
        logger.info(f"虚拟环境路径: {self.venv_path}")
        logger.info(f"项目根目录: {self.project_root}")

        # 检查是否在虚拟环境中
        if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            logger.warning("当前不在虚拟环境中，建议在虚拟环境中运行")

        logger.info("✓ 环境检查完成")

    def copy_project_files(self):
        """复制项目文件"""
        logger.info("复制项目文件...")

        project_target = self.pack_dir / "project"
        project_target.mkdir(exist_ok=True)

        # 要复制的文件
        files_to_copy = [
            "launcher.py",
            "main.py",
            "web_server.py",
            "config.json",
            "logo.ico",
            "README.md",
            "使用说明.md",
            "BUILD_README.md",
            "COMPLETE_BUILD_GUIDE.md"
        ]

        # 要复制的目录
        dirs_to_copy = [
            "services",
            "utils",
            "web",
            "ui",
            "data",
            "API_config"
        ]

        # 复制文件
        for file_name in files_to_copy:
            src = self.project_root / file_name
            if src.exists():
                dst = project_target / file_name
                shutil.copy2(src, dst)
                logger.info(f"复制文件: {file_name}")

        # 复制目录
        for dir_name in dirs_to_copy:
            src = self.project_root / dir_name
            if src.exists():
                dst = project_target / dir_name
                shutil.copytree(src, dst, dirs_exist_ok=True)
                logger.info(f"复制目录: {dir_name}")

        logger.info("✓ 项目文件复制完成")

    def copy_virtual_environment(self):
        """复制虚拟环境"""
        logger.info("复制虚拟环境...")

        venv_target = self.pack_dir / "venv"

        # 复制虚拟环境
        if self.venv_path.exists():
            logger.info(f"复制虚拟环境从: {self.venv_path}")
            shutil.copytree(self.venv_path, venv_target, dirs_exist_ok=True)
            logger.info("✓ 虚拟环境复制完成")
        else:
            logger.warning("未找到虚拟环境，跳过复制")

    def create_launcher_scripts(self):
        """创建启动脚本"""
        logger.info("创建启动脚本...")

        # Windows批处理启动脚本
        bat_content = f'''@echo off
chcp 65001 >nul
echo ================================================================
echo 多格式文档翻译助手 v{self.version}
echo ================================================================
echo.

cd /d "%~dp0"

echo 启动Web服务器...
echo.

:: 尝试不同的Python路径
set PYTHON_PATH=%~dp0venv\\Scripts\\python.exe
if not exist "%PYTHON_PATH%" (
    set PYTHON_PATH=%~dp0venv\\python.exe
)
if not exist "%PYTHON_PATH%" (
    set PYTHON_PATH=%~dp0venv\\bin\\python
)

if not exist "%PYTHON_PATH%" (
    echo 错误: 未找到Python解释器
    echo 尝试的路径:
    echo   %~dp0venv\\Scripts\\python.exe
    echo   %~dp0venv\\python.exe
    echo   %~dp0venv\\bin\\python
    pause
    exit /b 1
)

echo 使用Python: %PYTHON_PATH%
echo.

:: 设置工作目录并启动
cd /d "%~dp0project"
"%PYTHON_PATH%" launcher.py

if errorlevel 1 (
    echo.
    echo 启动失败，请检查错误信息
    pause
)
'''

        bat_file = self.pack_dir / "启动翻译助手.bat"
        with open(bat_file, 'w', encoding='gbk') as f:
            f.write(bat_content)

        # Python启动脚本
        py_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多格式文档翻译助手 - 启动脚本
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # 获取脚本所在目录
    script_dir = Path(__file__).parent

    # 设置Python路径
    python_path = script_dir / "venv" / "Scripts" / "python.exe"
    if not python_path.exists():
        python_path = script_dir / "venv" / "bin" / "python"  # Linux/Mac

    if not python_path.exists():
        print("错误: 未找到Python解释器")
        print(f"查找路径: {{python_path}}")
        return 1

    # 启动主程序
    launcher_path = script_dir / "project" / "launcher.py"
    if not launcher_path.exists():
        print("错误: 未找到launcher.py")
        return 1

    # 设置工作目录为项目目录
    os.chdir(script_dir / "project")

    # 启动程序
    try:
        subprocess.run([str(python_path), str(launcher_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"启动失败: {{e}}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
'''

        py_file = self.pack_dir / "start.py"
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write(py_content)

        logger.info("✓ 启动脚本创建完成")

    def create_readme(self):
        """创建说明文件"""
        logger.info("创建说明文件...")

        readme_content = f"""# 多格式文档翻译助手 v{self.version}

## 概述

这是一个完整的虚拟环境打包版本，包含了所有必需的Python依赖和运行时环境。

## 系统要求

- Windows 10/11 x64
- 至少4GB内存
- 1GB可用磁盘空间

## 使用方法

### 方法一：双击批处理文件（推荐）
1. 双击 `启动翻译助手.bat` 文件
2. 等待程序启动
3. 浏览器会自动打开Web界面

### 方法二：使用Python脚本
1. 双击 `start.py` 文件
2. 或在命令行中运行: `python start.py`

## 功能特性

- **多格式支持**: Word、PDF、Excel、TXT等格式
- **多翻译引擎**: 智谱AI、Ollama、硅基流动等
- **术语库管理**: 支持术语库导入导出和预处理
- **局域网访问**: 支持局域网内多设备访问
- **Web界面**: 现代化的Web用户界面

## 局域网访问

程序启动后，其他设备可以通过以下地址访问：
- `http://[主机IP]:8000`
- 例如：`http://192.168.1.100:8000`

## 目录结构

```
多格式文档翻译助手_v{self.version}_{self.build_date}/
├── 启动翻译助手.bat          # Windows启动脚本
├── start.py                  # Python启动脚本
├── README.txt               # 本说明文件
├── project/                 # 项目文件
│   ├── launcher.py          # 主启动器
│   ├── web_server.py        # Web服务器
│   ├── services/            # 翻译服务
│   ├── utils/               # 工具模块
│   ├── web/                 # Web界面
│   ├── data/                # 数据文件
│   └── API_config/          # API配置
└── venv/                    # 虚拟环境
    ├── Scripts/             # Python可执行文件
    ├── Lib/                 # Python库
    └── ...
```

## 故障排除

### 常见问题

1. **启动失败**
   - 检查是否有杀毒软件阻止
   - 确保有足够的磁盘空间
   - 检查端口8000是否被占用

2. **浏览器未自动打开**
   - 手动打开浏览器访问 `http://localhost:8000`

3. **翻译功能异常**
   - 检查网络连接
   - 配置正确的API密钥

### 技术支持

如遇问题，请：
1. 查看启动日志
2. 检查项目文档
3. 联系技术支持

---

**版本**: {self.version}
**构建日期**: {self.build_date}
**兼容性**: Windows 10/11 x64
"""

        readme_file = self.pack_dir / "README.txt"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        logger.info("✓ 说明文件创建完成")

    def create_zip_package(self):
        """创建ZIP压缩包"""
        logger.info("创建ZIP压缩包...")

        zip_name = f"多格式文档翻译助手_v{self.version}_{self.build_date}.zip"
        zip_path = self.project_root / zip_name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(self.pack_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(self.pack_dir)
                    zipf.write(file_path, arc_path)

        # 计算大小
        pack_size = sum(f.stat().st_size for f in self.pack_dir.rglob('*') if f.is_file())
        zip_size = zip_path.stat().st_size

        logger.info(f"打包目录大小: {pack_size / 1024 / 1024:.1f} MB")
        logger.info(f"ZIP文件大小: {zip_size / 1024 / 1024:.1f} MB")
        logger.info(f"✓ ZIP压缩包创建完成: {zip_path}")

        return zip_path

    def pack(self):
        """执行完整打包流程"""
        logger.info("=" * 60)
        logger.info("开始虚拟环境打包")
        logger.info("=" * 60)

        try:
            # 1. 环境检查
            self.check_environment()

            # 2. 清理打包目录
            self.clean_pack_dir()

            # 3. 复制项目文件
            self.copy_project_files()

            # 4. 复制虚拟环境
            self.copy_virtual_environment()

            # 5. 创建启动脚本
            self.create_launcher_scripts()

            # 6. 创建说明文件
            self.create_readme()

            # 7. 创建ZIP压缩包
            zip_path = self.create_zip_package()

            logger.info("=" * 60)
            logger.info("✓ 虚拟环境打包完成!")
            logger.info("=" * 60)
            logger.info(f"打包目录: {self.pack_dir}")
            logger.info(f"ZIP文件: {zip_path}")
            logger.info("可以将ZIP文件分发给用户使用")

        except Exception as e:
            logger.error(f"打包失败: {e}")
            raise

def main():
    """主函数"""
    try:
        packer = VenvPacker()
        packer.pack()
    except Exception as e:
        logger.error(f"打包过程出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
