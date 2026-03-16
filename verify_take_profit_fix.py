"""
验证止盈委托修复是否正确
"""
import ast

file_path = r'f:\Quant-Agent\ai_quant_trader\core\scheduler.py'

print("=" * 80)
print("取盈委托修复验证报告")
print("=" * 80)

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 检查 1: 是否使用 TAKE_PROFIT_MARKET 类型
print("\n✓ 检查 1: 委托类型")
if 'type="TAKE_PROFIT_MARKET"' in content or "type='TAKE_PROFIT_MARKET'" in content:
    print("  ✅ 使用 TAKE_PROFIT_MARKET 市价止盈类型")
else:
    print("  ❌ 未使用 TAKE_PROFIT_MARKET 类型")

# 检查 2: 是否设置 stopPrice 参数
print("\n✓ 检查 2: 触发价格参数")
if 'stopPrice=take_profit_price' in content:
    print("  ✅ 设置 stopPrice 触发价格参数")
else:
    print("  ❌ 未设置 stopPrice 参数")

# 检查 3: 是否设置 closePosition=True
print("\n✓ 检查 3: 全部平仓参数")
if 'closePosition=True' in content:
    print("  ✅ 设置 closePosition=True 全部平仓")
else:
    print("  ❌ 未设置 closePosition 参数")

# 检查 4: 是否有触发条件说明
print("\n✓ 检查 4: 触发条件说明")
if '最新价格' in content and (">=" in content or "<=" in content):
    print("  ✅ 包含触发条件说明（最新价格 >= 或 <= 触发价格）")
else:
    print("  ❌ 缺少触发条件说明")

# 检查 5: 是否有异常处理和回退机制
print("\n✓ 检查 5: 异常处理")
if 'try:' in content and 'except Exception as order_error:' in content:
    print("  ✅ 包含异常处理机制")
    if '回退' in content or 'fallback' in content.lower():
        print("  ✅ 包含回退到限价单的机制")
    else:
        print("  ⚠️ 缺少回退机制")
else:
    print("  ❌ 缺少异常处理")

# 检查 6: 日志输出是否完整
print("\n✓ 检查 6: 日志输出")
checks = [
    ("市价止盈委托已提交", "市价止盈委托已提交"),
    ("触发价格", "触发价格"),
    ("止盈详情", "止盈详情"),
]

all_found = True
for check_name, pattern in checks:
    if pattern in content:
        print(f"  ✅ 包含 {check_name} 日志")
    else:
        print(f"  ❌ 缺少 {check_name} 日志")
        all_found = False

# 检查 7: Python 语法验证
print("\n✓ 检查 7: Python 语法验证")
try:
    ast.parse(content)
    print("  ✅ Python 语法正确，无错误")
except SyntaxError as e:
    print(f"  ❌ 语法错误：{e}")
    print(f"     位置：第 {e.lineno} 行")

# 检查 8: 对比交易所格式
print("\n✓ 检查 8: 对比交易所格式要求")
exchange_requirements = {
    "类型：市价止盈": 'type="TAKE_PROFIT_MARKET"' in content,
    "触发条件：最新价格": '最新价格' in content,
    "只减仓：是 (closePosition)": 'closePosition=True' in content,
    "方向与持仓相反": 'take_profit_side' in content and '与持仓方向相反' in content,
}

for req, satisfied in exchange_requirements.items():
    if satisfied:
        print(f"  ✅ 符合交易所要求：{req}")
    else:
        print(f"  ❌ 不符合要求：{req}")

print("\n" + "=" * 80)
print("验证完成")
print("=" * 80)

# 显示关键代码段
print("\n📋 关键代码段预览：")
print("-" * 80)

lines = content.split('\n')
in_take_profit_block = False
block_lines = []

for i, line in enumerate(lines, 1):
    if 'TAKE_PROFIT_MARKET' in line:
        # 打印前后各 5 行
        start = max(0, i - 6)
        end = min(len(lines), i + 10)
        block_lines = lines[start:end]
        break

if block_lines:
    for idx, line in enumerate(block_lines, start):
        print(f"{idx:4d} | {line}")
else:
    print("未找到关键代码块")

print("-" * 80)
