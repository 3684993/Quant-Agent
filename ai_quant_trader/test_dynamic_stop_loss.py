"""
测试动态止损调整功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from risk.dynamic_stop_loss import dynamic_stop_loss


def test_dynamic_stop_loss():
    """测试动态止损调整功能"""
    print("=== 测试动态止损调整功能 ===")
    
    # 测试1: 趋势分析
    symbol = "BTCUSDT"
    current_price = 70000
    
    # 创建模拟历史价格数据（15分钟趋势向上）
    historical_prices = [
        69000, 69100, 69200, 69300, 69400, 69500, 69600, 69700, 69800, 69900,
        70000, 70100, 70200, 70300, 70400, 70500, 70600, 70700, 70800, 70900,
        71000, 71100, 71200, 71300, 71400, 71500, 71600, 71700, 71800, 71900
    ]
    
    trend_analysis = dynamic_stop_loss.analyze_15min_trend(symbol, current_price, historical_prices)
    print(f"✅ 趋势分析结果: {trend_analysis}")
    
    # 测试2: 多头持仓，趋势向上且盈利 - 应该收紧止损
    print("\n=== 测试多头持仓，趋势向上且盈利 ===")
    position_info = {
        "symbol": symbol,
        "side": "long",
        "current_price": 71000,
        "entry_price": 69000,
        "stop_loss": 68000,
        "take_profit": 72000,
        "hold_minutes": 30,  # 持仓30分钟
        "current_pnl_pct": 2.90  # 盈利2.9%
    }
    
    should_adjust = dynamic_stop_loss.should_adjust_stop_loss(symbol, position_info, trend_analysis)
    print(f"✅ 是否需要调整止损: {should_adjust}")
    
    if should_adjust:
        new_stop_loss = dynamic_stop_loss.calculate_new_stop_loss(symbol, position_info, trend_analysis, 200)
        print(f"✅ 新止损价格: {new_stop_loss:.2f}")
    
    # 测试3: 多头持仓，趋势转跌 - 应该立即调整止损
    print("\n=== 测试多头持仓，趋势转跌 ===")
    
    # 创建趋势向下的历史价格数据
    down_trend_prices = [
        72000, 71900, 71800, 71700, 71600, 71500, 71400, 71300, 71200, 71100,
        71000, 70900, 70800, 70700, 70600, 70500, 70400, 70300, 70200, 70100,
        70000, 69900, 69800, 69700, 69600, 69500, 69400, 69300, 69200, 69100
    ]
    
    down_trend_analysis = dynamic_stop_loss.analyze_15min_trend(symbol, current_price, down_trend_prices)
    print(f"✅ 下跌趋势分析: {down_trend_analysis}")
    
    position_info_down = {
        "symbol": symbol,
        "side": "long",
        "current_price": 70000,
        "entry_price": 71000,
        "stop_loss": 69000,
        "take_profit": 73000,
        "hold_minutes": 45,
        "current_pnl_pct": -1.41  # 亏损1.41%
    }
    
    should_adjust_down = dynamic_stop_loss.should_adjust_stop_loss(symbol, position_info_down, down_trend_analysis)
    print(f"✅ 是否需要调整止损（下跌趋势）: {should_adjust_down}")
    
    if should_adjust_down:
        new_stop_loss_down = dynamic_stop_loss.calculate_new_stop_loss(symbol, position_info_down, down_trend_analysis, 300)
        print(f"✅ 新止损价格（下跌趋势）: {new_stop_loss_down:.2f}")
    
    # 测试4: 空头持仓，趋势向下且盈利
    print("\n=== 测试空头持仓，趋势向下且盈利 ===")
    
    position_info_short = {
        "symbol": symbol,
        "side": "short",
        "current_price": 69000,
        "entry_price": 70000,
        "stop_loss": 71000,
        "take_profit": 68000,
        "hold_minutes": 25,
        "current_pnl_pct": 1.43  # 盈利1.43%
    }
    
    should_adjust_short = dynamic_stop_loss.should_adjust_stop_loss(symbol, position_info_short, down_trend_analysis)
    print(f"✅ 是否需要调整止损（空头）: {should_adjust_short}")
    
    if should_adjust_short:
        new_stop_loss_short = dynamic_stop_loss.calculate_new_stop_loss(symbol, position_info_short, down_trend_analysis, 250)
        print(f"✅ 新止损价格（空头）: {new_stop_loss_short:.2f}")
    
    # 测试5: 完整动态止损调整流程
    print("\n=== 测试完整动态止损调整流程 ===")
    
    adjustment_result = dynamic_stop_loss.dynamic_stop_loss_adjustment(
        symbol, position_info, historical_prices, 200
    )
    print(f"✅ 完整调整结果: {adjustment_result}")
    
    print("\n=== 所有测试完成 ===")


if __name__ == "__main__":
    test_dynamic_stop_loss()