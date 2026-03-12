#!/usr/bin/env python3
"""
测试真实的技术指标数据结构
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from core.formatted_output import formatted_output
from datetime import datetime

def test_real_indicators():
    """测试真实的技术指标数据结构"""
    print("🧪 测试真实的技术指标数据结构...\n")
    
    # 模拟真实的技术指标数据结构
    real_indicators = {
        "rsi": 65.5,  # 单个浮点数
        "atr": 850.2,  # 单个浮点数
        "macd": {  # 字典结构
            "macd": -120.5,
            "signal": -110.2,
            "hist": -10.3
        },
        "bollinger": {  # 字典结构
            "upper": 71000.0,
            "middle": 69500.0,
            "lower": 68000.0
        },
        "ema": {  # 字典结构
            "ema9": 69800.0,
            "ema21": 69200.0
        },
        "momentum": {  # 字典结构
            "price_change_1m": 0.001,
            "price_change_5m": 0.015,
            "price_change_15m": 0.025
        },
        "market_regime": {  # 字典结构
            "state": "volatile",
            "trend_strength": 0.0022
        }
    }
    
    # 测试周期头部
    formatted_output.print_cycle_header(1, datetime.now())
    
    # 测试市场状态
    formatted_output.print_market_status("BTCUSDT", 69410.80, 93.0, "volatile")
    
    # 测试技术指标（使用真实数据结构）
    formatted_output.print_indicators("BTCUSDT", real_indicators)
    
    # 测试持仓状态
    position = {
        "has_position": True,
        "side": "long",
        "position_size": 0.01,
        "entry_price": 69243.62,
        "current_price": 69410.80,
        "current_pnl_pct": 0.24,
        "hold_minutes": 0
    }
    formatted_output.print_position_status("BTCUSDT", position)
    
    # 测试AI决策
    decision = {
        "action": "close_position",
        "entry_range": [69459.24, 69568.01],
        "stop_loss": 68535.0,
        "take_profit": 70982.0,
        "confidence": 0.80
    }
    formatted_output.print_ai_decision("BTCUSDT", decision)
    
    # 测试执行结果 - 成功平仓
    exec_result = {
        "success": True,
        "action": "close_position",
        "pnl_pct": 0.24
    }
    formatted_output.print_execution_result("BTCUSDT", exec_result)
    
    # 测试周期结束
    formatted_output.print_cycle_footer(1, 1.64)
    
    print("\n✅ 真实技术指标测试完成！")

if __name__ == "__main__":
    test_real_indicators()