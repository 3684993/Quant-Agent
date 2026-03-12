"""
Execution Planner - 智能交易执行规划器

功能：
1. 计算仓位进度和剩余委托数量
2. 自动拆单和价格梯度生成
3. 委托执行规划和管理
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from core.logger import logger
from config.settings import settings


class ExecutionPlanner:
    """交易执行规划器"""
    
    def __init__(self):
        self.params = settings.PARAMS
        self.min_trade_size = self.params["min_trade_size"]
        self.max_trade_size = self.params["max_trade_size"]
        self.max_pending_orders = self.params["max_pending_orders"]
        self.price_step_ratio = self.params["price_step_ratio"]
        
        logger.info("ExecutionPlanner initialized")
    
    def calculate_position_progress(
        self, 
        symbol: str, 
        target_size: float,
        filled_size: float,
        pending_orders: List[Dict]
    ) -> Dict:
        """计算仓位进度
        
        Args:
            symbol: 交易对
            target_size: 目标仓位大小
            filled_size: 已成交数量
            pending_orders: 未成交订单列表
            
        Returns:
            仓位进度信息
        """
        # 计算未成交订单总数量
        pending_size = sum(order.get("size", 0) for order in pending_orders)
        
        # 计算剩余需要建仓的数量（只考虑已成交的）
        remaining_size = target_size - filled_size
        
        # 计算进度百分比（基于已成交的）
        progress_pct = (filled_size / target_size * 100) if target_size > 0 else 0
        
        # 检查是否达到目标仓位（只考虑已成交的，不考虑未成交订单）
        # 这样才能实现分批建仓和补仓
        target_reached = filled_size >= target_size
        
        # 检查是否还有未成交订单
        has_pending = pending_size > 0
        
        progress_info = {
            "symbol": symbol,
            "target_size": target_size,
            "filled_size": filled_size,
            "pending_size": pending_size,
            "remaining_size": remaining_size,
            "progress_pct": progress_pct,
            "can_trade": remaining_size > self.min_trade_size and not has_pending,
            "target_reached": target_reached,
            "has_pending": has_pending
        }
        
        logger.info(f"POSITION_PROGRESS: {symbol} - "
                   f"目标:{target_size:.4f} 已成交:{filled_size:.4f} "
                   f"未成交:{pending_size:.4f} 剩余:{remaining_size:.4f} "
                   f"进度:{progress_pct:.1f}%")
        
        return progress_info
    
    def generate_split_orders(
        self, 
        symbol: str, 
        side: str, 
        target_size: float, 
        base_price: float,
        remaining_size: float
    ) -> List[Dict]:
        """生成分批委托订单
        
        Args:
            symbol: 交易对
            side: 交易方向 (long/short)
            target_size: 目标仓位大小
            base_price: 基础价格
            remaining_size: 剩余需要建仓的数量
            
        Returns:
            分批委托订单列表
        """
        # 计算需要拆分的订单数量
        num_orders = min(
            int(remaining_size / self.min_trade_size),
            self.max_pending_orders
        )
        
        if num_orders <= 0:
            logger.warning(f"ORDER_SPLIT_EXECUTED: {symbol} - 剩余数量不足最小交易单位")
            return []
        
        # 计算每个订单的大小（平均分配）
        order_size = remaining_size / num_orders
        
        # 生成价格梯度
        price_levels = self._generate_price_levels(side, base_price, num_orders)
        
        orders = []
        for i in range(num_orders):
            order = {
                "symbol": symbol,
                "side": side,
                "size": order_size,
                "price": price_levels[i],
                "order_type": "limit",
                "reduce_only": False,
                "level": i + 1,
                "total_levels": num_orders
            }
            orders.append(order)
        
        logger.info(f"ORDER_SPLIT_EXECUTED: {symbol} {side} - "
                   f"目标:{target_size:.4f} 拆分:{num_orders}单 "
                   f"每单:{order_size:.4f} 价格梯度:{price_levels}")
        
        return orders
    
    def _generate_price_levels(
        self, 
        side: str, 
        base_price: float, 
        num_orders: int
    ) -> List[float]:
        """生成价格梯度
        
        Args:
            side: 交易方向
            base_price: 基础价格
            num_orders: 订单数量
            
        Returns:
            价格梯度列表
        """
        price_levels = []
        
        if side.lower() == "long":
            # 做多：价格递减（低于市价）
            for i in range(num_orders):
                price_multiplier = 1.0 - (i + 1) * self.price_step_ratio
                price = base_price * price_multiplier
                price_levels.append(price)
        else:
            # 做空：价格递增（高于市价）
            for i in range(num_orders):
                price_multiplier = 1.0 + (i + 1) * self.price_step_ratio
                price = base_price * price_multiplier
                price_levels.append(price)
        
        return price_levels
    
    def validate_order_size(self, size: float) -> bool:
        """验证订单大小是否合法
        
        Args:
            size: 订单大小
            
        Returns:
            是否合法
        """
        if size < self.min_trade_size:
            logger.warning(f"ORDER_SIZE_CALCULATED: 订单大小{size:.4f}小于最小交易单位{self.min_trade_size:.4f}")
            return False
        
        if size > self.max_trade_size:
            logger.warning(f"ORDER_SIZE_CALCULATED: 订单大小{size:.4f}超过最大交易单位{self.max_trade_size:.4f}")
            return False
        
        return True
    
    def check_hold_time_constraint(
        self, 
        entry_time: Optional[datetime], 
        current_time: datetime
    ) -> bool:
        """检查最小持仓时间约束
        
        Args:
            entry_time: 开仓时间
            current_time: 当前时间
            
        Returns:
            是否允许平仓
        """
        if not entry_time:
            return True  # 没有持仓，允许开仓
        
        min_hold_seconds = self.params["min_hold_time"]
        hold_time = (current_time - entry_time).total_seconds()
        
        can_close = hold_time >= min_hold_seconds
        
        if not can_close:
            remaining_time = min_hold_seconds - hold_time
            logger.info(f"HOLD_TIME_CONSTRAINT: 持仓时间{hold_time:.0f}s < 最小持仓{min_hold_seconds}s, "
                       f"剩余{remaining_time:.0f}s后允许平仓")
        
        return can_close
    
    def cancel_stale_orders(
        self, 
        pending_orders: List[Dict], 
        current_time: datetime
    ) -> List[Dict]:
        """取消超时订单
        
        Args:
            pending_orders: 未成交订单列表
            current_time: 当前时间
            
        Returns:
            需要取消的订单列表
        """
        order_timeout = self.params["order_timeout"]
        stale_orders = []
        
        for order in pending_orders:
            order_time = order.get("timestamp")
            if not order_time:
                continue
                
            if isinstance(order_time, str):
                try:
                    order_time = datetime.fromisoformat(order_time.replace('Z', '+00:00'))
                except:
                    continue
            
            time_diff = (current_time - order_time).total_seconds()
            
            if time_diff > order_timeout:
                stale_orders.append(order)
                logger.info(f"STALE_ORDER_CANCELLED: {order.get('symbol')} - "
                           f"订单{order.get('order_id')}超时{time_diff:.0f}s > {order_timeout}s")
        
        return stale_orders
    
    def get_execution_summary(self, progress_info: Dict) -> str:
        """获取执行摘要
        
        Args:
            progress_info: 仓位进度信息
            
        Returns:
            执行摘要字符串
        """
        symbol = progress_info["symbol"]
        target_size = progress_info["target_size"]
        filled_size = progress_info["filled_size"]
        pending_size = progress_info["pending_size"]
        progress_pct = progress_info["progress_pct"]
        
        summary = (f"{symbol}执行摘要: 目标{target_size:.4f} | "
                  f"已成交{filled_size:.4f} | 未成交{pending_size:.4f} | "
                  f"进度{progress_pct:.1f}%")
        
        if progress_info["target_reached"]:
            summary += " | 目标已达成"
        elif not progress_info["can_trade"]:
            summary += " | 剩余数量不足"
        
        return summary