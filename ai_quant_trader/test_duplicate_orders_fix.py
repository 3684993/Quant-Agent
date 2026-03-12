"""
测试重复委托问题修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from execution.order_executor import OrderExecutor
from exchange.binance_client import BinanceClient


def test_duplicate_orders_fix():
    """测试重复委托问题修复"""
    print("=== 测试重复委托问题修复 ===")
    
    try:
        # 创建模拟的binance客户端（测试模式）
        class MockBinanceClient:
            def __init__(self):
                self.mock_orders = []
                
            def get_open_orders(self, symbol=None):
                """模拟查询活跃订单"""
                return self.mock_orders
                
            def add_mock_order(self, symbol, side, price, quantity):
                """添加模拟订单"""
                self.mock_orders.append({
                    "orderId": f"mock_{len(self.mock_orders)}",
                    "symbol": symbol,
                    "side": side,
                    "price": str(price),
                    "origQty": str(quantity),
                    "status": "NEW"
                })
        
        # 创建模拟客户端
        mock_client = MockBinanceClient()
        
        # 模拟7个价格接近的买入订单（您发现的问题）
        base_price = 70000.0
        for i in range(7):
            price = base_price + i * 10  # 价格非常接近
            mock_client.add_mock_order("BTCUSDT", "BUY", price, 0.005)
        
        # 创建委托执行器
        order_executor = OrderExecutor(mock_client, testnet=True)
        
        # 测试1: 查询现有订单
        print("\n=== 测试1: 查询现有订单 ===")
        existing_orders = order_executor.get_existing_orders("BTCUSDT", "BUY")
        print(f"✅ 查询到 {len(existing_orders)} 个活跃订单")
        
        for order in existing_orders:
            print(f"   订单: {order['side']} {order['quantity']:.4f} @ {order['price']:.2f}")
        
        # 测试2: 检查重复委托
        print("\n=== 测试2: 检查重复委托 ===")
        test_price = 70050.0  # 与现有订单价格接近
        test_size = 0.005
        
        is_duplicate = order_executor.check_duplicate_orders(
            "BTCUSDT", "BUY", test_price, test_size
        )
        
        print(f"✅ 重复委托检查: {is_duplicate}")
        
        if is_duplicate:
            print("✅ 正确检测到重复委托")
        else:
            print("❌ 未能检测到重复委托")
        
        # 测试3: 尝试委托（应该被阻止）
        print("\n=== 测试3: 尝试委托（应该被阻止） ===")
        result = order_executor.open_position(
            symbol="BTCUSDT",
            side="long",
            size=0.005,
            order_type="limit",
            price=70050.0
        )
        
        if result.get("duplicate"):
            print("✅ 委托被正确阻止（重复委托检测生效）")
            print(f"   错误信息: {result.get('error')}")
        else:
            print("❌ 委托未被阻止（重复委托检测失效）")
        
        # 测试4: 清理重复委托逻辑
        print("\n=== 测试4: 清理重复委托逻辑 ===")
        
        # 模拟调度器的重复委托检查逻辑
        duplicate_count = 0
        for order in existing_orders:
            order_price = order.get("price", 0)
            order_side = order.get("side", "")
            order_size = order.get("quantity", 0)
            
            for other_order in existing_orders:
                if order["order_id"] != other_order["order_id"]:
                    other_price = other_order.get("price", 0)
                    price_diff_pct = abs(order_price - other_price) / max(order_price, other_price)
                    
                    if (price_diff_pct <= 0.005 and 
                        order_side == other_order.get("side", "") and
                        abs(order_size - other_order.get("quantity", 0)) / max(order_size, other_order.get("quantity", 0)) <= 0.1):
                        duplicate_count += 1
                        print(f"✅ 发现重复委托: {order_side} {order_size:.4f} @ {order_price:.2f}")
        
        if duplicate_count > 0:
            print(f"✅ 发现 {duplicate_count} 个重复委托")
        else:
            print("❌ 未发现重复委托")
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_duplicate_orders_fix()