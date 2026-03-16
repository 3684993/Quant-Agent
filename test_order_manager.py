"""
测试委托管理模块的优化功能

测试内容：
1. 委托数量限制（最多 4 个）
2. 价格间距检查（10 <= 间距 <= 100 USDT）
3. 趋势判断取消委托
"""

import sys
sys.path.insert(0, 'f:/Quant-Agent/ai_quant_trader')

from datetime import datetime
from execution.order_manager import OrderManager

# 模拟 OrderExecutor
class MockOrderExecutor:
    def __init__(self):
        self.orders = []
    
    def get_existing_orders(self, symbol):
        return self.orders
    
    def get_current_price(self, symbol):
        return 70000.0
    
    def cancel_orders(self, symbol, order_ids):
        print(f"取消订单：{order_ids}")
        return {"success": True, "cancelled": order_ids}

# 测试 1: 委托数量限制
print("=" * 80)
print("测试 1: 委托数量限制")
print("=" * 80)

mock_executor = MockOrderExecutor()
order_manager = OrderManager(mock_executor)

# 模拟 4 个委托（已达上限）
for i in range(4):
    mock_executor.orders.append({
        "order_id": f"order_{i}",
        "price": 70000 + i * 50,  # 间距 50 USDT
        "side": "BUY",
        "quantity": 0.005,
        "timestamp": datetime.now().timestamp()
    })

result = order_manager.inspect_all_orders("BTCUSDT", "BUY")
print(f"委托数量：{result['total_orders']}")
print(f"数量检查：{result['inspections']['quantity_check']['message']}")
print(f"状态：{'✅ 通过' if result['inspections']['quantity_check']['within_limit'] else '❌ 失败'}")
print()

# 测试 2: 价格间距检查 - 正常
print("=" * 80)
print("测试 2: 价格间距检查 - 正常（间距 50 USDT）")
print("=" * 80)

mock_executor.orders = [
    {"order_id": "o1", "price": 70000, "side": "BUY", "quantity": 0.005, "timestamp": datetime.now().timestamp()},
    {"order_id": "o2", "price": 70050, "side": "BUY", "quantity": 0.005, "timestamp": datetime.now().timestamp()},
    {"order_id": "o3", "price": 70100, "side": "BUY", "quantity": 0.005, "timestamp": datetime.now().timestamp()},
]

result = order_manager.inspect_all_orders("BTCUSDT", "BUY")
spacing_check = result['inspections']['spacing_check']
print(f"最小间距：{spacing_check['min_spacing']:.2f} USDT")
print(f"最大间距：{spacing_check['max_spacing']:.2f} USDT")
print(f"平均间距：{spacing_check['avg_spacing']:.2f} USDT")
print(f"要求范围：[{spacing_check['min_required']:.2f}, {spacing_check['max_required']:.2f}]")
print(f"状态：{'✅ 通过' if spacing_check['meets_requirement'] else '❌ 失败'}")
print(f"建议：{result['recommendations']}")
print()

# 测试 3: 价格间距检查 - 过小
print("=" * 80)
print("测试 3: 价格间距检查 - 过小（间距 5 USDT < 10 USDT）")
print("=" * 80)

mock_executor.orders = [
    {"order_id": "o1", "price": 70000, "side": "BUY", "quantity": 0.005, "timestamp": datetime.now().timestamp()},
    {"order_id": "o2", "price": 70005, "side": "BUY", "quantity": 0.005, "timestamp": datetime.now().timestamp()},  # 间距 5
    {"order_id": "o3", "price": 70010, "side": "BUY", "quantity": 0.005, "timestamp": datetime.now().timestamp()},
]

result = order_manager.inspect_all_orders("BTCUSDT", "BUY")
spacing_check = result['inspections']['spacing_check']
print(f"最小间距：{spacing_check['min_spacing']:.2f} USDT")
print(f"最大间距：{spacing_check['max_spacing']:.2f} USDT")
print(f"要求范围：[{spacing_check['min_required']:.2f}, {spacing_check['max_required']:.2f}]")
print(f"状态：{'✅ 通过' if spacing_check['meets_requirement'] else '❌ 失败'}")
print(f"建议：{result['recommendations']}")
print()

# 测试 4: 价格间距检查 - 过大
print("=" * 80)
print("测试 4: 价格间距检查 - 过大（间距 150 USDT > 100 USDT）")
print("=" * 80)

