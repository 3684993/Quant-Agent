"""
测试所有改进功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.advanced_take_profit import advanced_take_profit
from core.formatted_output import formatted_output


def test_improvements():
    """测试所有改进功能"""
    print("=== 测试高级止盈策略 ===")
    
    # 测试1: 高级止盈策略
    symbol = "BTCUSDT"
    price = 70733.20
    
    # 模拟技术指标
    indicators = {
        "bollinger": {
            "upper": 72500.0,
            "lower": 68500.0,
            "middle": 70500.0
        },
        "atr": 800.0,
        "rsi": 65.0,
        "macd": {"macd": 150.0, "signal": 120.0, "histogram": 30.0}
    }
    
    # 模拟持仓信息（与您提供的日志一致）
    position_info = {
        "symbol": symbol,
        "side": "long",
        "current_price": price,
        "entry_price": 69923.10,
        "stop_loss": 69182.00,
        "take_profit": 72672.00,
        "hold_minutes": 36,
        "current_pnl_pct": 1.16,
        "has_position": True
    }
    
    market_summary = {
        "trend": "bullish",
        "momentum": "strengthening",
        "volatility": "medium"
    }
    
    # 测试高级止盈优化
    optimized_tp = advanced_take_profit.optimize_take_profit(
        price, indicators, position_info, market_summary
    )
    print(f"✅ 优化后的止盈价格: {optimized_tp:.2f}")
    
    # 测试收益委托判断
    should_trailing = advanced_take_profit.should_set_profit_trailing(36, 1.16)
    print(f"✅ 是否应该设置收益委托: {should_trailing}")
    
    print("\n=== 测试持仓显示（交易所格式） ===")
    
    # 测试持仓显示
    position_data = {
        "has_position": True,
        "symbol": symbol,
        "side": "long",
        "position_size": 0.0100,
        "entry_price": 69923.10,
        "current_price": 70733.20,
        "current_pnl": 10.56,  # 未实现盈亏（USDT）
        "current_pnl_pct": 1.16,  # 价格变动百分比
        "exchange_pnl_pct": 29.82,  # 交易所收益率
        "initial_margin": 35.42,  # 初始保证金
        "hold_minutes": 36
    }
    
    formatted_output.print_position_status(symbol, position_data)
    
    print("\n=== 测试AI决策显示 ===")
    
    # 测试AI决策显示
    decision_data = {
        "action": "hold",
        "entry_range": [70500.59, 70655.66],
        "stop_loss": 69182.00,
        "take_profit": optimized_tp,  # 使用优化后的止盈价格
        "confidence": 0.8
    }
    
    formatted_output.print_ai_decision(symbol, decision_data)
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_improvements()