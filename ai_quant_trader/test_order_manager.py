"""
测试独立的委托订单管理模块
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from execution.order_manager import OrderManager


def test_order_manager():
    """测试委托管理模块"""
    print("=== 测试独立的委托订单管理模块 ===")
    
    try:
        # 创建模拟的委托执行器
        class MockOrderExecutor:
            def __init__(self):
                self.mock_orders = []
                self.current_price = 70100.0
            
            def get_existing_orders(self, symbol=None):
                return self.mock_orders
            
            def get_current_price(self, symbol):
                return self.current_price
            
            def cancel_orders(self, symbol, order_ids):
                # 模拟取消委托
                cancelled = []
                for order_id in order_ids:
                    self.mock_orders = [order for order in self.mock_orders if order.get("order_id") != order_id]
                    cancelled.append(order_id)
                return {"success": True, "cancelled": cancelled}
            
            def add_mock_order(self, symbol, side, price, quantity, order_id=None):
                order = {
                    "order_id": order_id or f"mock_{len(self.mock_orders)}",
                    "symbol": symbol,
                    "side": side,
                    "price": price,
                    "quantity": quantity,
                    "time": "2026-03-11T22:00:00"
                }
                self.mock_orders.append(order)
        
        # 创建模拟的市场分析器
        class MockMarketAnalyzer:
            def get_market_summary(self, symbol):
                return {
                    "trend": "bullish",
                    "momentum": "strong",
                    "volatility": "medium"
                }
        
        # 创建模拟组件
        mock_executor = MockOrderExecutor()
        mock_analyzer = MockMarketAnalyzer()
        
        # 创建委托管理模块
        order_manager = OrderManager(mock_executor, mock_analyzer)
        
        # 测试1: 空委托巡查
        print("\n=== 测试1: 空委托巡查 ===")
        
        inspection_result_1 = order_manager.inspect_all_orders("BTCUSDT")
        
        if inspection_result_1.get("success"):
            print(f"✅ 空委托巡查成功")
            print(f"   活跃委托: {inspection_result_1.get('total_orders', 0)}个")
            print(f"   建议: {inspection_result_1.get('recommendations', [])}")
        else:
            print(f"❌ 空委托巡查失败: {inspection_result_1.get('error', '')}")
        
        # 测试2: 添加问题委托并巡查
        print("\n=== 测试2: 问题委托巡查 ===")
        
        # 添加您发现的问题委托：价格过于接近
        mock_executor.add_mock_order("BTCUSDT", "BUY", 70128.10, 0.005, "order1")
        mock_executor.add_mock_order("BTCUSDT", "BUY", 70163.20, 0.005, "order2")
        mock_executor.add_mock_order("BTCUSDT", "BUY", 70216.30, 0.005, "order3")
        mock_executor.add_mock_order("BTCUSDT", "BUY", 70251.40, 0.005, "order4")
        
        inspection_result_2 = order_manager.inspect_all_orders("BTCUSDT")
        
        if inspection_result_2.get("success"):
            print(f"✅ 问题委托巡查成功")
            print(f"   活跃委托: {inspection_result_2.get('total_orders', 0)}个")
            
            inspections = inspection_result_2.get("inspections", {})
            
            # 显示各项巡查结果
            for inspection_name, result in inspections.items():
                status = result.get("status", "未知")
                message = result.get("message", "")
                print(f"   {inspection_name}: {status} - {message}")
            
            # 显示建议
            recommendations = inspection_result_2.get("recommendations", [])
            for rec in recommendations:
                print(f"   📋 建议: {rec}")
        else:
            print(f"❌ 问题委托巡查失败: {inspection_result_2.get('error', '')}")
        
        # 测试3: 自动清理功能
        print("\n=== 测试3: 自动清理功能 ===")
        
        # 添加距离过远的委托
        mock_executor.add_mock_order("BTCUSDT", "BUY", 75000.0, 0.005, "far_order")
        
        cleanup_result = order_manager.auto_cleanup_orders("BTCUSDT")
        
        if cleanup_result.get("success"):
            print(f"✅ 自动清理成功")
            cleanup_actions = cleanup_result.get("cleanup_actions", [])
            for action in cleanup_actions:
                print(f"   🧹 清理动作: {action}")
            
            # 检查清理后的委托数量
            remaining_orders = len(mock_executor.mock_orders)
            print(f"   剩余委托: {remaining_orders}个")
        else:
            print(f"❌ 自动清理失败: {cleanup_result.get('error', '')}")
        
        # 测试4: 趋势一致性检查
        print("\n=== 测试4: 趋势一致性检查 ===")
        
        # 添加与趋势不一致的委托（牛市趋势下添加卖单）
        mock_executor.add_mock_order("BTCUSDT", "SELL", 70000.0, 0.005, "sell_order")
        
        inspection_result_3 = order_manager.inspect_all_orders("BTCUSDT")
        
        if inspection_result_3.get("success"):
            trend_check = inspection_result_3.get("inspections", {}).get("trend_check", {})
            status = trend_check.get("status", "未知")
            message = trend_check.get("message", "")
            
            print(f"✅ 趋势一致性检查: {status}")
            print(f"   详情: {message}")
            
            if status == "不一致":
                print("   ⚠️ 检测到趋势不一致的委托")
        
        # 测试5: 成交可能性分析
        print("\n=== 测试5: 成交可能性分析 ===")
        
        # 设置当前价格
        mock_executor.current_price = 70200.0
        
        inspection_result_4 = order_manager.inspect_all_orders("BTCUSDT")
        
        if inspection_result_4.get("success"):
            prob_check = inspection_result_4.get("inspections", {}).get("execution_probability", {})
            status = prob_check.get("status", "未知")
            low_prob_orders = prob_check.get("low_probability_orders", [])
            
            print(f"✅ 成交可能性分析: {status}")
            print(f"   低可能性委托: {len(low_prob_orders)}个")
            
            # 显示详细分析
            prob_analysis = prob_check.get("probability_analysis", [])
            for analysis in prob_analysis:
                order_id = analysis.get("order_id", "")
                side = analysis.get("side", "")
                order_price = analysis.get("order_price", 0)
                probability = analysis.get("probability", 0)
                
                print(f"   {order_id} | {side} @ {order_price:.2f} | 可能性: {probability:.2%}")
        
        # 测试6: 配置更新
        print("\n=== 测试6: 配置更新 ===")
        
        new_config = {
            "min_price_spacing": 150.0,  # 增加最小间距
            "max_orders_per_symbol": 3,  # 减少最大委托数量
        }
        
        order_manager.update_config(new_config)
        print("✅ 配置更新成功")
        
        # 使用新配置进行巡查
        inspection_result_5 = order_manager.inspect_all_orders("BTCUSDT")
        
        if inspection_result_5.get("success"):
            spacing_check = inspection_result_5.get("inspections", {}).get("spacing_check", {})
            required_spacing = spacing_check.get("required_spacing", 0)
            print(f"   新配置生效: 最小间距要求 = {required_spacing:.1f}点")
        
        # 测试7: 巡查历史记录
        print("\n=== 测试7: 巡查历史记录 ===")
        
        history = order_manager.get_inspection_history("BTCUSDT")
        print(f"✅ 巡查历史记录: {len(history)}条")
        
        print("\n=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_order_manager()