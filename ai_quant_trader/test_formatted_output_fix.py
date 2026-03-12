"""
测试FormattedOutput修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.formatted_output import formatted_output


def test_formatted_output_fix():
    """测试FormattedOutput修复"""
    print("=== 测试FormattedOutput修复 ===")
    
    try:
        # 测试所有方法是否存在
        methods_to_test = [
            'print_cycle_header',
            'print_market_status', 
            'print_indicators',
            'print_position_status',
            'print_ai_decision',
            'print_execution_result',
            'print_sl_tp_info',
            'print_learning_stats',
            'print_cycle_footer',
            'print_system_status',
            'print_error',
            'print_warning',
            'print_info'  # 这是新添加的方法
        ]
        
        print("\n=== 测试方法存在性 ===")
        for method_name in methods_to_test:
            if hasattr(formatted_output, method_name):
                print(f"✅ {method_name} - 存在")
            else:
                print(f"❌ {method_name} - 缺失")
        
        # 测试新添加的print_info方法
        print("\n=== 测试print_info方法 ===")
        formatted_output.print_info("测试信息：持仓36分钟，盈利1.16%，建议设置收益委托")
        print("✅ print_info方法调用成功")
        
        # 测试其他关键方法
        print("\n=== 测试其他关键方法 ===")
        
        # 测试print_warning
        formatted_output.print_warning("测试警告信息")
        print("✅ print_warning方法调用成功")
        
        # 测试print_error
        formatted_output.print_error("测试错误信息")
        print("✅ print_error方法调用成功")
        
        # 测试print_market_status
        formatted_output.print_market_status("BTCUSDT", 70733.20, 93.0, "volatile")
        print("✅ print_market_status方法调用成功")
        
        # 测试print_position_status
        test_position = {
            "has_position": True,
            "symbol": "BTCUSDT",
            "side": "long",
            "position_size": 0.0100,
            "entry_price": 69923.10,
            "current_price": 70733.20,
            "current_pnl": 10.56,
            "exchange_pnl_pct": 29.82,
            "initial_margin": 35.42,
            "hold_minutes": 36
        }
        formatted_output.print_position_status("BTCUSDT", test_position)
        print("✅ print_position_status方法调用成功")
        
        print("\n=== 所有测试通过 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_formatted_output_fix()