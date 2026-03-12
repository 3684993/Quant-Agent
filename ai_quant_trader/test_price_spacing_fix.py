"""
测试价格间隔严格固定为100点
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from execution.order_executor import OrderExecutor


def test_price_spacing_fix():
    """测试价格间隔严格固定为100点"""
    print("=== 测试价格间隔严格固定为100点 ===")
    
    try:
        # 创建模拟的binance客户端
        class MockBinanceClient:
            def __init__(self):
                self.mock_orders = []
                
            def get_open_orders(self, symbol=None):
                """模拟查询活跃订单"""
                return self.mock_orders
        
        # 创建模拟客户端
        mock_client = MockBinanceClient()
        
        # 创建委托执行器
        order_executor = OrderExecutor(mock_client, testnet=True)
        
        # 测试1: 价格范围过小的情况
        print("\n=== 测试1: 价格范围过小（<100点） ===")
        
        test_prices_1 = [70000, 70050, 70100]  # 价格范围100点，但间距50点
        test_sizes_1 = [0.005, 0.005, 0.005]
        
        optimized_prices_1, optimized_sizes_1 = order_executor._optimize_entry_levels(
            test_prices_1, test_sizes_1
        )
        
        print(f"✅ 价格范围过小测试:")
        print(f"   原始价格: {test_prices_1} (范围: {max(test_prices_1)-min(test_prices_1):.2f}点)")
        print(f"   优化后价格: {optimized_prices_1}")
        
        if len(optimized_prices_1) == 1:
            print("✅ 正确：价格范围过小，使用单一价格")
        else:
            print("❌ 错误：应该使用单一价格")
        
        # 测试2: 价格范围适中，但间距过小
        print("\n=== 测试2: 价格范围适中但间距过小 ===")
        
        test_prices_2 = [70000, 70030, 70060, 70090, 70120]  # 间距30点
        test_sizes_2 = [0.005, 0.005, 0.005, 0.005, 0.005]
        
        optimized_prices_2, optimized_sizes_2 = order_executor._optimize_entry_levels(
            test_prices_2, test_sizes_2
        )
        
        print(f"✅ 间距过小测试:")
        print(f"   原始价格: {test_prices_2}")
        print(f"   优化后价格: {optimized_prices_2}")
        
        # 检查价格间距
        if len(optimized_prices_2) > 1:
            min_spacing = min([abs(optimized_prices_2[i+1] - optimized_prices_2[i]) for i in range(len(optimized_prices_2)-1)])
            print(f"   最小价格间距: {min_spacing:.2f}点")
            
            if min_spacing >= 100.0:
                print("✅ 正确：价格间距≥100点")
            else:
                print("❌ 错误：价格间距仍然<100点")
        
        # 测试3: 您发现的问题价格
        print("\n=== 测试3: 您发现的问题价格 ===")
        
        # 您发现的4个价格：70,128.10、70,163.20、70,216.30、70,251.40
        problem_prices = [70128.10, 70163.20, 70216.30, 70251.40]
        problem_sizes = [0.005, 0.005, 0.005, 0.005]
        
        optimized_prices_3, optimized_sizes_3 = order_executor._optimize_entry_levels(
            problem_prices, problem_sizes
        )
        
        print(f"✅ 问题价格测试:")
        print(f"   原始问题价格: {problem_prices}")
        print(f"   价格间距: 35.1点, 53.1点, 35.1点")
        print(f"   优化后价格: {optimized_prices_3}")
        
        # 检查价格间距
        if len(optimized_prices_3) > 1:
            min_spacing = min([abs(optimized_prices_3[i+1] - optimized_prices_3[i]) for i in range(len(optimized_prices_3)-1)])
            print(f"   最小价格间距: {min_spacing:.2f}点")
            
            if min_spacing >= 100.0:
                print("✅ 正确：问题价格已修复，间距≥100点")
            else:
                print("❌ 错误：问题价格仍然存在")
        else:
            print("✅ 正确：价格范围过小，使用单一价格")
        
        # 测试4: 正常价格范围
        print("\n=== 测试4: 正常价格范围 ===")
        
        normal_prices = [70000, 70100, 70200, 70300, 70400]  # 间距100点
        normal_sizes = [0.005, 0.005, 0.005, 0.005, 0.005]
        
        optimized_prices_4, optimized_sizes_4 = order_executor._optimize_entry_levels(
            normal_prices, normal_sizes
        )
        
        print(f"✅ 正常价格测试:")
        print(f"   原始价格: {normal_prices}")
        print(f"   优化后价格: {optimized_prices_4}")
        
        # 检查价格间距
        if len(optimized_prices_4) > 1:
            min_spacing = min([abs(optimized_prices_4[i+1] - optimized_prices_4[i]) for i in range(len(optimized_prices_4)-1)])
            print(f"   最小价格间距: {min_spacing:.2f}点")
            
            if min_spacing >= 100.0:
                print("✅ 正确：正常价格间距≥100点")
            else:
                print("❌ 错误：正常价格间距有问题")
        
        # 测试5: 严格的最小间距验证
        print("\n=== 测试5: 严格的最小间距验证 ===")
        
        strict_prices = [70000, 70099, 70198, 70297]  # 间距99点（应该被优化）
        strict_sizes = [0.005, 0.005, 0.005, 0.005]
        
        optimized_prices_5, optimized_sizes_5 = order_executor._optimize_entry_levels(
            strict_prices, strict_sizes
        )
        
        print(f"✅ 严格间距验证:")
        print(f"   原始价格: {strict_prices} (间距99点)")
        print(f"   优化后价格: {optimized_prices_5}")
        
        # 检查价格间距
        if len(optimized_prices_5) > 1:
            min_spacing = min([abs(optimized_prices_5[i+1] - optimized_prices_5[i]) for i in range(len(optimized_prices_5)-1)])
            print(f"   最小价格间距: {min_spacing:.2f}点")
            
            if min_spacing >= 100.0:
                print("✅ 正确：严格间距验证通过，间距≥100点")
            else:
                print("❌ 错误：严格间距验证失败")
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_price_spacing_fix()