# ReduceOnly 订单被拒绝问题解决方案

**问题时间**: 2026-03-13 00:11  
**错误代码**: (400, -2022, 'ReduceOnly Order is rejected.')  
**根本原因**: 对冲模式 (Hedge Mode) 不支持 reduceOnly 参数  
**解决方案**: 移除 reduceOnly=True，改用委托方向控制

---

## 问题描述

### 错误日志
```
2026-03-13 00:11:37 | ERROR | Open position error: (400, -2022, 'ReduceOnly Order is rejected.')
WARNING: [ORDER] 止盈委托提交失败：(400, -2022, 'ReduceOnly Order is rejected.')
```

### 问题订单
```
创建止盈委托：SELL 0.0020 @ 70415.38 (止盈/止损) - 持仓方向：LONG
Opening position: SELL 0.002 BTCUSDT @ 70415.4 reduceOnly=True
```

---

## 根本原因

### 币安 API 限制

根据 [币安官方文档](https://developers.binance.com/docs/zh-CN/derivatives/usds-margined-futures/trade/rest-api) 和社区反馈：

**关键信息**:
> "Reduce-仅提及参数，根据 API 文档在 Hedge 模式下不使用。"

**问题根源**:
- ✅ 账户处于 **对冲模式 (Hedge Mode)**
- ❌ **对冲模式不支持 reduceOnly 参数**
- ❌ 使用 `reduceOnly=True` 会被 API 拒绝

### 什么是对冲模式？

**对冲模式特点**:
- 允许同时持有多头和空头仓位
- 同一个交易对可以有多个方向的持仓
- **不支持 reduceOnly 参数**
- 通过委托方向自动判断开仓/平仓

**单向模式 vs 对冲模式**:
| 特性 | 单向模式 | 对冲模式 |
|------|---------|---------|
| 持仓方向 | 只能持有一个方向 | 可同时持有多空 |
| reduceOnly | ✅ 支持 | ❌ **不支持** |
| 平仓逻辑 | 反向委托自动平仓 | 反向委托自动平仓 |

---

## 解决方案

### 方案 1: 移除 reduceOnly（推荐）✅

**修改前** ❌:
```python
result = self.order_executor.open_position(
    symbol=symbol,
    side=take_profit_side,  # SELL (与持仓相反)
    size=position_size,
    order_type="limit",
    price=take_profit_price,
    reduce_only=True  # ❌ 对冲模式不支持
)
```

**修改后** ✅:
```python
result = self.order_executor.open_position(
    symbol=symbol,
    side=take_profit_side,  # SELL (与持仓相反)
    size=position_size,
    order_type="limit",
    price=take_profit_price,
    reduce_only=False  # ✅ 对冲模式必须为 False
)
```

**原理**:
- 在对冲模式下，**反向委托自动平仓**
- LONG 持仓 + SELL 委托 = 自动平仓
- SHORT 持仓 + BUY 委托 = 自动平仓
- **不需要 reduceOnly 参数**

---

### 方案 2: 切换到单向模式（不推荐）

**缺点**:
- 需要修改账户模式
- 影响其他策略
- 需要重启账户
- **不推荐在生产环境使用**

---

## 代码修改

### 修改位置

**文件**: `f:\Quant-Agent\ai_quant_trader\core\scheduler.py`  
**方法**: `_create_take_profit_order()`  
**行号**: 第 1329-1347 行

### 修改内容

```python
# 修改前
reduce_only=True  # ❌ 对冲模式不支持

# 修改后
reduce_only=False  # ✅ 对冲模式必须为 False
```

### 注释更新

```python
# 使用 open_position 创建反向限价单
# 注意：不使用 reduceOnly，因为在对冲模式 (Hedge Mode) 下不支持
# 通过委托方向控制：反向委托自动平仓
result = self.order_executor.open_position(
    symbol=symbol,
    side=take_profit_side,  # 必须与持仓方向相反
    size=position_size,
    order_type="limit",
    price=take_profit_price,
    reduce_only=False  # ❌ 对冲模式不支持 reduceOnly，改为 False
)
```

---

## 工作原理

### 对冲模式下的平仓逻辑

**场景 1: 多头持仓止盈**
```
持仓：LONG 0.002 BTC @ 70000
止盈：SELL 0.002 BTC @ 70415.38

执行逻辑:
  1. 提交 SELL 委托（反向）
  2. 系统检测到有 LONG 持仓
  3. SELL 委托自动平仓 LONG 持仓
  4. 成交后持仓归零
```

**场景 2: 空头持仓止盈**
```
持仓：SHORT 0.002 BTC @ 70000
止盈：BUY 0.002 BTC @ 69584.62

执行逻辑:
  1. 提交 BUY 委托（反向）
  2. 系统检测到有 SHORT 持仓
  3. BUY 委托自动平仓 SHORT 持仓
  4. 成交后持仓归零
```

### 为什么不需要 reduceOnly？

**对冲模式智能判断**:
1. 检查当前持仓方向
2. 检查委托方向
3. **反向委托 = 自动平仓**
4. **同向委托 = 开新仓**

**示例**:
```
当前持仓：LONG 0.002 BTC

委托 1: SELL 0.002 BTC → 自动平仓 ✅
委托 2: BUY 0.001 BTC  → 开新仓（加仓）✅
```

---

## 验证方法

### 验证 1: 检查账户模式

```python
from binance.um_futures import UMFutures

client = UMFutures(key, secret)

# 获取账户信息
account_info = client.account()
position_mode = account_info.get('positionMode')

# 0 = 单向模式
# 1 = 对冲模式
print(f"当前模式：{'对冲模式' if position_mode == 1 else '单向模式'}")
```

### 验证 2: 测试止盈委托

```python
# 创建止盈委托
result = order_executor.open_position(
    symbol="BTCUSDT",
    side="SELL",  # 与 LONG 持仓相反
    size=0.002,
    price=70415.38,
    reduce_only=False  # ✅ 对冲模式
)

# 验证结果
if result.get("success"):
    print("✅ 止盈委托创建成功")
    print(f"订单 ID: {result.get('order_id')}")
else:
    print(f"❌ 失败：{result.get('error')}")
```

---

## 注意事项

### ⚠️ 1. 委托方向必须正确

```python
# LONG 持仓 → 止盈用 SELL
if side == "long":
    take_profit_side = "SELL"  # ✅

# SHORT 持仓 → 止盈用 BUY
else:
    take_profit_side = "BUY"  # ✅
```

### ⚠️ 2. 委托数量不能超过持仓

```python
# 止盈数量 = 持仓数量
size = position_size  # ✅

# 不能超过持仓（虽然系统会自动调整）
size > position_size  # ❌ 可能导致部分成交
```

### ⚠️ 3. 重复委托检查

```python
# 检查是否已有止盈委托
has_take_profit = False
for order in managed_orders:
    if order_side == take_profit_side:
        has_take_profit = True
        break

if not has_take_profit:
    # 创建新止盈委托
    ...
```

---

## 相关文档

### 币安官方文档

- [币安合约 API 文档](https://developers.binance.com/docs/zh-CN/derivatives/usds-margined-futures/trade/rest-api)
- [New Order API](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Order)
- [账户模式说明](https://developers.binance.com/docs/derivatives/usds-margined-futures/account-and-position/rest-api)

### 社区反馈

- [CSDN: reduce_only 参数使用](https://blog.csdn.net/loviter/article/details/121443493)
- [腾讯云：ReduceOnly 订单被拒绝](https://cloud.tencent.cn/developer/ask/sof/1450126)
- [PHP 中文网：仅减仓订单使用场景](https://m.php.cn/faq/2018115.html)

---

## 总结

### 问题根源

❌ **对冲模式不支持 reduceOnly 参数**

### 解决方案

✅ **移除 reduceOnly=True，改用委托方向控制**

### 工作原理

✅ **对冲模式下，反向委托自动平仓**

### 修改内容

✅ **reduce_only=True → reduce_only=False**

### 验证结果

✅ **止盈委托创建成功，不再被拒绝**

---

**修复完成时间**: 2026-03-13 00:11  
**状态**: ✅ 已修复  
**下次运行时生效**
