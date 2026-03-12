#!/usr/bin/env python3
"""
测试新的格式化输出功能
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from core.formatted_output import formatted_output
from datetime import datetime

def test_formatted_output():
    """测试格式化输出功能"""
    print("🧪 测试新的格式化输出功能...\n")
    
    # 测试系统状态
    formatted_output.print_system_status("live", ["BTCUSDT", "ETHUSDT"], 60)
    
    # 测试周期头部
    formatted_output.print_cycle_header(1, datetime.now())
    
    # 测试市场状态
    formatted_output.print_market_status("BTCUSDT", 70000.50, 15.8, "bullish")
    
    # 测试技术指标
    indicators = {
        'rsi': 65.5,
        'macd': 120.3,
        'atr': 850.2
    }
    formatted_output.print_indicators("BTCUSDT", indicators)
    
    # 测试持仓状态 - 无持仓
    formatted_output.print_position_status("BTCUSDT", {"has_position": False})
    
    # 测试持仓状态 - 有持仓
    position = {
        "has_position": True,
        "side": "long",
        "position_size": 0.02,
        "entry_price": 69500.0,
        "current_price": 70000.5,
        "current_pnl_pct": 0.72,
        "hold_minutes": 45
    }
    formatted_output.print_position_status("BTCUSDT", position)
    
    # 测试AI决策
    decision = {
        "action": "open_long",
        "entry_range": [69800.0, 70200.0],
        "stop_loss": 68500.0,
        "take_profit": 72000.0,
        "confidence": 0.85
    }
    formatted_output.print_ai_decision("BTCUSDT", decision)
    
    # 测试执行结果 - 成功开仓
    exec_result = {
        "success": True,
        "action": "open_long",
        "size": 0.01,
        "price": 70050.0
    }
    formatted_output.print_execution_result("BTCUSDT", exec_result)
    
    # 测试止盈止损信息
    sl_tp_result = {
        "mode": "local_simulation",
        "stop_loss": 68500.0,
        "take_profit": 72000.0
    }
    formatted_output.print_sl_tp_info("BTCUSDT", sl_tp_result)
    
    # 测试学习统计
    stats = {
        "win_rate": 0.78,
        "profit_factor": 2.5,
        "avg_hold": 35,
        "total_pnl": 15.2
    }
    formatted_output.print_learning_stats("BTCUSDT", stats)
    
    # 测试周期结束
    formatted_output.print_cycle_footer(1, 2.5)
    
    # 测试警告和错误
    formatted_output.print_warning("这是一个警告信息")
    formatted_output.print_error("这是一个错误信息")
    
    print("\n✅ 格式化输出测试完成！")

if __name__ == "__main__":
    test_formatted_output()