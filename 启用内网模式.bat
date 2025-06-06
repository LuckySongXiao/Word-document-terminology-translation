@echo off
chcp 65001 >nul
echo.
echo ========================================
echo 🌐 文档术语翻译助手 - 内网模式配置
echo ========================================
echo.

echo 📋 此脚本将配置程序在内网环境中运行
echo.
echo 🔧 内网模式特性：
echo    ✅ 跳过外部API连接检查
echo    ✅ 避免网络超时错误
echo    ✅ 优先使用本地Ollama服务
echo    ✅ 支持内网翻译API
echo.

set /p confirm="是否启用内网模式？(Y/N): "
if /i "%confirm%" neq "Y" (
    echo 操作已取消
    pause
    exit /b
)

echo.
echo 🔄 正在配置内网模式...

:: 设置环境变量
set INTRANET_MODE=true
set OFFLINE_MODE=false

:: 备份原配置文件
if exist config.json (
    copy config.json config.json.backup >nul
    echo ✅ 已备份原配置文件为 config.json.backup
)

:: 使用PowerShell修改JSON配置文件
powershell -Command "& {
    try {
        $configPath = 'config.json'
        if (Test-Path $configPath) {
            $config = Get-Content $configPath -Raw | ConvertFrom-Json
            
            # 确保environment节点存在
            if (-not $config.environment) {
                $config | Add-Member -Type NoteProperty -Name 'environment' -Value @{}
            }
            
            # 设置内网模式
            $config.environment.intranet_mode = $true
            $config.environment.offline_mode = $false
            $config.environment.skip_network_checks = $true
            
            # 保存配置
            $config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
            Write-Host '✅ 配置文件已更新'
        } else {
            Write-Host '❌ 未找到config.json文件'
            exit 1
        }
    } catch {
        Write-Host '❌ 配置更新失败:' $_.Exception.Message
        exit 1
    }
}"

if %errorlevel% neq 0 (
    echo.
    echo ❌ 配置失败，请检查config.json文件是否存在
    pause
    exit /b 1
)

echo.
echo ========================================
echo 🎉 内网模式配置完成！
echo ========================================
echo.
echo 📋 配置详情：
echo    • 内网模式：已启用
echo    • 跳过网络检查：已启用
echo    • 环境变量：INTRANET_MODE=true
echo.
echo 💡 使用说明：
echo    1. 现在可以正常启动程序
echo    2. 程序将跳过外部API连接检查
echo    3. 优先使用本地Ollama或内网API
echo    4. 如需恢复，运行"恢复外网模式.bat"
echo.
echo 🚀 可以开始使用翻译功能了！
echo.
pause
