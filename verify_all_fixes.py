"""
验证所有修复是否成功应用
"""
import ast
import sys

file_path = r'f:\Quant-Agent\ai_quant_trader\execution\order_executor.py'

print("=" * 60)
print("VERIFICATION REPORT - All Fixes")
print("=" * 60)

# 读取文件
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# 检查 1: 函数签名是否包含 check_price_only 参数
print("\n✓ 检查 1: 函数签名")
if 'def check_duplicate_orders(self, symbol: str, side: str, price: float,' in content:
    if 'check_price_only: bool = False' in content:
        print("  ✅ 函数签名正确，包含 check_price_only 参数")
    else:
        print("  ❌ 函数签名缺少 check_price_only 参数")
else:
    print("  ❌ 未找到 check_duplicate_orders 函数")

# 检查 2: check_price_only 分支逻辑
print("\n✓ 检查 2: check_price_only 分支逻辑")
if 'if check_price_only:' in content:
    print("  ✅ 找到 if check_price_only 分支")
    if 'abs(float(order_price) - float(price)) < 0.5' in content:
        print("  ✅ 价格检查逻辑正确 (< 0.5 USDT)")
    else:
        print("  ❌ 价格检查逻辑不正确")
else:
    print("  ❌ 未找到 check_price_only 分支")

# 检查 3: else 分支逻辑
print("\n✓ 检查 3: else 分支逻辑（价格 + 数量检查）")
if 'else:' in content and 'price_diff_pct <= price_tolerance' in content:
    print("  ✅ else 分支存在且包含价格容差检查")
    if 'abs(order_size - size) / max(order_size, size) <= 0.1' in content:
        print("  ✅ 包含数量相似度检查")
    else:
        print("  ❌ 缺少数量相似度检查")
else:
    print("  ❌ else 分支逻辑不完整")

# 检查 4: 调用处是否使用 check_price_only=True
print("\n✓ 检查 4: 调用处检查")
call_found = False
for i, line in enumerate(lines, 1):
    if 'check_duplicate_orders' in line and 'check_price_only=True' in line:
        print(f"  ✅ 第 {i} 行：调用时使用了 check_price_only=True")
        call_found = True
        break
if not call_found:
    print("  ❌ 未找到使用 check_price_only=True 的调用")

# 检查 5: 语法验证（尝试解析 Python 代码）
print("\n✓ 检查 5: Python 语法验证")
try:
    ast.parse(content)
    print("  ✅ Python 语法正确，无缩进错误")
except SyntaxError as e:
    print(f"  ❌ 语法错误：{e}")
    print(f"     位置：第 {e.lineno} 行")

# 检查 6: 关键代码段验证
print("\n✓ 检查 6: 关键代码段验证")
checks = [
    ("函数定义", "def check_duplicate_orders", False),
    ("参数 check_price_only", "check_price_only: bool = False", False),
    ("if check_price_only 分支", "if check_price_only:", False),
    ("价格检查 < 0.5", "abs(float(order_price) - float(price)) < 0.5", False),
    ("else 分支", "else:", False),
    ("价格容差检查", "price_diff_pct <= price_tolerance", False),
    ("数量相似度检查", "abs(order_size - size) / max(order_size, size) <= 0.1", False),
    ("调用 check_price_only=True", "check_price_only=True", False),
]

for check_name, pattern, found in checks:
    if pattern in content:
        print(f"  ✅ {check_name}: 已找到")
    else:
        print(f"  ❌ {check_name}: 未找到")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
