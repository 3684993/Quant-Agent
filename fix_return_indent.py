file_path = r'f:\Quant-Agent\ai_quant_trader\execution\order_executor.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 修复第 1133 行的缩进（索引 1132）
if 'return True' in lines[1132]:
    lines[1132] = '                        return True\n'
    print("Fixed line 1133")

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Indentation fixed!")

# 验证
print("\n=== Verification ===")
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[1128:1135], start=1129):
        print(f"{i}: {line.rstrip()}")
