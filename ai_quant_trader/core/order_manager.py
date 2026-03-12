from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from core.logger import logger
from config.settings import settings


class OrderManager:
    def __init__(self, order_executor, market_analyzer=None):
        self.order_executor = order_executor
        self.max_orders = int(settings.PARAMS.get("max_orders", 4))
        self.price_gap = float(settings.PARAMS.get("price_gap", 100))
        self.order_timeout = int(settings.PARAMS.get("order_timeout", 120))
        self.too_far_distance = 500.0
        self.market_analyzer = market_analyzer

    def inspect_all_orders(self, symbol: str, intended_side: Optional[str] = None) -> Dict:
        orders = self.order_executor.get_existing_orders(symbol) or []
        if len(orders) > self.max_orders:
            logger.warning(f"ORDER_SPLIT_EXECUTED: {symbol} existing_orders={len(orders)} > {self.max_orders}")

        prices = sorted(float(o.get("price", 0.0)) for o in orders)
        min_gap = min([abs(prices[i+1] - prices[i]) for i in range(len(prices)-1)]) if len(prices) > 1 else 0.0

        current_price = self.order_executor.get_current_price(symbol) or 0.0
        too_far_ids = []
        low_prob_ids = []
        wrong_dir_ids = []
        for o in orders:
            oid = o.get("order_id", "unknown")
            if intended_side and str(o.get("side", "")).upper() != intended_side.upper():
                wrong_dir_ids.append(oid)

            distance = abs(float(o.get("price", 0.0)) - float(current_price))
            if distance > self.too_far_distance:
                logger.warning(f"ORDER_DISTANCE_TOO_FAR: {symbol} order={oid} distance={distance:.2f}")
                too_far_ids.append(oid)

            prob = self._estimate_fill_probability(float(o.get("price", 0.0)), float(current_price), str(o.get("side", "BUY")))
            if prob < 0.3:
                low_prob_ids.append(oid)

        stale_ids = self._find_stale_orders(orders)
        return {
            "success": True,
            "symbol": symbol,
            "total_orders": len(orders),
            "min_gap": min_gap,
            "gap_ok": min_gap >= self.price_gap if len(orders) > 1 else True,
            "wrong_direction_order_ids": wrong_dir_ids,
            "too_far_order_ids": too_far_ids,
            "low_probability_order_ids": low_prob_ids,
            "stale_order_ids": stale_ids,
        }

    def auto_cleanup_orders(self, symbol: str) -> Dict:
        report = self.inspect_all_orders(symbol)
        cancel_ids = list(dict.fromkeys(report.get("too_far_order_ids", []) + report.get("stale_order_ids", [])))
        if cancel_ids:
            self.order_executor.cancel_orders(symbol, cancel_ids)
            for oid in report.get("stale_order_ids", []):
                logger.info(f"STALE_ORDER_CANCELLED: {symbol} order={oid}")
        return {"success": True, "cancelled": cancel_ids}

    def _find_stale_orders(self, orders: List[Dict]) -> List[str]:
        now = datetime.now()
        stale = []
        for o in orders:
            ts = o.get("time") or o.get("timestamp")
            t = None
            if isinstance(ts, (int, float)):
                t = datetime.fromtimestamp(ts / 1000 if ts > 1e11 else ts)
            elif isinstance(ts, str):
                try:
                    t = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    pass
            elif isinstance(ts, datetime):
                t = ts
            if t and (now - t).total_seconds() > self.order_timeout:
                stale.append(o.get("order_id", "unknown"))
        return stale

    def _estimate_fill_probability(self, order_price: float, current_price: float, side: str) -> float:
        if current_price <= 0:
            return 0.0
        diff = abs(order_price - current_price) / current_price
        base = max(0.0, 1.0 - diff * 20)
        return min(1.0, base)
