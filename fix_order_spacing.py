"""
委托价格调整工具
用于调整过于接近的委托价格，确保间距 >= 10 USDT
"""

print("=" * 80)
print("委托价格间距分析与调整建议")
print("=" * 80)
print()

# 当前两个委托
order1_price = 70272.70
order2_price = 70271.10
order1_id = "委托 1"
order2_id = "委托 2"

# 计算当前间距
current_spacing = abs(order1_price - order2_price)
min_required = 10.0  # 最小间距要求

print(f"当前委托:")
print(f"  {order1_id}: {order1_price:.2f} USDT")
print(f"  {order2_id}: {order2_price:.2f} USDT")
print()
print(f"当前间距：{current_spacing:.2f} USDT")
print(f"要求最小间距：{min_required:.2f} USDT")
print(f"间距不足：{min_required - current_spacing:.2f} USDT")
print()

# 检查是否违规
if current_spacing < min_required:
    print(f"❌ 违规：两委托价格太近 ({current_spacing:.2f} < {min_required:.2f})")
    print()
    
    # 方案 1: 调整较低的委托（向下移动）
    new_price_1 = order2_price - min_required
    print(f"✅ 调整方案 1: 向下移动较低价格的委托")
    print(f"   原价格：{order2_price:.2f} USDT")
    print(f"   新价格：{new_price_1:.2f} USDT")
    print(f"   调整后间距：{min_required:.2f} USDT")
    print(f"   操作：取消 {order2_id} @ {order2_price:.2f}, 重新委托 @ {new_price_1:.2f}")
    print()
    
    # 方案 2: 调整较高的委托（向上移动）
    new_price_2 = order1_price + min_required
    print(f"✅ 调整方案 2: 向上移动较高价格的委托")
    print(f"   原价格：{order1_price:.2f} USDT")
    print(f"   新价格：{new_price_2:.2f} USDT")
    print(f"   调整后间距：{min_required:.2f} USDT")
    print(f"   操作：取消 {order1_id} @ {order1_price:.2f}, 重新委托 @ {new_price_2:.2f}")
    print()
    
    # 方案 3: 平均分布（两个都调整）
    mid_price = (order1_price + order2_price) / 2
    new_price_3a = mid_price - min_required / 2
    new_price_3b = mid_price + min_required / 2
    print(f"✅ 调整方案 3: 平均分布（两个委托都调整）")
    print(f"   {order2_id} 新价格：{new_price_3a:.2f} USDT")
    print(f"   {order1_id} 新价格：{new_price_3b:.2f} USDT")
    print(f"   调整后间距：{min_required:.2f} USDT")
    print(f"   操作：取消两个委托，重新在 {new_price_3a:.2f} 和 {new_price_3b:.2f} 挂单")
    print()
    
    # 推荐方案
    print("=" * 80)
    print("推荐方案:")
    print("=" * 80)
    print(f"💡 建议使用方案 1（向下移动较低价格委托）")
    print()
    print(f"理由:")
    print(f"  1. 只调整一个委托，减少操作次数")
    print(f"  2. 保持较高价格委托更接近成交价")
    print(f"  3. 符合分批建仓的价格递减策略")
    print()
    print(f"具体操作:")
    print(f"  1. 取消 {order2_id} @ {order2_price:.2f} USDT")
    print(f"  2. 立即重新委托 {order2_id} @ {new_price_1:.2f} USDT")
    print(f"  3. 保留 {order1_id} @ {order1_price:.2f} USDT 不变")
    print()
    print(f"调整后的委托:")
    print(f"  {order1_id}: {order1_price:.2f} USDT (不变)")
    print(f"  {order2_id}: {new_price_1:.2f} USDT (新)")
    print(f"  间距：{min_required:.2f} USDT ✅")
    print()
    
else:
    print(f"✅ 合规：两委托价格间距符合要求 ({current_spacing:.2f} >= {min_required:.2f})")
    print()

# 检查最大间距
max_allowed = 100.0
if current_spacing > max_allowed:
    print(f"❌ 违规：两委托价格太远 ({current_spacing:.2f} > {max_allowed:.2f})")
    print(f"建议：缩小间距到 {max_allowed:.2f} USDT 以内")
    print()
else:
    print(f"✅ 最大间距检查通过 ({current_spacing:.2f} <= {max_allowed:.2f})")
    print()

# 总结
print("=" * 80)
print("总结")
print("=" * 80)
print(f"当前状态：{'❌ 需要调整' if current_spacing < min_required else '✅ 符合要求'}")
print(f"当前间距：{current_spacing:.2f} USDT")
print(f"合规范围：[{min_required:.2f}, {max_allowed:.2f}] USDT")
print()

# 自动化建议
if current_spacing < min_required:
    print("自动化处理建议:")
    print("  1. 调用 order_manager.inspect_all_orders() 检查所有委托")
    print("  2. 检查 spacing_check 是否返回 'too_close': True")
    print("  3. 根据 recommendations 建议调整价格")
    print("  4. 调用 order_executor.cancel_orders() 取消需要调整的委托")
    print("  5. 重新委托，确保间距 >= 10 USDT")
    print()

print("=" * 80)
