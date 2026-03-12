@echo off
chcp 65001 > nul
echo.
echo ========================================
echo     AI量化交易实盘系统启动器
echo ========================================
echo.

REM 切换到项目目录
cd /d "d:\Quant Agent\ai_quant_trader"

echo [%date% %time%] 正在启动AI量化交易实盘系统...
echo.

REM 检查Python环境
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请确保Python已安装并添加到PATH
    pause
    exit /b 1
)

echo [%date% %time%] Python环境检查通过
echo.

REM 检查.env文件是否存在
if not exist ".env" (
    echo [警告] 未找到.env配置文件
    echo 请从根目录复制.env文件到当前目录
    copy "..\.env" ".env" > nul 2>&1
    if errorlevel 1 (
        echo [错误] 无法复制.env文件，请手动创建
        pause
        exit /b 1
    )
    echo [%date% %time%] 已复制.env配置文件
)

echo [%date% %time%] 启动实盘交易监控系统...
echo.
echo 系统特点:
echo   • 自动启动量化交易实盘系统
echo   • 每30分钟生成系统运行状态报告
echo   • 实时监控进程状态和系统资源
echo   • 自动保存运行日志和报告
echo.
echo 操作说明:
echo   • 按Ctrl+C可随时停止系统
echo   • 所有报告保存在logs/目录下
echo   • 系统将每30分钟自动生成报告
echo.
echo ========================================
echo.

REM 启动监控系统
python monitor.py

echo.
echo [%date% %time%] 系统已停止
echo 报告文件保存在: d:\Quant Agent\ai_quant_trader\logs\
echo.
pause