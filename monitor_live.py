"""
直接运行量化交易系统并实时监控
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("f:/Quant-Agent/live_monitor.log")
ERROR_SUMMARY = Path("f:/Quant-Agent/error_summary.txt")

print("=" * 80)
print("🚀 量化交易系统 - 实时实盘监控")
print("=" * 80)
print(f"启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("监控内容：错误、警告、止盈委托、持仓、暴露量")
print("=" * 80)
print()

# 启动系统
process = subprocess.Popen(
    ["python", "-m", "ai_quant_trader.main", "live", "--use-ai"],
    cwd="f:/Quant-Agent",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    universal_newlines=True,
    encoding="utf-8",
    errors="ignore"
)

errors = []
warnings = []
tp_orders = []

try:
    while True:
        line = process.stdout.readline()
        if not line:
            if process.poll() is not None:
                break
            continue
            
        # 写入日志
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
        
        # 显示关键信息
        line_stripped = line.strip()
        
        # 错误
        if "ERROR" in line_stripped or "Error" in line_stripped:
            errors.append(line_stripped)
            print(f"\n❌ {datetime.now().strftime('%H:%M:%S')} - 错误：{line_stripped[:200]}")
        
        # 警告（特别是暴露量）
        elif "WARNING" in line_stripped:
            warnings.append(line_stripped)
            if "暴露量" in line_stripped or "EXPOSURE" in line_stripped or "EXPOSURE_LIMIT" in line_stripped:
                print(f"\n⚠️  {datetime.now().strftime('%H:%M:%S')} - 暴露量警告：{line_stripped[:200]}")
            elif "止盈" in line_stripped:
                print(f"\n⚠️  {datetime.now().strftime('%H:%M:%S')} - 警告：{line_stripped[:200]}")
        
        # 止盈委托
        elif "止盈委托" in line_stripped or "take_profit" in line_stripped:
            tp_orders.append(line_stripped)
            print(f"\n📋 {datetime.now().strftime('%H:%M:%S')} - 止盈：{line_stripped[:200]}")
        
        # 持仓
        elif "持仓" in line_stripped and ("LONG" in line_stripped or "SHORT" in line_stripped):
            print(f"\n💼 {datetime.now().strftime('%H:%M:%S')} - 持仓：{line_stripped[:200]}")
        
        # 委托
        elif "[ORDER]" in line_stripped:
            print(f"\n📝 {datetime.now().strftime('%H:%M:%S')} - 委托：{line_stripped[:200]}")
        
        # AI 决策
        elif "[AI_DECISION]" in line_stripped:
            print(f"\n🤖 {datetime.now().strftime('%H:%M:%S')} - AI: {line_stripped[:200]}")
            
        # 执行
        elif "[EXECUTION]" in line_stripped:
            print(f"\n⚡ {datetime.now().strftime('%H:%M:%S')} - 执行：{line_stripped[:200]}")
        
except KeyboardInterrupt:
    print("\n\n" + "=" * 80)
    print("🛑 监控停止")
    print("=" * 80)
    print(f"错误数量：{len(errors)}")
    print(f"警告数量：{len(warnings)}")
    print(f"止盈委托：{len(tp_orders)}")
    
    # 保存错误摘要
    with open(ERROR_SUMMARY, "w", encoding="utf-8") as f:
        f.write(f"监控时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"错误数量：{len(errors)}\n")
        f.write(f"警告数量：{len(warnings)}\n\n")
        
        if errors:
            f.write("=" * 80 + "\n")
            f.write("错误列表:\n")
            f.write("=" * 80 + "\n")
            for err in errors:
                f.write(f"{err}\n")
        
        if warnings:
            f.write("\n" + "=" * 80 + "\n")
            f.write("警告列表:\n")
            f.write("=" * 80 + "\n")
            for warn in warnings:
                f.write(f"{warn}\n")
    
    print(f"\n详细日志：{LOG_FILE}")
    print(f"错误摘要：{ERROR_SUMMARY}")
    process.terminate()
