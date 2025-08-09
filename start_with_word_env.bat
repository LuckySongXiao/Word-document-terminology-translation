@echo off
REM 启动脚本 - 使用word环境运行程序
echo 正在启动文档术语翻译助手...

REM 设置环境变量
set CONDA_DEFAULT_ENV=word
set CONDA_PREFIX=C:\ProgramData\anaconda3\envs\word
set PATH=C:\ProgramData\anaconda3\envs\word;C:\ProgramData\anaconda3\envs\word\Scripts;%PATH%

REM 切换到项目目录
cd /d "d:\AI_project\文档术语翻译V3"

REM 使用word环境的Python运行程序
echo 使用word环境启动GUI...
C:\ProgramData\anaconda3\envs\word\python.exe main.py

pause
