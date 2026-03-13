"""
彻底修复 check_duplicate_orders 函数
"""

# 读取文件
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到函数定义行并修改
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # 查找函数定义
    if 'def check_duplicate_orders(self, symbol: str, side: str, price: float,' in line:
        # 替换函数签名（多行）
        new_lines.append('    def check_duplicate_orders(self, symbol: str, side: str, price: float, \n')
        new_lines.append('                             size: float, price_tolerance: float = 5.0,\n')
        new_lines.append('                             check_price_only: bool = False) -> bool:\n')
        
        # 跳过原来的签名行
        i += 1
        while i < len(lines) and '-> bool:' not in lines[i]:
            i += 1
        i += 1  # 跳过 '-> bool:' 行
        
        # 添加 docstring
        new_lines.append('        """\n')
        new_lines.append('        检查是否存在重复委托\n')
        new_lines.append('        \n')
        new_lines.append('        Args:\n')
        new_lines.append('            check_price_only: 如果为 True，只检查价格是否相同（不管数量）\n')
        new_lines.append('                             如果为 False，检查价格和数量都相似\n')
        new_lines.append('        """\n')
        continue
    
    # 查找函数体内的逻辑
    elif '检查价格是否接近（价格容差范围内）' in line:
        # 替换为新的逻辑
        new_lines.append('                if check_price_only:\n')
        new_lines.append('                    # 只检查价格是否相同（更严格的重复检查）\n')
        new_lines.append('                    if abs(float(order_price) - float(price)) < 0.5:  # 价格差异 < 0.5 USDT\n')
        new_lines.append('                        return True\n')
        new_lines.append('                else:\n')
        new_lines.append('                    # 检查价格是否接近（价格容差范围内）\n')
        # 跳过原来的注释行
        i += 1
        while i < len(lines) and '检查数量和价格是否相似' not in lines[i]:
            i += 1
        # 添加 else 分支的注释
        new_lines.append('                    # 检查数量和价格是否相似\n')
        continue
    
    else:
        new_lines.append(line)
    
    i += 1

# 写入文件
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Successfully fixed check_duplicate_orders function")

# 验证修改
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'check_price_only: bool = False' in content:
        print("✅ check_price_only parameter added")
    else:
        print("❌ check_price_only parameter NOT found")
    
    if 'if check_price_only:' in content:
        print("✅ check_price_only logic added")
    else:
        print("❌ check_price_only logic NOT found")
