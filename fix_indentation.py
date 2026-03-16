"""
修复缩进问题
"""

# 读取文件
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复缩进
old_indent = '''                    if (price_diff_pct <= price_tolerance and 
                        abs(order_size - size) / max(order_size, size) <= 0.1):
                    logger.warning(f"发现重复委托：价格={order_price:.2f} vs {price:.2f}, "
                                 f"数量={order_size:.4f} vs {size:.4f}")
                    return True'''

new_indent = '''                    if (price_diff_pct <= price_tolerance and 
                        abs(order_size - size) / max(order_size, size) <= 0.1):
                        logger.warning(f"发现重复委托：价格={order_price:.2f} vs {price:.2f}, "
                                     f"数量={order_size:.4f} vs {size:.4f}")
                        return True'''

content = content.replace(old_indent, new_indent)

# 写入文件
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed indentation issue")
