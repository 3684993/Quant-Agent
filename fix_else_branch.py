"""
修复 check_duplicate_orders 函数的 else 逻辑
"""

# 读取文件
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 else 分支
old_else = '''                if check_price_only:
                    # 只检查价格是否相同（更严格的重复检查）
                    if abs(float(order_price) - float(price)) < 0.5:  # 价格差异 < 0.5 USDT
                        return True
                else:
                    # 检查价格是否接近（价格容差范围内）
                    # 检查数量和价格是否相似
                # 检查数量和价格是否相似
                if (price_diff_pct <= price_tolerance and 
                    abs(order_size - size) / max(order_size, size) <= 0.1):'''

new_else = '''                if check_price_only:
                    # 只检查价格是否相同（更严格的重复检查）
                    if abs(float(order_price) - float(price)) < 0.5:  # 价格差异 < 0.5 USDT
                        return True
                else:
                    # 检查价格是否接近（价格容差范围内）
                    price_diff_pct = abs(float(order_price) - float(price))
                    
                    # 检查数量和价格是否相似
                    if (price_diff_pct <= price_tolerance and 
                        abs(order_size - size) / max(order_size, size) <= 0.1):'''

content = content.replace(old_else, new_else)

# 写入文件
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed else branch in check_duplicate_orders")
