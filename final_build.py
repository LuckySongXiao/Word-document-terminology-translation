#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终封装脚本 - 包含所有最新改进
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path

class FinalBuilder:
    def __init__(self):
        self.project_root = Path.cwd()
        self.version = "3.1"
        self.build_name = "多格式文档翻译助手-最新版"
        
    def print_header(self):
        """打印构建头部信息"""
        print("=" * 70)
        print(f"🚀 多格式文档翻译助手 v{self.version} - 最终封装")
        print("=" * 70)
        print()
        print("📋 本次封装包含的最新改进:")
        print("✅ 启动器不自动关闭功能")
        print("✅ 实时后台信息显示")
        print("✅ 服务器控制按钮")
        print("✅ 改进的UI布局")
        print("✅ 增强的日志显示")
        print("✅ 编码问题修复")
        print("✅ 完整的错误处理")
        print()
        
    def check_environment(self):
        """检查构建环境"""
        print("🔍 检查构建环境...")
        
        # 检查Python版本
        python_version = sys.version_info
        print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        if python_version < (3, 8):
            print("❌ 错误: 需要Python 3.8或更高版本")
            return False
            
        # 检查关键文件
        required_files = [
            "launcher.py",
            "web_server.py", 
            "main.py",
            "config.json",
            "requirements.txt"
        ]
        
        missing_files = []
        for file in required_files:
            if not Path(file).exists():
                missing_files.append(file)
                
        if missing_files:
            print(f"❌ 缺少关键文件: {', '.join(missing_files)}")
            return False
            
        print("✅ 环境检查通过")
        return True
        
    def install_pyinstaller(self):
        """安装PyInstaller"""
        print("📦 检查PyInstaller...")
        
        try:
            import PyInstaller
            print(f"✅ PyInstaller已安装: {PyInstaller.__version__}")
            return True
        except ImportError:
            print("📥 安装PyInstaller...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                             check=True, capture_output=True)
                print("✅ PyInstaller安装成功")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ PyInstaller安装失败: {e}")
                return False
                
    def clean_build_dirs(self):
        """清理构建目录"""
        print("🧹 清理旧的构建文件...")
        
        dirs_to_clean = ["build", "dist"]
        for dir_name in dirs_to_clean:
            if Path(dir_name).exists():
                shutil.rmtree(dir_name)
                print(f"删除: {dir_name}")
                
        print("✅ 清理完成")
        
    def create_spec_file(self):
        """创建PyInstaller规格文件"""
        print("📝 创建PyInstaller规格文件...")
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 数据文件
datas = [
    ('data', 'data'),
    ('web', 'web'),
    ('API_config', 'API_config'),
    ('config.json', '.'),
    ('web_server.py', '.'),
    ('main.py', '.'),
    ('services', 'services'),
    ('utils', 'utils'),
    ('ui', 'ui'),
    ('gui', 'gui'),
    ('tools', 'tools'),
    ('requirements.txt', '.'),
    ('logo.ico', '.'),
]

# 隐藏导入
hiddenimports = [
    'uvicorn',
    'fastapi',
    'jinja2',
    'starlette',
    'pydantic',
    'websockets',
    'python-multipart',
    'requests',
    'zhipuai',
    'ollama',
    'openpyxl',
    'python-docx',
    'PyPDF2',
    'pdfplumber',
    'Pillow',
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'threading',
    'asyncio',
    'json',
    'pathlib',
    'datetime',
    'logging',
    'subprocess',
    'webbrowser',
    'socket',
    'time',
    'os',
    'sys',
    'shutil',
    'traceback',
    'queue',
    'concurrent.futures',
]

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{self.build_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    cofile=None,
    icon='logo.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{self.build_name}',
)
'''
        
        spec_file = f"{self.build_name}.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
            
        print(f"✅ 规格文件已创建: {spec_file}")
        return spec_file
        
    def build_executable(self, spec_file):
        """构建可执行文件"""
        print("🔨 开始构建可执行文件...")
        print("注意: 这可能需要几分钟时间，请耐心等待...")
        
        try:
            cmd = [sys.executable, "-m", "PyInstaller", spec_file, "--clean", "--noconfirm"]
            
            print(f"执行命令: {' '.join(cmd)}")
            
            # 执行构建
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时显示输出
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(f"  {output.strip()}")
                    
            return_code = process.poll()
            
            if return_code == 0:
                print("✅ 构建成功!")
                return True
            else:
                print(f"❌ 构建失败，返回码: {return_code}")
                return False
                
        except Exception as e:
            print(f"❌ 构建过程中出现错误: {e}")
            return False
            
    def create_documentation(self):
        """创建使用文档"""
        print("📚 创建使用文档...")
        
        dist_dir = Path("dist") / self.build_name
        
        # 创建使用说明
        readme_content = f"""# {self.build_name} v{self.version}

## 🎯 最新改进

本版本包含以下重要改进：

### ✅ 启动器改进
- **不自动关闭**: 启动器保持运行，持续监控服务器状态
- **实时信息显示**: 完整显示Web服务器的后台运行信息
- **控制按钮**: 重启、停止、打开浏览器、清空日志等功能
- **改进UI**: 更大窗口，更好的布局和交互体验

### ✅ 日志系统改进
- **颜色分级**: 不同级别的日志使用不同颜色显示
- **智能过滤**: 过滤无用信息，只显示重要日志
- **实时同步**: 终端和Web界面日志完全同步

### ✅ 稳定性改进
- **编码修复**: 解决emoji字符导致的编码错误
- **错误处理**: 完善的异常处理和错误提示
- **资源管理**: 改进的进程和资源管理

## 🚀 使用方法

### 1. 启动程序
双击 `{self.build_name}.exe` 启动程序

### 2. 功能说明
- **自动启动**: 程序会自动启动Web服务器
- **实时监控**: 启动器显示详细的运行信息
- **控制管理**: 使用按钮控制服务器状态
- **Web访问**: 浏览器自动打开Web界面

### 3. 支持功能
- ✅ Word文档翻译
- ✅ PDF文档翻译  
- ✅ Excel表格翻译
- ✅ TXT文本翻译
- ✅ 术语库管理
- ✅ 多种翻译引擎支持

### 4. 翻译引擎
- 智谱AI (推荐)
- Ollama (本地)
- 硅基流动
- 内网翻译器

## 📝 注意事项

1. **首次使用**: 需要配置API密钥
2. **网络要求**: 在线翻译需要网络连接
3. **系统要求**: Windows 10及以上版本
4. **局域网访问**: 支持局域网内其他设备访问

## 🔧 故障排除

如果遇到问题：
1. 查看启动器的日志信息
2. 检查网络连接
3. 确认API密钥配置
4. 重启程序尝试

## 📞 技术支持

如需技术支持，请提供：
- 启动器显示的错误信息
- 操作系统版本
- 具体的操作步骤

---
版本: v{self.version}
构建时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        readme_path = dist_dir / "使用说明.txt"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
            
        print(f"✅ 使用说明已创建: {readme_path}")
        
    def verify_build(self):
        """验证构建结果"""
        print("🔍 验证构建结果...")
        
        dist_dir = Path("dist") / self.build_name
        exe_file = dist_dir / f"{self.build_name}.exe"
        
        if not exe_file.exists():
            print("❌ 可执行文件未找到")
            return False
            
        # 检查文件大小
        file_size = exe_file.stat().st_size / (1024 * 1024)  # MB
        print(f"可执行文件大小: {file_size:.1f} MB")
        
        # 检查关键目录
        required_dirs = ["_internal"]
        for dir_name in required_dirs:
            if not (dist_dir / dir_name).exists():
                print(f"❌ 缺少目录: {dir_name}")
                return False
                
        print("✅ 构建验证通过")
        return True
        
    def build(self):
        """执行完整构建流程"""
        self.print_header()
        
        # 检查环境
        if not self.check_environment():
            return False
            
        # 安装PyInstaller
        if not self.install_pyinstaller():
            return False
            
        # 清理旧文件
        self.clean_build_dirs()
        
        # 创建规格文件
        spec_file = self.create_spec_file()
        
        # 构建可执行文件
        if not self.build_executable(spec_file):
            return False
            
        # 创建文档
        self.create_documentation()
        
        # 验证构建
        if not self.verify_build():
            return False
            
        # 构建完成
        print()
        print("=" * 70)
        print("🎉 构建完成!")
        print("=" * 70)
        print(f"📁 输出目录: dist/{self.build_name}/")
        print(f"🚀 可执行文件: {self.build_name}.exe")
        print()
        print("📋 下一步:")
        print("1. 测试可执行文件")
        print("2. 检查所有功能是否正常")
        print("3. 准备分发给用户")
        print()
        
        return True

def main():
    """主函数"""
    builder = FinalBuilder()
    
    try:
        success = builder.build()
        if success:
            # 询问是否打开构建目录
            try:
                choice = input("是否打开构建目录? (y/n): ").lower().strip()
                if choice in ['y', 'yes', '是']:
                    import subprocess
                    subprocess.run(['explorer', f'dist\\{builder.build_name}'], shell=True)
            except KeyboardInterrupt:
                print("\n构建完成")
        else:
            print("构建失败，请检查错误信息")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n构建被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"构建过程中出现未预期的错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
