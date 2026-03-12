"""
简单测试scheduler修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.profit_optimizer import ProfitOptimizer


def test_simple_fix():
    """简单测试修复后的系统"""
    print("=== 简单测试scheduler修复 ===")
    
    try:
        # 测试profit_optimizer调用（这是之前出错的地方）
        profit_optimizer = ProfitOptimizer()
        
        # 模拟技术指标
        indicators = {
            "price": {"close": 70500.0},
            "atr": 800.0,
            "bollinger": {"upper": 72000.0, "lower": 69000.0, "middle": 70500.0}
        }
        
        market_summary = {"trend": "bullish", "momentum": "strengthening"}
        regime = {"state": "trend_up"}
        
        # 测试1: 无持仓时的调用
        print("\n=== 测试1: 无持仓调用 ===")
        profit_result_no_position = profit_optimizer.optimize(
            indicators, market_summary, regime
        )
        print(f"✅ 无持仓调用成功")
        print(f"   止盈价格: {profit_result_no_position.get('take_profit', 0):.2f}")
        
        # 测试2: 有持仓时的调用
        print("\n=== 测试2: 有持仓调用 ===")
        test_position = {
            "has_position": True,
            "symbol": "BTCUSDT",
            "side": "long",
            "position_size": 0.01,
            "entry_price": 70000.0,
            "current_price": 70500.0,
            "current_pnl": 50.0,
            "current_pnl_pct": 0.71,
            "exchange_pnl_pct": 14.29,
            "initial_margin": 350.0,
            "hold_minutes": 36
        }
        
        profit_result_with_position = profit_optimizer.optimize(
            indicators, market_summary, regime, test_position
        )
        print(f"✅ 有持仓调用成功")
        print(f"   止盈价格: {profit_result_with_position.get('take_profit', 0):.2f}")
        
        # 测试3: 检查是否使用了高级止盈策略
        print("\n=== 测试3: 高级止盈策略检查 ===")
        if profit_result_no_position.get('take_profit') != profit_result_with_position.get('take_profit'):
            print("✅ 高级止盈策略生效 - 有持仓和无持仓的止盈价格不同")
        else:
            print("⚠️ 高级止盈策略可能未生效")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_simple_fix()