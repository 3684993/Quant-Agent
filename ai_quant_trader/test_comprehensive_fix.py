"""
测试综合修复效果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.advanced_take_profit import advanced_take_profit
from ai.decision_engine import DecisionEngine


def test_advanced_take_profit_fix():
    """测试高级止盈策略修复"""
    print("=== 测试高级止盈策略修复 ===")
    
    try:
        # 模拟持仓70分钟，盈利0.47%的情况
        price = 70251.40
        pnl_pct = 0.47
        hold_minutes = 70
        side = "long"
        market_summary = {"trend": "neutral"}
        
        # 测试时间策略止盈
        time_tp = advanced_take_profit._time_based_take_profit(
            price, pnl_pct, hold_minutes, side, market_summary
        )
        
        print(f"✅ 时间策略止盈: {time_tp:.2f}")
        print(f"   当前价格: {price:.2f}")
        print(f"   目标涨幅: {(time_tp/price - 1)*100:.2f}%")
        
        # 测试完整止盈优化
        indicators = {
            "price": {"close": price},
            "bollinger": {"upper": 70602.66, "lower": 69000.00, "middle": 69800.00},
            "atr": 800.0
        }
        
        profit_result = advanced_take_profit.optimize_take_profit(
            indicators, market_summary, side, hold_minutes, pnl_pct
        )
        
        print(f"✅ 完整止盈优化: {profit_result:.2f}")
        print(f"   目标涨幅: {(profit_result/price - 1)*100:.2f}%")
        
        # 验证止盈价格合理性
        if profit_result < 75000:  # 确保止盈价格合理
            print("✅ 止盈价格设置合理")
        else:
            print("❌ 止盈价格仍然过高")
            
        print("\n=== 高级止盈策略测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_decision_engine_fix():
    """测试AI决策引擎修复"""
    print("\n=== 测试AI决策引擎修复 ===")
    
    try:
        # 创建决策引擎实例
        decision_engine = DecisionEngine()
        
        # 模拟持仓70分钟，达到预期持仓时间的情况
        context = {
            "price": 70251.40,
            "indicators": {
                "bollinger": {"upper": 70602.66, "lower": 69000.00, "middle": 69800.00},
                "atr": 800.0,
                "rsi": 55.0,
                "macd": {"macd": 0.5, "signal": 0.3, "histogram": 0.2}
            },
            "market_summary": {
                "trend": "neutral",
                "macd_signal": "neutral",
                "momentum": "weak"
            },
            "profit_optimizer": {
                "optimal_entry": [69972.12, 70158.31],
                "stop_loss": 68390.00,
                "take_profit": 70602.66
            },
            "position": {
                "has_position": True,
                "side": "long",
                "position_size": 0.01,
                "target_size": 0.01,
                "hold_minutes": 70,
                "expected_hold_minutes": 60,
                "current_pnl_pct": 0.47
            }
        }
        
        # 生成决策
        decision = decision_engine.generate_decision("BTCUSDT", context)
        
        print(f"✅ AI决策生成成功")
        print(f"   动作: {decision.get('action', 'unknown')}")
        print(f"   止损: {decision.get('stop_loss', 0):.2f}")
        print(f"   止盈: {decision.get('take_profit', 0):.2f}")
        
        # 验证决策合理性
        if decision.get("action") == "close_position":
            print("✅ 决策正确：持仓时间达到预期，执行平仓")
        else:
            print(f"⚠️ 决策可能有问题：持仓70分钟但动作是 {decision.get('action')}")
            
        print("\n=== AI决策引擎测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_profit_trailing():
    """测试收益委托判断"""
    print("\n=== 测试收益委托判断 ===")
    
    try:
        # 测试持仓70分钟，盈利0.47%的情况
        should_trailing = advanced_take_profit.should_set_profit_trailing(70, 0.47)
        
        print(f"✅ 收益委托判断: {should_trailing}")
        print(f"   持仓时间: 70分钟")
        print(f"   盈利: 0.47%")
        
        if should_trailing:
            print("✅ 正确：持仓超过60分钟，建议设置收益委托")
        else:
            print("❌ 错误：应该建议设置收益委托")
            
        print("\n=== 收益委托测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_advanced_take_profit_fix()
    test_decision_engine_fix()
    test_profit_trailing()
    print("\n🎉 所有测试完成！")