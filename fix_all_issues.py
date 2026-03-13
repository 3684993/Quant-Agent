import re

# 读取文件
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 问题 1: 修复 check_duplicate_orders 函数签名
old_signature = '''    def check_duplicate_orders(self, symbol: str, side: str, price: float, 
                             size: float, price_tolerance: float = 5.0) -> bool:
        """检查是否存在重复委托"""
        try:
            existing_orders = self.get_existing_orders(symbol, side)
            
            for order in existing_orders:
                order_id = str(order.get("order_id", ""))
                if order_id and order_id in self.recently_cancelled:
                    elapsed = (datetime.now() - self.recently_cancelled[order_id]).total_seconds()
                    if elapsed < 30:
                        continue
                order_price = order.get("price", 0)
                order_size = order.get("quantity", 0)
                
                # 检查价格是否接近（价格容差范围内）
                price_diff_pct = abs(float(order_price) - float(price))
                
                # 检查数量和价格是否相似
                if (price_diff_pct <= price_tolerance and 
                    abs(order_size - size) / max(order_size, size) <= 0.1):
                    logger.warning(f"发现重复委托：价格={order_price:.2f} vs {price:.2f}, "
                                 f"数量={order_size:.4f} vs {size:.4f}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查重复委托失败：{e}")
            return False'''

new_signature = '''    def check_duplicate_orders(self, symbol: str, side: str, price: float, 
                             size: float, price_tolerance: float = 5.0,
                             check_price_only: bool = False) -> bool:
        """
        检查是否存在重复委托
        
        Args:
            check_price_only: 如果为 True，只检查价格是否相同（不管数量）
                             如果为 False，检查价格和数量都相似
        """
        try:
            existing_orders = self.get_existing_orders(symbol, side)
            
            for order in existing_orders:
                order_id = str(order.get("order_id", ""))
                if order_id and order_id in self.recently_cancelled:
                    elapsed = (datetime.now() - self.recently_cancelled[order_id]).total_seconds()
                    if elapsed < 30:
                        continue
                order_price = order.get("price", 0)
                order_size = order.get("quantity", 0)
                
                if check_price_only:
                    # 只检查价格是否相同（更严格的重复检查）
                    if abs(float(order_price) - float(price)) < 0.5:  # 价格差异 < 0.5 USDT
                        return True
                else:
                    # 检查价格是否接近（价格容差范围内）
                    price_diff_pct = abs(float(order_price) - float(price))
                    
                    # 检查数量和价格是否相似
                    if (price_diff_pct <= price_tolerance and 
                        abs(order_size - size) / max(order_size, size) <= 0.1):
                        logger.warning(f"发现重复委托：价格={order_price:.2f} vs {price:.2f}, "
                                     f"数量={order_size:.4f} vs {size:.4f}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"检查重复委托失败：{e}")
            return False'''

content = content.replace(old_signature, new_signature)

# 问题 2: 移除 emoji 字符（替换为中文）
emoji_replacements = {
    '🏦': '[银行]',
    '🚀': '[启动]',
    '📅': '[日期]',
    '📝': '[记录]',
    '⚠️': '[警告]',
    '❌': '[错误]',
    '✅': '[成功]',
    '💼': '[持仓]',
    '📋': '[委托]',
    '🤖': '[AI]',
    '⚡': '[执行]',
    '🔍': '[监控]',
    '🛑': '[停止]',
    '📊': '[统计]',
    '💡': '[建议]',
    '🎉': '[完成]',
    '🎊': '[庆祝]',
}

for emoji, replacement in emoji_replacements.items():
    content = content.replace(emoji, replacement)

# 写入文件
with open('f:/Quant-Agent/ai_quant_trader/execution/order_executor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed both issues:")
print("   1. Added check_price_only parameter to check_duplicate_orders()")
print("   2. Removed all emoji characters")
