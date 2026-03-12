@echo off
echo ========================================
echo   AI量化交易实盘系统 - 监控模式启动
echo ========================================
echo.
echo 当前时间: %date% %time%
echo.

REM 检查Python环境
python --version
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

REM 检查依赖
echo.
echo 检查Python依赖...
python -c "import psutil, pandas, numpy, requests" 2>nul
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 依赖安装失败
        pause
        exit /b 1
    )
)

REM 创建日志目录
if not exist logs mkdir logs
if not exist reports mkdir reports

REM 启动监控系统
echo.
echo 启动AI量化交易实盘系统监控器...
echo 系统将每30分钟自动生成详细运行报告
echo 按Ctrl+C可停止系统
echo.

python enhanced_monitor.py

echo.
echo ========================================
echo   系统已停止
echo ========================================
echo.
echo 生成的报告和日志：
echo   - logs/           - 系统日志
echo   - reports/        - 监控报告
echo   - reports/dashboard.html - 实时监控面板
echo.
echo 按任意键退出...
pause >nul