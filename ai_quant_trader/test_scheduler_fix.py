"""
测试scheduler修复后的系统
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.scheduler import Scheduler
from data.market_data import MarketDataService
from data.kline_cache import KlineCache
from execution.position_manager import PositionManager
from execution.order_executor import OrderExecutor
from core.logger import logger


def test_scheduler_fix():
    """测试scheduler修复后的系统"""
    print("=== 测试scheduler修复 ===")
    
    try:
        # 创建必要的组件实例
        market_data = MarketDataService()
        kline_cache = KlineCache()
        position_manager = PositionManager()
        
        # 创建scheduler实例
        scheduler = Scheduler(
            market_data_service=market_data,
            kline_cache=kline_cache,
            binance_client=None,  # 测试时不使用真实交易所连接
            position_manager=position_manager,
            interval=60
        )
        
        print("✅ scheduler实例创建成功")
        
        # 测试position_state变量作用域
        # 模拟一个简单的交易周期
        print("\n=== 测试交易周期执行 ===")
        
        # 模拟持仓状态
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
        
        # 测试profit_optimizer调用（这是之前出错的地方）
        from agents.profit_optimizer import ProfitOptimizer
        profit_optimizer = ProfitOptimizer()
        
        # 模拟技术指标
        indicators = {
            "price": {"close": 70500.0},
            "atr": 800.0,
            "bollinger": {"upper": 72000.0, "lower": 69000.0, "middle": 70500.0}
        }
        
        market_summary = {"trend": "bullish", "momentum": "strengthening"}
        regime = {"state": "trend_up"}
        
        # 测试调用（这是之前出错的地方）
        profit_result = profit_optimizer.optimize(
            indicators, market_summary, regime, test_position
        )
        
        print(f"✅ profit_optimizer调用成功")
        print(f"   止盈价格: {profit_result.get('take_profit', 0):.2f}")
        print(f"   止损价格: {profit_result.get('stop_loss', 0):.2f}")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_scheduler_fix()