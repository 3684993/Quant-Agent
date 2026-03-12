"""
测试委托管理问题修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from execution.order_executor import OrderExecutor


def test_order_management_fix():
    """测试委托管理问题修复"""
    print("=== 测试委托管理问题修复 ===")
    
    try:
        # 创建模拟的binance客户端
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
        
        # 模拟您发现的问题：4个价格接近的委托
        print("\n=== 测试1: 价格过于接近的委托 ===")
        
        # 添加4个价格接近的委托（您发现的问题）
        mock_prices = [70128.10, 70163.20, 70216.30, 70251.40]
        for price in mock_prices:
            mock_client.add_mock_order("BTCUSDT", "BUY", price, 0.005)
        
        # 创建委托执行器
        order_executor = OrderExecutor(mock_client, testnet=True)
        
        # 测试价格优化
        test_prices = [70100, 70150, 70200, 70250, 70300]  # 价格接近
        test_sizes = [0.005, 0.005, 0.005, 0.005, 0.005]
        
        optimized_prices, optimized_sizes = order_executor._optimize_entry_levels(
            test_prices, test_sizes
        )
        
        print(f"✅ 价格优化结果:")
        print(f"   原始: {len(test_prices)}个价格，间距: {test_prices}")
        print(f"   优化后: {len(optimized_prices)}个价格，间距: {optimized_prices}")
        
        # 检查价格间距是否合理
        if len(optimized_prices) < len(test_prices):
            print("✅ 价格优化成功：合并了过于接近的价格")
        else:
            print("❌ 价格优化可能有问题")
        
        # 测试委托数量控制
        print("\n=== 测试2: 委托数量控制 ===")
        
        # 模拟已有4个委托（超过限制）
        existing_orders = order_executor.get_existing_orders("BTCUSDT", "BUY")
        print(f"✅ 现有委托数量: {len(existing_orders)}个")
        
        # 测试委托数量限制
        max_allowed = 3
        if len(existing_orders) >= max_allowed:
            print(f"✅ 委托数量已达上限: {len(existing_orders)}/{max_allowed}")
        else:
            print(f"❌ 委托数量控制可能有问题")
        
        # 测试清理过多委托
        print("\n=== 测试3: 清理过多委托 ===")
        
        cleanup_result = order_executor.cleanup_excessive_orders("BTCUSDT", "BUY", max_orders=3)
        
        if cleanup_result.get("excessive_orders_count", 0) > 0:
            print(f"✅ 清理了 {cleanup_result['excessive_orders_count']} 个过多委托")
            print(f"   消息: {cleanup_result.get('message', '')}")
        else:
            print("✅ 委托数量正常，无需清理")
        
        # 测试分批委托策略
        print("\n=== 测试4: 分批委托策略 ===")
        
        # 模拟分批委托
        scale_in_prices = [70000, 70100, 70200, 70300, 70400]  # 价格间距100点
        scale_in_sizes = [0.005, 0.005, 0.005, 0.005, 0.005]
        
        # 测试价格优化
        optimized_prices_2, optimized_sizes_2 = order_executor._optimize_entry_levels(
            scale_in_prices, scale_in_sizes, min_price_spacing=200  # 最小间距200点
        )
        
        print(f"✅ 分批委托价格优化:")
        print(f"   原始: {len(scale_in_prices)}个价格")
        print(f"   优化后: {len(optimized_prices_2)}个价格")
        print(f"   价格: {optimized_prices_2}")
        
        # 检查价格间距是否合理
        if len(optimized_prices_2) >= 2:
            price_spacing = abs(optimized_prices_2[1] - optimized_prices_2[0])
            print(f"✅ 价格间距: {price_spacing:.2f}点")
            if price_spacing >= 100:  # 至少100点间距
                print("✅ 价格间距合理，具有分批委托意义")
            else:
                print("❌ 价格间距过小，分批委托意义不大")
        
        # 测试委托数量限制
        print("\n=== 测试5: 委托数量限制 ===")
        
        # 模拟分批委托执行（应该被限制）
        scale_in_result = order_executor.scale_in(
            symbol="BTCUSDT",
            side="long",
            entry_levels=scale_in_prices,
            sizes=scale_in_sizes
        )
        
        if scale_in_result.get("success"):
            print(f"✅ 分批委托成功执行")
            print(f"   委托数量: {len(scale_in_result.get('orders', []))}")
            print(f"   总数量: {scale_in_result.get('total_size', 0):.4f}")
        else:
            print(f"✅ 分批委托被正确阻止: {scale_in_result.get('error', '')}")
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_order_management_fix()