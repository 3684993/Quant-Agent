import re

file_path = r'f:\Quant-Agent\ai_quant_trader\execution\order_executor.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 查找并修复缩进问题
# 问题：第 1129-1133 行的 if 语句后没有正确缩进
old_pattern = r'''                else:
                    # 检查价格是否接近（价格容差范围内）
                    price_diff_pct = abs\(float\(order_price\) - float\(price\)\)
                    
                    # 检查数量和价格是否相似
                    if \(price_diff_pct <= price_tolerance and 
                        abs\(order_size - size\) / max\(order_size, size\) <= 0\.1\):
                    logger\.warning\(f"发现重复委托：价格=\{order_price:.2f\} vs \{price:.2f\}, "
                                 f"数量=\{order_size:.4f\} vs \{size:.4f\}"\)
                    return True'''

new_pattern = '''                else:
                    # 检查价格是否接近（价格容差范围内）
                    price_diff_pct = abs(float(order_price) - float(price))
                    
                    # 检查数量和价格是否相似
                    if (price_diff_pct <= price_tolerance and 
                        abs(order_size - size) / max(order_size, size) <= 0.1):
                        logger.warning(f"发现重复委托：价格={order_price:.2f} vs {price:.2f}, "
                                     f"数量={order_size:.4f} vs {size:.4f}")
                        return True'''

# 使用更简单的方法：直接按行处理
lines = content.split('\n')
fixed = False

for i in range(len(lines)):
    # 查找问题行
    if 'abs(order_size - size) / max(order_size, size) <= 0.1):' in lines[i]:
        # 检查下一行是否缩进错误
        if i + 1 < len(lines) and lines[i + 1].strip().startswith('logger.warning'):
            # 修复缩进
            lines[i + 1] = '                        ' + lines[i + 1].lstrip()
            fixed = True
            print(f"Fixed line {i + 2}: {lines[i + 1][:50]}...")
        
        if i + 2 < len(lines) and lines[i + 2].strip().startswith('return True'):
            # 修复缩进
            lines[i + 2] = '                        ' + lines[i + 2].lstrip()
            fixed = True
            print(f"Fixed line {i + 3}: {lines[i + 2][:50]}...")

if fixed:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print("\nIndentation fixed successfully!")
else:
    print("Pattern not found, no changes made.")

# 验证修复
print("\n=== Verification ===")
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[1128:1135], start=1129):
        print(f"{i}: {line.rstrip()}")
