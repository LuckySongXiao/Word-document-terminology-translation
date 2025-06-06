@echo off
chcp 65001 >nul
echo.
echo ========================================
echo 🌍 文档术语翻译助手 - 外网模式恢复
echo ========================================
echo.

echo 📋 此脚本将恢复程序的外网模式配置
echo.
echo 🔧 外网模式特性：
echo    ✅ 启用外部API连接检查
echo    ✅ 支持智谱AI等在线服务
echo    ✅ 完整的网络功能
echo.

set /p confirm="是否恢复外网模式？(Y/N): "
if /i "%confirm%" neq "Y" (
    echo 操作已取消
    pause
    exit /b
)

echo.
echo 🔄 正在恢复外网模式...

:: 清除环境变量
set INTRANET_MODE=
set OFFLINE_MODE=

:: 检查是否有备份文件
if exist config.json.backup (
    set /p restore_backup="发现配置备份文件，是否恢复备份？(Y/N): "
    if /i "!restore_backup!" equ "Y" (
        copy config.json.backup config.json >nul
        echo ✅ 已从备份恢复配置文件
        goto :success
    )
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
            
            # 设置外网模式
            $config.environment.intranet_mode = $false
            $config.environment.offline_mode = $false
            $config.environment.skip_network_checks = $false
            
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

:success
echo.
echo ========================================
echo 🎉 外网模式恢复完成！
echo ========================================
echo.
echo 📋 配置详情：
echo    • 内网模式：已禁用
echo    • 跳过网络检查：已禁用
echo    • 环境变量：已清除
echo.
echo 💡 使用说明：
echo    1. 现在程序将正常进行网络连接检查
echo    2. 支持智谱AI等在线翻译服务
echo    3. 需要确保网络连接正常
echo    4. 如需重新启用内网模式，运行"启用内网模式.bat"
echo.
echo 🌍 外网模式已就绪！
echo.
pause
