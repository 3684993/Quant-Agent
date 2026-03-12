"""
测试持仓时间修复功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from utils.position_time_utils import position_time_utils
from execution.position_manager import PositionManager


def test_position_time_utils():
    """测试持仓时间工具类"""
    print("=== 测试持仓时间工具类 ===")
    
    # 测试1: 更新持仓时间
    symbol = "BTCUSDT"
    test_time = datetime.now() - timedelta(minutes=30)  # 30分钟前开仓
    
    position_time_utils.update_position_entry_time(symbol, test_time)
    print(f"✅ 更新持仓时间: {symbol} 开仓时间 {test_time}")
    
    # 测试2: 计算持仓时间
    hold_minutes = position_time_utils.calculate_hold_minutes_with_fallback(
        symbol, None, test_time
    )
    print(f"✅ 计算持仓时间: {hold_minutes} 分钟")
    
    # 测试3: 模拟系统重启后恢复持仓时间
    print("\n=== 模拟系统重启后恢复持仓时间 ===")
    
    # 创建新的PositionManager实例（模拟重启）
    pm = PositionManager()
    
    # 模拟持仓信息
    position_info = {
        "symbol": symbol,
        "side": "long",
        "current_price": 70000,
        "entry_price": 69000,
        "stop_loss": 68000,
        "take_profit": 71000,
        "hold_minutes": 0,  # 模拟持仓时间丢失
        "current_pnl_pct": 1.45
    }
    
    # 测试动态止损调整（需要历史价格数据）
    historical_prices = [69000, 69100, 69200, 69300, 69400, 69500, 69600, 69700, 69800, 69900, 70000]
    atr = 200  # 模拟ATR
    
    adjustment_result = pm.dynamic_adjust_stop_loss(symbol, historical_prices, atr)
    print(f"✅ 动态止损调整测试: {adjustment_result}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_position_time_utils()