@echo off
chcp 65001 >nul
echo.
echo ================================================
echo    AI量化交易实盘系统 - 监控模式
echo ================================================
echo.

REM 检查是否在正确目录
if not exist "main.py" (
    echo 错误: 请在 ai_quant_trader 目录下运行此脚本
    pause
    exit /b 1
)

echo 当前目录: %cd%
echo 当前时间: %date% %time%
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Python未找到，请先安装Python 3.x
    pause
    exit /b 1
)

echo 检查Python版本...
python -c "import sys; print('Python', sys.version.split()[0])"

REM 检查基本依赖
echo.
echo 检查依赖包...
python -c "import pandas" 2>nul
if errorlevel 1 (
    echo 安装pandas...
    pip install pandas
)

python -c "import psutil" 2>nul
if errorlevel 1 (
    echo 安装psutil...
    pip install psutil
)

REM 创建必要的目录
if not exist "reports" mkdir reports
if not exist "logs" mkdir logs

echo.
echo ================================================
echo    启动监控系统
echo ================================================
echo.
echo 说明:
echo  1. 系统将运行 main.py live
echo  2. 每30分钟自动生成运行报告
echo  3. 报告保存到 reports/ 目录
echo  4. 按 Ctrl+C 可停止系统
echo.
echo 正在启动...
echo.

REM 启动Python监控脚本
python simple_monitor.py

echo.
echo ================================================
echo    系统已停止
echo ================================================
echo.
echo 生成的报告文件:
echo.
dir reports\*.txt /b
echo.
echo 详细报告查看: reports\ 目录
echo 运行总结查看: reports\运行总结.md
echo.
echo 按任意键退出...
pause >nul