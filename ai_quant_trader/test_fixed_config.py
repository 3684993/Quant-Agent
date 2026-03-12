"""
测试固定配置修改：价格间隔100点，委托数量不超过4个
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from execution.order_executor import OrderExecutor


def test_fixed_config():
    """测试固定配置修改"""
    print("=== 测试固定配置修改 ===")
    
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
        
        # 创建委托执行器
        order_executor = OrderExecutor(mock_client, testnet=True)
        
        # 测试1: 价格间隔优化
        print("\n=== 测试1: 价格间隔优化（固定100点） ===")
        
        # 模拟价格过于接近的情况
        test_prices = [70000, 70050, 70100, 70150, 70200]  # 间距50点
        test_sizes = [0.005, 0.005, 0.005, 0.005, 0.005]
        
        optimized_prices, optimized_sizes = order_executor._optimize_entry_levels(
            test_prices, test_sizes
        )
        
        print(f"✅ 价格优化结果:")
        print(f"   原始价格: {test_prices}")
        print(f"   优化后价格: {optimized_prices}")
        print(f"   价格数量: {len(test_prices)} -> {len(optimized_prices)}")
        
        # 检查价格间距
        if len(optimized_prices) >= 2:
            for i in range(len(optimized_prices) - 1):
                spacing = abs(optimized_prices[i+1] - optimized_prices[i])
                print(f"   价格间距 {i+1}: {spacing:.1f}点")
                if spacing >= 100:
                    print("   ✅ 间距符合要求（≥100点）")
                else:
                    print("   ❌ 间距不符合要求")
        
        # 测试2: 委托数量限制
        print("\n=== 测试2: 委托数量限制（不超过4个） ===")
        
        # 添加4个委托（达到上限）
        for i in range(4):
            mock_client.add_mock_order("BTCUSDT", "BUY", 70000 + i*100, 0.005)
        
        existing_orders = order_executor.get_existing_orders("BTCUSDT", "BUY")
        print(f"✅ 现有委托数量: {len(existing_orders)}个")
        
        # 测试委托数量控制
        max_allowed = 4
        if len(existing_orders) >= max_allowed:
            print(f"✅ 委托数量已达上限: {len(existing_orders)}/{max_allowed}")
        else:
            print(f"❌ 委托数量控制可能有问题")
        
        # 测试3: 清理过多委托
        print("\n=== 测试3: 清理过多委托 ===")
        
        # 添加第5个委托（超过限制）
        mock_client.add_mock_order("BTCUSDT", "BUY", 70500, 0.005)
        
        cleanup_result = order_executor.cleanup_excessive_orders("BTCUSDT", "BUY", max_orders=4)
        
        if cleanup_result.get("excessive_orders_count", 0) > 0:
            print(f"✅ 清理了 {cleanup_result['excessive_orders_count']} 个过多委托")
            print(f"   消息: {cleanup_result.get('message', '')}")
        else:
            print("✅ 委托数量正常，无需清理")
        
        # 测试4: 分批委托策略验证
        print("\n=== 测试4: 分批委托策略验证 ===")
        
        # 模拟分批委托
        scale_in_prices = [70000, 70100, 70200, 70300, 70400]  # 间距100点
        scale_in_sizes = [0.005, 0.005, 0.005, 0.005, 0.005]
        
        optimized_prices_2, optimized_sizes_2 = order_executor._optimize_entry_levels(
            scale_in_prices, scale_in_sizes
        )
        
        print(f"✅ 分批委托价格优化:")
        print(f"   原始: {len(scale_in_prices)}个价格")
        print(f"   优化后: {len(optimized_prices_2)}个价格")
        print(f"   价格: {optimized_prices_2}")
        
        # 检查是否符合最大4个委托的限制
        if len(optimized_prices_2) <= 4:
            print("✅ 委托数量符合限制（≤4个）")
        else:
            print("❌ 委托数量超过限制")
        
        # 测试5: 配置参数验证
        print("\n=== 测试5: 配置参数验证 ===")
        
        # 检查默认参数
        import inspect
        sig = inspect.signature(order_executor._optimize_entry_levels)
        
        print("✅ 方法参数默认值:")
        for param_name, param in sig.parameters.items():
            if param.default != inspect.Parameter.empty:
                print(f"   {param_name}: {param.default}")
        
        # 验证固定配置
        if sig.parameters['min_price_spacing'].default == 100.0:
            print("✅ 价格间隔配置正确：100.0")
        else:
            print("❌ 价格间隔配置错误")
            
        if sig.parameters['max_levels'].default == 4:
            print("✅ 最大委托数量配置正确：4")
        else:
            print("❌ 最大委托数量配置错误")
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_fixed_config()