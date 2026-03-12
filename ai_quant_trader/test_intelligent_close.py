"""
测试智能平仓决策系统
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.intelligent_close_decision import intelligent_close_decision


def test_intelligent_close_decision():
    """测试智能平仓决策系统"""
    print("=== 测试智能平仓决策系统 ===")
    
    try:
        # 测试1: 高收益短持仓（应该平仓）
        print("\n=== 测试1: 高收益短持仓 ===")
        position_1 = {
            "has_position": True,
            "side": "long",
            "hold_minutes": 25,
            "current_pnl_pct": 0.08,  # 8%收益
            "exchange_pnl_pct": 20.0,
            "initial_margin": 35.0,
            "expected_hold_minutes": 60
        }
        
        indicators_1 = {
            "rsi": 65,
            "macd": {"macd": 0.5},
            "atr": 800,
            "bollinger": {"width": 2000}
        }
        
        market_summary_1 = {
            "trend": "bullish",
            "momentum": "strengthening",
            "volatility": "normal"
        }
        
        result_1 = intelligent_close_decision.should_close_position(
            position_1, indicators_1, market_summary_1, False
        )
        
        should_close, reason, priority = result_1
        print(f"✅ 决策: {'平仓' if should_close else '持仓'}")
        print(f"   原因: {reason}")
        print(f"   优先级: {priority:.2f}")
        
        # 测试2: 持仓时间过短且收益不佳（应该持仓）
        print("\n=== 测试2: 持仓时间过短且收益不佳 ===")
        position_2 = {
            "has_position": True,
            "side": "long",
            "hold_minutes": 10,
            "current_pnl_pct": 0.005,  # 0.5%收益
            "exchange_pnl_pct": 1.5,
            "initial_margin": 35.0,
            "expected_hold_minutes": 60
        }
        
        result_2 = intelligent_close_decision.should_close_position(
            position_2, indicators_1, market_summary_1, False
        )
        
        should_close, reason, priority = result_2
        print(f"✅ 决策: {'平仓' if should_close else '持仓'}")
        print(f"   原因: {reason}")
        print(f"   优先级: {priority:.2f}")
        
        # 测试3: 趋势改变（应该平仓）
        print("\n=== 测试3: 趋势改变 ===")
        position_3 = {
            "has_position": True,
            "side": "long",
            "hold_minutes": 40,
            "current_pnl_pct": 0.02,  # 2%收益
            "exchange_pnl_pct": 6.0,
            "initial_margin": 35.0,
            "expected_hold_minutes": 60
        }
        
        result_3 = intelligent_close_decision.should_close_position(
            position_3, indicators_1, market_summary_1, True  # 趋势改变
        )
        
        should_close, reason, priority = result_3
        print(f"✅ 决策: {'平仓' if should_close else '持仓'}")
        print(f"   原因: {reason}")
        print(f"   优先级: {priority:.2f}")
        
        # 测试4: 强制止损（应该平仓）
        print("\n=== 测试4: 强制止损 ===")
        position_4 = {
            "has_position": True,
            "side": "long",
            "hold_minutes": 50,
            "current_pnl_pct": -0.04,  # -4%亏损
            "exchange_pnl_pct": -12.0,
            "initial_margin": 35.0,
            "expected_hold_minutes": 60
        }
        
        result_4 = intelligent_close_decision.should_close_position(
            position_4, indicators_1, market_summary_1, False
        )
        
        should_close, reason, priority = result_4
        print(f"✅ 决策: {'平仓' if should_close else '持仓'}")
        print(f"   原因: {reason}")
        print(f"   优先级: {priority:.2f}")
        
        # 测试5: 趋势强度分析
        print("\n=== 测试5: 趋势强度分析 ===")
        trend_analysis = intelligent_close_decision.analyze_trend_strength(
            indicators_1, market_summary_1
        )
        
        print(f"✅ 趋势强度: {trend_analysis.get('strength_level')}")
        print(f"   趋势分数: {trend_analysis.get('trend_score'):.2f}")
        print(f"   可靠性: {trend_analysis.get('reliability')}")
        
        # 测试6: 净利润计算
        print("\n=== 测试6: 净利润计算 ===")
        net_profit_1 = intelligent_close_decision._calculate_net_profit(0.08, 25)  # 8%收益，25分钟
        net_profit_2 = intelligent_close_decision._calculate_net_profit(0.02, 10)  # 2%收益，10分钟
        net_profit_3 = intelligent_close_decision._calculate_net_profit(-0.03, 30)  # -3%亏损，30分钟
        
        print(f"✅ 净利润计算:")
        print(f"   8%收益25分钟 -> 净利润: {net_profit_1:.3f}")
        print(f"   2%收益10分钟 -> 净利润: {net_profit_2:.3f}")
        print(f"   -3%亏损30分钟 -> 净利润: {net_profit_3:.3f}")
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_intelligent_close_decision()