"""
委托合理性检查模块

功能：
1. 从交易所拉取现有委托
2. 检查委托合理性（数量、间距、时间）
3. 自动取消不合理委托

不合理定义：
- 数量太多：超过最大委托数量限制
- 间隔太近：价格间距 < 10 USDT
- 时间太久：超过指定时间（默认 60 分钟）
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class OrderRationalityChecker:
    """委托合理性检查器"""
    
    def __init__(self, order_executor, 
                 max_orders: int = 4,
                 min_price_spacing: float = 10.0,
                 order_timeout_minutes: int = 60):
        """
        初始化检查器
        
        Args:
            order_executor: 委托执行器
            max_orders: 最大委托数量（默认 4 个）
            min_price_spacing: 最小价格间距（默认 10 USDT）
            order_timeout_minutes: 委托超时时间（默认 60 分钟）
        """
        self.order_executor = order_executor
        self.max_orders = max_orders
        self.min_price_spacing = min_price_spacing
        self.order_timeout = timedelta(minutes=order_timeout_minutes)
        
    def check_and_cleanup(self, symbol: str, side: Optional[str] = None) -> Dict:
        """
        检查并清理不合理委托
        
        Args:
            symbol: 交易对
            side: 委托方向（可选，None 表示检查所有方向）
            
        Returns:
            清理结果字典
        """
        try:
            logger.info(f"[RATIONALITY] 开始检查 {symbol} 委托合理性...")
            
            # 1. 从交易所拉取现有委托
            orders = self._fetch_orders(symbol, side)
            
            if not orders:
                logger.info(f"[RATIONALITY] {symbol} 无未成交委托")
                return {
                    "success": True,
                    "symbol": symbol,
                    "total_orders": 0,
                    "cancelled_orders": [],
                    "reasons": []
                }
            
            logger.info(f"[RATIONALITY] {symbol} 当前有 {len(orders)} 个委托")
            
            # 2. 检查委托合理性
            unreasonable_orders = self._find_unreasonable_orders(orders)
            
            if not unreasonable_orders:
                logger.info(f"[RATIONALITY] {symbol} 所有委托都合理")
                return {
                    "success": True,
                    "symbol": symbol,
                    "total_orders": len(orders),
                    "cancelled_orders": [],
                    "reasons": []
                }
            
            # 3. 取消不合理委托
            cancelled_ids = self._cancel_unreasonable_orders(symbol, unreasonable_orders)
            
            # 4. 记录清理原因
            reasons = self._build_reasons(unreasonable_orders)
            
            logger.info(f"[RATIONALITY] {symbol} 清理完成：取消 {len(cancelled_ids)} 个不合理委托")
            
            return {
                "success": True,
                "symbol": symbol,
                "total_orders": len(orders),
                "cancelled_orders": cancelled_ids,
                "cancelled_count": len(cancelled_ids),
                "reasons": reasons,
                "unreasonable_orders": unreasonable_orders
            }
            
        except Exception as e:
            logger.error(f"[RATIONALITY] 检查失败：{e}")
            return {
                "success": False,
                "symbol": symbol,
                "error": str(e)
            }
    
    def _fetch_orders(self, symbol: str, side: Optional[str] = None) -> List[Dict]:
        """从交易所拉取现有委托"""
        try:
            orders = self.order_executor.get_existing_orders(symbol, side)
            return orders or []
        except Exception as e:
            logger.error(f"拉取委托失败：{e}")
            return []
    
    def _find_unreasonable_orders(self, orders: List[Dict]) -> List[Dict]:
        """查找不合理委托"""
        unreasonable = []
        
        # 1. 检查数量太多
        if len(orders) > self.max_orders:
            # 超过最大数量，标记多余的委托
            excess_count = len(orders) - self.max_orders
            # 按时间排序，取消最早的
            sorted_orders = sorted(orders, key=lambda x: self._parse_order_time(x))
            unreasonable.extend(sorted_orders[:excess_count])
            logger.warning(f"委托数量过多：{len(orders)} > {self.max_orders}，标记 {excess_count} 个")
        
        # 2. 检查间隔太近
        close_spacing_ids = self._find_close_spacing_orders(orders)
        unreasonable.extend(close_spacing_ids)
        
        # 3. 检查时间太久
        timeout_ids = self._find_timeout_orders(orders)
        unreasonable.extend(timeout_ids)
        
        # 去重
        seen_ids = set()
        unique_unreasonable = []
        for order in unreasonable:
            order_id = order.get("order_id", "")
            if order_id and order_id not in seen_ids:
                seen_ids.add(order_id)
                unique_unreasonable.append(order)
        
        return unique_unreasonable
    
    def _find_close_spacing_orders(self, orders: List[Dict]) -> List[Dict]:
        """查找间隔太近的委托"""
        if len(orders) <= 1:
            return []
        
        # 按价格排序
        sorted_orders = sorted(orders, key=lambda x: float(x.get("price", 0) or 0))
        
        close_orders = []
        for i in range(len(sorted_orders) - 1):
            price1 = float(sorted_orders[i].get("price", 0) or 0)
            price2 = float(sorted_orders[i + 1].get("price", 0) or 0)
            spacing = abs(price2 - price1)
            
            if spacing < self.min_price_spacing:
                # 标记价格较低的那个（保留价格较高的）
                close_orders.append(sorted_orders[i])
                logger.warning(
                    f"委托间隔过近：{sorted_orders[i].get('order_id')} @ {price1:.2f} "
                    f"与 {sorted_orders[i+1].get('order_id')} @ {price2:.2f} "
                    f"(间距={spacing:.2f} < {self.min_price_spacing:.2f})"
                )
        
        return close_orders
    
    def _find_timeout_orders(self, orders: List[Dict]) -> List[Dict]:
        """查找时间太久的委托"""
        now = datetime.now()
        timeout_orders = []
        
        for order in orders:
            order_time = self._parse_order_time(order)
            if order_time:
                elapsed = now - order_time
                if elapsed > self.order_timeout:
                    timeout_orders.append(order)
                    logger.warning(
                        f"委托时间过久：{order.get('order_id')} "
                        f"已挂单 {elapsed.total_seconds()/60:.1f} 分钟 "
                        f"(限制={self.order_timeout.total_seconds()/60:.0f} 分钟)"
                    )
        
        return timeout_orders
    
    def _cancel_unreasonable_orders(self, symbol: str, orders: List[Dict]) -> List[str]:
        """取消不合理委托"""
        order_ids = [order.get("order_id", "") for order in orders if order.get("order_id")]
        
        if not order_ids:
            return []
        
        try:
            result = self.order_executor.cancel_orders(symbol, order_ids)
            
            if result.get("success"):
                logger.info(f"[RATIONALITY] 成功取消 {len(order_ids)} 个不合理委托")
                return order_ids
            else:
                logger.error(f"取消委托失败：{result.get('error', '未知错误')}")
                return []
                
        except Exception as e:
            logger.error(f"取消委托异常：{e}")
            return []
    
    def _build_reasons(self, orders: List[Dict]) -> List[str]:
        """构建清理原因列表"""
        reasons = []
        
        # 统计各种原因
        too_many = 0
        too_close = 0
        too_old = 0
        
        for order in orders:
            reason = order.get("unreasonable_reason", "")
            if "数量过多" in reason:
                too_many += 1
            elif "间隔过近" in reason:
                too_close += 1
            elif "时间过久" in reason:
                too_old += 1
        
        if too_many > 0:
            reasons.append(f"数量过多：{too_many}个")
        if too_close > 0:
            reasons.append(f"间隔过近：{too_close}个")
        if too_old > 0:
            reasons.append(f"时间过久：{too_old}个")
        
        return reasons
    
    def _parse_order_time(self, order: Dict) -> Optional[datetime]:
        """解析委托时间"""
        try:
            # 尝试不同的时间字段
            time_fields = ["time", "timestamp", "updateTime", "createTime"]
            
            for field in time_fields:
                if field in order:
                    ts = order[field]
                    if isinstance(ts, (int, float)):
                        # 时间戳
                        if ts > 1e12:  # 毫秒
                            return datetime.fromtimestamp(ts / 1000)
                        else:  # 秒
                            return datetime.fromtimestamp(ts)
                    elif isinstance(ts, str):
                        # 字符串时间
                        try:
                            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        except:
                            continue
            
            # 默认返回当前时间（不算超时）
            return datetime.now()
            
        except Exception as e:
            logger.debug(f"解析委托时间失败：{e}")
            return datetime.now()
    
    def update_config(self, **kwargs):
        """更新配置参数"""
        if "max_orders" in kwargs:
            self.max_orders = int(kwargs["max_orders"])
        if "min_price_spacing" in kwargs:
            self.min_price_spacing = float(kwargs["min_price_spacing"])
        if "order_timeout_minutes" in kwargs:
            self.order_timeout = timedelta(minutes=int(kwargs["order_timeout_minutes"]))
        
        logger.info(
            f"委托合理性检查器配置已更新："
            f"max_orders={self.max_orders}, "
            f"min_spacing={self.min_price_spacing}, "
            f"timeout={self.order_timeout.total_seconds()/60:.0f}分钟"
        )


# 便捷函数
def check_orders(order_executor, symbol: str, side: Optional[str] = None, **kwargs) -> Dict:
    """
    快速检查并清理不合理委托
    
    使用示例:
    result = check_orders(order_executor, "BTCUSDT")
    print(f"取消的委托：{result['cancelled_orders']}")
    """
    checker = OrderRationalityChecker(order_executor, **kwargs)
    return checker.check_and_cleanup(symbol, side)
