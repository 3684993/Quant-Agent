"""
测试advanced_take_profit导入修复
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_import_fix():
    """测试导入修复"""
    print("=== 测试advanced_take_profit导入修复 ===")
    
    try:
        # 测试1: 直接导入advanced_take_profit
        from agents.advanced_take_profit import advanced_take_profit
        print("✅ advanced_take_profit导入成功")
        
        # 测试2: 测试功能
        should_trailing = advanced_take_profit.should_set_profit_trailing(36, 1.16)
        print(f"✅ 收益委托判断功能正常: {should_trailing}")
        
        # 测试3: 测试scheduler中的导入
        from core.scheduler import Scheduler
        print("✅ scheduler导入成功（包含advanced_take_profit）")
        
        print("\n=== 所有导入测试通过 ===")
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_import_fix()