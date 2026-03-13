"""
修复止盈委托实现，使用币安官方推荐的 TAKE_PROFIT_MARKET 类型

根据币安官方文档：
- 类型：TAKE_PROFIT_MARKET (市价止盈)
- 参数：stopPrice (触发价格)
- 参数：closePosition=True (全部平仓)
- 触发条件：当最新价格 >= stopPrice 时触发（多头止盈）
"""

import re

file_path = r'f:\Quant-Agent\ai_quant_trader\core\scheduler.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 _create_take_profit_order 方法并替换
# 旧版本：使用 limit 限价单
# 新版本：使用 TAKE_PROFIT_MARKET 市价止盈

old_method_start = '''            if not has_take_profit and self.order_executor:
                # 创建止盈委托（方向必须与持仓相反）
                logger.info("[ORDER] 创建止盈委托：%s %.4f @ %.2f (止盈/止损) - 持仓方向：%s",
                          take_profit_side, position_size, take_profit_price, side.upper())
                
                # 使用 open_position 创建反向限价单
                # 注意：不使用 reduceOnly，因为在对冲模式 (Hedge Mode) 下不支持
                # 通过委托方向控制：反向委托自动平仓
                result = self.order_executor.open_position(
                    symbol=symbol,
                    side=take_profit_side,  # 必须与持仓方向相反
                    size=position_size,  # 使用实际持仓数量
                    order_type="limit",
                    price=take_profit_price,
                    reduce_only=False  # ❌ 对冲模式不支持 reduceOnly，改为 False
                )
                
                if result.get("success"):
                    logger.info("[ORDER] 止盈委托已提交：订单 ID=%s", result.get("order_id", "UNKNOWN"))
                elif result.get("duplicate"):
                    # 重复委托，忽略
                    logger.debug("[ORDER] 止盈委托已存在，跳过")
                else:
                    logger.warning("[ORDER] 止盈委托提交失败：%s", result.get("error", "未知错误"))'''

new_method_start = '''            if not has_take_profit and self.order_executor:
                # 创建止盈委托（方向必须与持仓相反）
                logger.info("[ORDER] 创建止盈委托：%s %.4f @ %.2f (止盈/止损) - 持仓方向：%s",
                          take_profit_side, position_size, take_profit_price, side.upper())
                
                # ✅ 使用 TAKE_PROFIT_MARKET 市价止盈（币安官方推荐方式）
                # 根据币安官方文档：
                # - 类型：TAKE_PROFIT_MARKET (市价止盈)
                # - 参数：stopPrice (触发价格)
                # - 参数：closePosition=True (全部平仓)
                # - 触发条件：当最新价格 >= stopPrice 时触发（多头止盈）
                try:
                    result = self.order_executor.client.client.new_order(
                        symbol=symbol,
                        side=take_profit_side,  # 必须与持仓方向相反
                        type="TAKE_PROFIT_MARKET",  # ✅ 市价止盈
                        stopPrice=take_profit_price,  # ✅ 触发价格
                        closePosition=True  # ✅ 全部平仓
                    )
                    
                    if result.get("orderId"):
                        logger.info("[ORDER] ✅ 市价止盈委托已提交：订单 ID=%s, 触发价格=%.2f", 
                                  result.get("orderId"), take_profit_price)
                        logger.info("[ORDER] 止盈详情：方向=%s, 数量=%.4f, 触发条件：最新价格%s%.2f",
                                  take_profit_side, position_size,
                                  ">=" if side == "long" else "<=", take_profit_price)
                    else:
                        logger.warning("[ORDER] 止盈委托提交失败：返回结果异常")
                        
                except Exception as order_error:
                    logger.error(f"[ORDER] 市价止盈委托提交失败：{order_error}")
                    # 回退到限价单方式
                    logger.info("[ORDER] 回退到限价单方式")
                    result = self.order_executor.open_position(
                        symbol=symbol,
                        side=take_profit_side,
                        size=position_size,
                        order_type="limit",
                        price=take_profit_price,
                        reduce_only=False
                    )
                    
                    if result.get("success"):
                        logger.info("[ORDER] 限价止盈委托已提交：订单 ID=%s", result.get("order_id", "UNKNOWN"))
                    else:
                        logger.warning("[ORDER] 限价止盈委托提交失败：%s", result.get("error", "未知错误"))'''

if old_method_start in content:
    content = content.replace(old_method_start, new_method_start)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 止盈委托方法已更新为使用 TAKE_PROFIT_MARKET 类型")
else:
    print("❌ 未找到目标代码段，可能已经修改过")

# 验证修改
print("\n=== 验证修改 ===")
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
    if 'TAKE_PROFIT_MARKET' in content:
        print("✅ 找到 TAKE_PROFIT_MARKET 类型")
    else:
        print("❌ 未找到 TAKE_PROFIT_MARKET 类型")
    
    if 'closePosition=True' in content:
        print("✅ 找到 closePosition=True 参数")
    else:
        print("❌ 未找到 closePosition=True 参数")
    
    if 'stopPrice=take_profit_price' in content:
        print("✅ 找到 stopPrice 参数设置")
    else:
        print("❌ 未找到 stopPrice 参数设置")