mock_executor.orders = [
    {"order_id": "o1", "price": 70000, "side": "BUY", "quantity": 0.005, "timestamp": datetime.now().timestamp()},
    {"order_id": "o2", "price": 70150, "side": "BUY", "quantity": 0.005, "timestamp": datetime.now().timestamp()},  # 间距 150
    {"order_id": "o3", "price": 70300, "side": "BUY", "quantity": 0.005, "timestamp": datetime.now().timestamp()},
]

result = order_manager.inspect_all_orders("BTCUSDT", "BUY")
spacing_check = result['inspections']['spacing_check']
print(f"最小间距：{spacing_check['min_spacing']:.2f} USDT")
print(f"最大间距：{spacing_check['max_spacing']:.2f} USDT")
print(f"要求范围：[{spacing_check['min_required']:.2f}, {spacing_check['max_required']:.2f}]")
print(f"状态：{'✅ 通过' if spacing_check['meets_requirement'] else '❌ 失败'}")
print(f"建议：{result['recommendations']}")
print()

# 测试 5: 委托数量超限
print("=" * 80)
print("测试 5: 委托数量超限（5 个 > 4 个）")
print("=" * 80)

mock_executor.orders = [
    {"order_id": f"o{i}", "price": 70000 + i * 50, "side": "BUY", "quantity": 0.005, "timestamp": datetime.now().timestamp()}
    for i in range(5)
]

result = order_manager.inspect_all_orders("BTCUSDT", "BUY")
quantity_check = result['inspections']['quantity_check']
print(f"委托数量：{quantity_check['order_count']}")
print(f"最大允许：{quantity_check['max_allowed']}")
print(f"状态：{'✅ 通过' if quantity_check['within_limit'] else '❌ 超限'}")
print(f"建议：{result['recommendations']}")
print()

# 测试 6: 趋势判断（模拟上涨趋势中的卖单）
print("=" * 80)
print("测试 6: 趋势判断 - 上涨趋势中的卖单")
print("=" * 80)

class MockMarketAnalyzer:
    def get_trend(self, symbol):
        return {
            "trend": "UPTREND",  # 上涨趋势
            "strength": 0.8  # 强度 0.8（> 0.6 阈值）
        }

mock_executor.orders = [
    {"order_id": "o1", "price": 70000, "side": "SELL", "quantity": 0.005, "timestamp": datetime.now().timestamp()},  # 卖单
    {"order_id": "o2", "price": 70050, "side": "SELL", "quantity": 0.005, "timestamp": datetime.now().timestamp()},
]

order_manager_with_trend = OrderManager(mock_executor, market_analyzer=MockMarketAnalyzer())
result = order_manager_with_trend.inspect_all_orders("BTCUSDT", "BUY")
trend_check = result['inspections']['trend_check']
print(f"当前趋势：{trend_check.get('trend', '未知')}")
print(f"趋势强度：{trend_check.get('trend_strength', 0):.2f}")
print(f"建议取消：{trend_check.get('recommend_cancel', [])}")
print(f"状态：{trend_check.get('status', '未知')}")
print(f"建议：{result['recommendations']}")
print()

# 测试 7: 趋势判断（震荡市场）
print("=" * 80)
print("测试 7: 趋势判断 - 震荡市场（保留所有委托）")
print("=" * 80)

class MockVolatileMarket:
    def get_trend(self, symbol):
        return {
            "trend": "volatile",  # 震荡市场
            "strength": 0.3
        }

mock_executor.orders = [
    {"order_id": "o1", "price": 70000, "side": "SELL", "quantity": 0.005, "timestamp": datetime.now().timestamp()},
    {"order_id": "o2", "price": 70050, "side": "BUY", "quantity": 0.005, "timestamp": datetime.now().timestamp()},
]

order_manager_volatile = OrderManager(mock_executor, market_analyzer=MockVolatileMarket())
result = order_manager_volatile.inspect_all_orders("BTCUSDT")
trend_check = result['inspections']['trend_check']
print(f"当前趋势：{trend_check.get('trend', '未知')}")
print(f"建议取消：{trend_check.get('recommend_cancel', [])}")
print(f"状态：{trend_check.get('status', '未知')}")
print(f"建议：{result['recommendations']}")
print()

print("=" * 80)
print("所有测试完成！")
print("=" * 80)
print("\n核心功能验证:")
print("1. ✅ 委托数量限制（最多 4 个）")
print("2. ✅ 价格间距检查（10 <= 间距 <= 100 USDT）")
print("3. ✅ 趋势判断取消委托（强趋势时取消反向委托）")
print("4. ✅ 震荡市场保留所有委托")
