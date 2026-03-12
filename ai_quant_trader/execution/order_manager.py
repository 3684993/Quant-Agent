"""OrderManager - 统一管理委托订单生命周期。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger("ai_quant_trader")


class OrderManager:
    """委托管理模块。

    规则：
    1) 最大委托数量=4
    2) 价格间隔>=100
    3) 检查委托方向
    4) 检查委托与当前价格距离
    5) 取消过期订单
    """

    def __init__(self, order_executor, market_analyzer=None, order_timeout_minutes: int = 60):
        self.order_executor = order_executor
        self.market_analyzer = market_analyzer
        self.max_orders_per_symbol = 4
        self.min_price_spacing = 100.0
        self.max_price_distance_ratio = 0.02
        self.order_timeout = timedelta(minutes=order_timeout_minutes)
        self.inspection_records: Dict[str, Dict] = {}

    def inspect_all_orders(self, symbol: str, intended_side: Optional[str] = None) -> Dict:
        orders = self.order_executor.get_existing_orders(symbol) or []

        inspections = {
            "quantity_check": self._check_max_orders(orders),
            "spacing_check": self._check_price_spacing(orders),
            "direction_check": self._check_direction(orders, intended_side),
            "distance_check": self._check_price_distance(symbol, orders),
            "expiry_check": self._check_expiry(orders),
        }

        recommendations = self._build_recommendations(inspections)
        result = {
            "success": True,
            "symbol": symbol,
            "total_orders": len(orders),
            "inspections": inspections,
            "recommendations": recommendations,
        }
        self.inspection_records[symbol] = {"timestamp": datetime.now(), **result}
        return result

    def auto_cleanup_orders(self, symbol: str) -> Dict:
        report = self.inspect_all_orders(symbol)
        if not report.get("success"):
            return {"success": False, "symbol": symbol, "error": "inspect failed"}

        expired_ids = report["inspections"].get("expiry_check", {}).get("expired_order_ids", [])
        far_ids = report["inspections"].get("distance_check", {}).get("too_far_order_ids", [])
        to_cancel = list(dict.fromkeys(expired_ids + far_ids))

        cleanup_actions: List[str] = []
        if to_cancel:
            self.order_executor.cancel_orders(symbol, to_cancel)
            cleanup_actions.append(f"取消{len(to_cancel)}个订单")

        return {
            "success": True,
            "symbol": symbol,
            "cleanup_actions": cleanup_actions,
            "recommendations": report.get("recommendations", []),
        }

    def _check_max_orders(self, orders: List[Dict]) -> Dict:
        count = len(orders)
        ok = count <= self.max_orders_per_symbol
        return {
            "status": "正常" if ok else "过多",
            "order_count": count,
            "max_allowed": self.max_orders_per_symbol,
            "within_limit": ok,
            "message": f"委托数量 {count}/{self.max_orders_per_symbol}",
        }

    def _check_price_spacing(self, orders: List[Dict]) -> Dict:
        if len(orders) <= 1:
            return {"status": "正常", "meets_requirement": True, "min_spacing": 0.0, "required_spacing": self.min_price_spacing, "message": "不足两笔，跳过"}

        prices = sorted(float(order.get("price", 0.0)) for order in orders)
        min_spacing = min(abs(prices[i + 1] - prices[i]) for i in range(len(prices) - 1))
        ok = min_spacing >= self.min_price_spacing
        return {
            "status": "正常" if ok else "间距过小",
            "meets_requirement": ok,
            "min_spacing": min_spacing,
            "required_spacing": self.min_price_spacing,
            "message": f"最小间距 {min_spacing:.2f}, 要求 {self.min_price_spacing:.2f}",
        }

    def _check_direction(self, orders: List[Dict], intended_side: Optional[str]) -> Dict:
        if not orders:
            return {"status": "正常", "direction_consistent": True, "message": "无挂单"}
        if not intended_side:
            return {"status": "跳过", "direction_consistent": True, "message": "未提供目标方向"}

        intended = intended_side.upper()
        mismatched = [o.get("order_id", "unknown") for o in orders if str(o.get("side", "")).upper() != intended]
        ok = len(mismatched) == 0
        return {
            "status": "正常" if ok else "方向不一致",
            "direction_consistent": ok,
            "intended_side": intended,
            "mismatched_order_ids": mismatched,
            "message": "方向一致" if ok else f"{len(mismatched)}个方向不一致",
        }

    def _check_price_distance(self, symbol: str, orders: List[Dict]) -> Dict:
        current_price = self.order_executor.get_current_price(symbol)
        if not current_price:
            return {"status": "跳过", "message": "无法获取最新价", "too_far_order_ids": []}

        too_far: List[str] = []
        analysis: List[Dict] = []
        for order in orders:
            op = float(order.get("price", 0.0))
            distance = abs(op - current_price) / current_price if current_price else 0.0
            oid = order.get("order_id", "unknown")
            over = distance > self.max_price_distance_ratio
            if over:
                too_far.append(oid)
            analysis.append({"order_id": oid, "distance_ratio": distance, "too_far": over})

        return {
            "status": "正常" if not too_far else "距离过远",
            "current_price": current_price,
            "threshold": self.max_price_distance_ratio,
            "analysis": analysis,
            "too_far_order_ids": too_far,
            "message": "价格距离正常" if not too_far else f"{len(too_far)}个距离过远",
        }

    def _check_expiry(self, orders: List[Dict]) -> Dict:
        now = datetime.now()
        expired: List[str] = []
        for order in orders:
            order_time = self._parse_order_time(order.get("time") or order.get("timestamp"))
            if order_time and now - order_time > self.order_timeout:
                expired.append(order.get("order_id", "unknown"))

        return {
            "status": "正常" if not expired else "存在过期委托",
            "expired_order_ids": expired,
            "message": "无过期订单" if not expired else f"{len(expired)}个过期订单",
        }

    def _parse_order_time(self, value) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)) and value > 0:
            return datetime.fromtimestamp(value / 1000 if value > 1e11 else value)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                return None
        return None

    def _build_recommendations(self, inspections: Dict) -> List[str]:
        recs: List[str] = []
        if not inspections["quantity_check"].get("within_limit", True):
            recs.append("委托数量超限，先取消多余订单")
        if not inspections["spacing_check"].get("meets_requirement", True):
            recs.append("委托价格间隔不足100，重排价格层")
        if not inspections["direction_check"].get("direction_consistent", True):
            recs.append("存在反向订单，建议撤销")
        if inspections["distance_check"].get("too_far_order_ids"):
            recs.append("部分委托离现价过远，建议撤单重挂")
        if inspections["expiry_check"].get("expired_order_ids"):
            recs.append("存在过期订单，建议立即取消")
        return recs or ["所有委托状态正常"]

    def get_inspection_history(self, symbol: str, limit: int = 10) -> List[Dict]:
        if symbol not in self.inspection_records:
            return []
        return [self.inspection_records[symbol]][:limit]

    def update_config(self, new_config: Dict):
        self.min_price_spacing = float(new_config.get("min_price_spacing", self.min_price_spacing))
        self.max_orders_per_symbol = int(new_config.get("max_orders_per_symbol", self.max_orders_per_symbol))
        self.max_price_distance_ratio = float(new_config.get("price_distance_threshold", self.max_price_distance_ratio))
        logger.info("OrderManager config updated: %s", new_config)
