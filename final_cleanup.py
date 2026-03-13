"""
最终清理和验证
"""

# 读取文件
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 清理重复的 docstring
content = content.replace('        """\n        """检查是否存在重复委托"""', '        """')

# 写入文件
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Final cleanup complete")

# 验证
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
checks = [
    ('check_price_only: bool = False', 'Function signature'),
    ('if check_price_only:', 'Check logic'),
    ('abs(float(order_price) - float(price)) < 0.5', 'Price check'),
    ('price_diff_pct = abs(float(order_price) - float(price))', 'Price diff calculation'),
]

print("\nVerification:")
for check_str, description in checks:
    if check_str in content:
        print(f"  ✅ {description}: Found")
    else:
        print(f"  ❌ {description}: NOT found")
