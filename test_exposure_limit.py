"""测试暴露量限制逻辑"""

print("=== 暴露量限制逻辑测试 ===\n")

# 模拟场景
max_position_size = 0.02  # 最大持仓 0.02 BTC

print(f"配置：最大持仓限制 = {max_position_size} BTC\n")

# 场景 1: 没有持仓，没有委托
print("场景 1: 没有持仓，没有委托")
current_position = 0
existing_orders_size = 0
new_size = 0.02
total_exposure = current_position + existing_orders_size + new_size
available = max_position_size - current_position - existing_orders_size
print(f"  当前持仓：{current_position:.4f}")
print(f"  现有委托：{existing_orders_size:.4f}")
print(f"  新委托：{new_size:.4f}")
print(f"  总暴露量：{total_exposure:.4f}")
print(f"  可用额度：{available:.4f}")
print(f"  结果：{'✅ 允许委托' if total_exposure <= max_position_size else '❌ 拒绝委托'}\n")

# 场景 2: 持仓 0.01，没有委托
print("场景 2: 持仓 0.01，没有委托")
current_position = 0.01
existing_orders_size = 0
new_size = 0.01
total_exposure = current_position + existing_orders_size + new_size
available = max_position_size - current_position - existing_orders_size
print(f"  当前持仓：{current_position:.4f}")
print(f"  现有委托：{existing_orders_size:.4f}")
print(f"  新委托：{new_size:.4f}")
print(f"  总暴露量：{total_exposure:.4f}")
print(f"  可用额度：{available:.4f}")
print(f"  结果：{'✅ 允许委托' if total_exposure <= max_position_size else '❌ 拒绝委托'}\n")

# 场景 3: 持仓 0.01，委托 0.005，再委托 0.01
print("场景 3: 持仓 0.01，委托 0.005，尝试再委托 0.01")
current_position = 0.01
existing_orders_size = 0.005
new_size = 0.01
total_exposure = current_position + existing_orders_size + new_size
available = max_position_size - current_position - existing_orders_size
print(f"  当前持仓：{current_position:.4f}")
print(f"  现有委托：{existing_orders_size:.4f}")
print(f"  新委托：{new_size:.4f}")
print(f"  总暴露量：{total_exposure:.4f}")
print(f"  可用额度：{available:.4f}")
print(f"  结果：{'✅ 允许委托' if total_exposure <= max_position_size else '❌ 拒绝委托'}\n")

# 场景 4: 持仓 0.015，委托 0.005，再委托 0.005
print("场景 4: 持仓 0.015，委托 0.005，尝试再委托 0.005")
current_position = 0.015
existing_orders_size = 0.005
new_size = 0.005
total_exposure = current_position + existing_orders_size + new_size
available = max_position_size - current_position - existing_orders_size
print(f"  当前持仓：{current_position:.4f}")
print(f"  现有委托：{existing_orders_size:.4f}")
print(f"  新委托：{new_size:.4f}")
print(f"  总暴露量：{total_exposure:.4f}")
print(f"  可用额度：{available:.4f}")
print(f"  结果：{'✅ 允许委托' if total_exposure <= max_position_size else '❌ 拒绝委托'}\n")

# 场景 5: 持仓 0.02，尝试委托
print("场景 5: 持仓 0.02，尝试委托 0.001")
current_position = 0.02
existing_orders_size = 0
new_size = 0.001
total_exposure = current_position + existing_orders_size + new_size
available = max_position_size - current_position - existing_orders_size
print(f"  当前持仓：{current_position:.4f}")
print(f"  现有委托：{existing_orders_size:.4f}")
print(f"  新委托：{new_size:.4f}")
print(f"  总暴露量：{total_exposure:.4f}")
print(f"  可用额度：{available:.4f}")
print(f"  结果：{'✅ 允许委托' if total_exposure <= max_position_size else '❌ 拒绝委托'}\n")

print("=== 测试完成 ===")
print("\n核心逻辑:")
print("1. 总暴露量 = 当前持仓 + 现有未成交委托 + 新委托")
print("2. 可用额度 = 最大持仓限制 - 当前持仓 - 现有未成交委托")
print("3. 只有当 总暴露量 <= 最大持仓限制 时，才允许委托")
