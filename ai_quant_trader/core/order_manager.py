from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from core.logger import logger
from config.settings import settings


class OrderManager:
    def __init__(self, order_executor, market_analyzer=None):
        self.order_executor = order_executor
        self.max_orders = int(settings.PARAMS.get("max_orders", 4))
        self.price_gap = float(settings.PARAMS.get("price_gap", 100))
        self.order_timeout = int(settings.PARAMS.get("order_timeout", 120))
        self.too_far_distance = float(settings.PARAMS.get("too_far_distance", 500.0))
        self.market_analyzer = market_analyzer
        self.last_trend_by_symbol: Dict[str, str] = {}

        # 防止取消循环：symbol -> {reason, cancel_time}
        self.cancel_history: Dict[str, Dict] = {}
        self.cancel_cooldown_seconds = 300

    def inspect_all_orders(self, symbol: str, intended_side: Optional[str] = None) -> Dict:
        orders = self.order_executor.get_existing_orders(symbol) or []
        if len(orders) > self.max_orders:
            logger.warning(f"ORDER_SPLIT_EXECUTED: {symbol} existing_orders={len(orders)} > {self.max_orders}")

        # 仅统计有效限价价格（市价单/无价格单跳过）
        valid_prices = []
        for o in orders:
            try:
                p = float(o.get("price", 0.0) or 0.0)
            except Exception:
                p = 0.0
            if p > 0:
                valid_prices.append(p)
        valid_prices.sort()
        min_gap = min([abs(valid_prices[i + 1] - valid_prices[i]) for i in range(len(valid_prices) - 1)]) if len(valid_prices) > 1 else 0.0

        current_price = float(self.order_executor.get_current_price(symbol) or 0.0)
        too_far_ids: List[str] = []
        low_prob_ids: List[str] = []
        wrong_dir_ids: List[str] = []

        for o in orders:
            oid = o.get("order_id", "unknown")

            if intended_side and str(o.get("side", "")).upper() != intended_side.upper():
                wrong_dir_ids.append(oid)

            # 关键修复：距离必须使用订单 price，严禁用 order_id
            try:
                order_price = float(o.get("price", 0.0) or 0.0)
            except Exception:
                order_price = 0.0

            # 市价单/无价格订单跳过距离检查
            if order_price <= 0 or current_price <= 0:
                continue

            order_distance = abs(order_price - current_price)
            logger.info(
                f"ORDER_DISTANCE_CHECK: {symbol} order={oid} price={order_price:.2f} "
                f"current={current_price:.2f} distance={order_distance:.2f}"
            )

            # 每5秒巡检时仅 distance>500 才取消
            if order_distance > self.too_far_distance:
                logger.warning(f"ORDER_DISTANCE_TOO_FAR: {symbol} order={oid} distance={order_distance:.2f}")
                too_far_ids.append(oid)

            prob = self._estimate_fill_probability(order_price, current_price, str(o.get("side", "BUY")))
            if prob < 0.3:
                low_prob_ids.append(oid)

        stale_ids = self._find_stale_orders(orders)
        trend_changed = self._detect_trend_change(symbol)

        return {
            "success": True,
            "symbol": symbol,
            "total_orders": len(orders),
            "min_gap": min_gap,
            "gap_ok": min_gap >= self.price_gap if len(valid_prices) > 1 else True,
            "wrong_direction_order_ids": wrong_dir_ids,
            "too_far_order_ids": too_far_ids,
            "low_probability_order_ids": low_prob_ids,
            "stale_order_ids": stale_ids,
            "trend_changed": trend_changed,
        }

    def can_create_orders(self, symbol: str) -> bool:
        info = self.cancel_history.get(symbol)
        if not info:
            return True

        elapsed = (datetime.now() - info["cancel_time"]).total_seconds()
        if elapsed < self.cancel_cooldown_seconds:
            logger.warning(
                f"ORDER_CANCEL_REASON: {symbol} cooldown_active reason={info['reason']} "
                f"elapsed={elapsed:.0f}s<{self.cancel_cooldown_seconds}s"
            )
            return False
        return True

    def auto_cleanup_orders(self, symbol: str) -> Dict:
        report = self.inspect_all_orders(symbol)

        cancel_with_reason: List[tuple] = []
        for oid in report.get("too_far_order_ids", []):
            cancel_with_reason.append((oid, "DISTANCE_TOO_FAR"))
        for oid in report.get("stale_order_ids", []):
            cancel_with_reason.append((oid, "TIMEOUT"))

        unique = {}
        for oid, reason in cancel_with_reason:
            unique[oid] = reason
        cancel_ids = list(unique.keys())
        if cancel_ids:
            self.order_executor.cancel_orders(symbol, cancel_ids)
            last_reason = list(unique.values())[-1]
            self.cancel_history[symbol] = {
                "reason": last_reason,
                "cancel_time": datetime.now(),
            }
            logger.warning(f"ORDER_CANCEL_REASON: {symbol} reason={last_reason} count={len(cancel_ids)}")
            for oid, reason in cancel_with_reason:
                if reason == "TIMEOUT":
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

    def _detect_trend_change(self, symbol: str) -> bool:
        if not self.market_analyzer:
            return False
        try:
            summary = self.market_analyzer.get_market_summary(symbol)
            trend = str(summary.get("trend", "neutral"))
            prev = self.last_trend_by_symbol.get(symbol)
            self.last_trend_by_symbol[symbol] = trend
            return prev is not None and prev != trend
        except Exception:
            return False
