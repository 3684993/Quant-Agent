from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class OrderRationalityChecker:
    """委托合理性检查器（重构版）

    检查规则：
    1. 最大挂单数（默认4）
    2. 总委托数量不超过 max_total_quantity（默认0.02）
    3. 单笔委托数量不小于 min_order_quantity（默认0.005）
    4. 同类型订单价格间距不能过近
    5. 订单超时自动清理
    6. 价格偏离当前价过远自动清理
    7. 止盈单必须是 LIMIT（禁止条件委托）
    """

    def __init__(
        self,
        order_executor,
        max_orders: int = 4,
        min_price_spacing: float = 10.0,
        order_timeout_minutes: int = 60,
        min_order_quantity: float = 0.005,
        max_total_quantity: float = 0.02,
        max_price_distance_ratio: float = 0.02,
    ):
        self.order_executor = order_executor
        self.max_orders = max_orders
        self.min_price_spacing = min_price_spacing
        self.order_timeout = timedelta(minutes=order_timeout_minutes)
        self.min_order_quantity = min_order_quantity
        self.max_total_quantity = max_total_quantity
        self.max_price_distance_ratio = max_price_distance_ratio

    def check_and_cleanup(self, symbol: str, side: Optional[str] = None) -> Dict:
        try:
            orders = self._fetch_orders(symbol, side)
            if not orders:
                return {
                    "success": True,
                    "symbol": symbol,
                    "total_orders": 0,
                    "cancelled_orders": [],
                    "cancelled_count": 0,
                    "reasons": [],
                    "summary": {},
                }

            current_price = float(self.order_executor.get_current_price(symbol) or 0.0)
            flagged = self._find_unreasonable_orders(symbol, orders, current_price)
            if not flagged:
                return {
                    "success": True,
                    "symbol": symbol,
                    "total_orders": len(orders),
                    "cancelled_orders": [],
                    "cancelled_count": 0,
                    "reasons": [],
                    "summary": self._build_summary(orders, current_price),
                }

            cancelled_ids = self._cancel_unreasonable_orders(symbol, flagged)
            reasons = self._build_reasons(flagged)
            return {
                "success": True,
                "symbol": symbol,
                "total_orders": len(orders),
                "cancelled_orders": cancelled_ids,
                "cancelled_count": len(cancelled_ids),
                "reasons": reasons,
                "summary": self._build_summary(orders, current_price),
                "unreasonable_orders": flagged,
            }
        except Exception as e:
            logger.error("[RATIONALITY] 检查失败：%s", e)
            return {"success": False, "symbol": symbol, "error": str(e)}

    def _fetch_orders(self, symbol: str, side: Optional[str] = None) -> List[Dict]:
        try:
            return self.order_executor.get_existing_orders(symbol, side) or []
        except Exception as e:
            logger.error("拉取委托失败：%s", e)
            return []

    def _find_unreasonable_orders(self, symbol: str, orders: List[Dict], current_price: float) -> List[Dict]:
        flagged: List[Dict] = []

        # 1) 数量上限：按时间从旧到新移除超出上限订单
        if len(orders) > self.max_orders:
            excess_count = len(orders) - self.max_orders
            for o in sorted(orders, key=self._parse_order_time)[:excess_count]:
                flagged.append(self._with_reason(o, f"数量过多(>{self.max_orders})"))

        # 2) 总委托量检查（仅计算开仓单，reduceOnly=False）
        opening_orders = [o for o in orders if not bool(o.get("reduceOnly") or o.get("closePosition"))]
        opening_total_qty = sum(float(o.get("quantity", 0) or 0) for o in opening_orders)
        if opening_total_qty > self.max_total_quantity:
            overflow = opening_total_qty - self.max_total_quantity
            for o in sorted(opening_orders, key=self._parse_order_time):
                if overflow <= 0:
                    break
                qty = float(o.get("quantity", 0) or 0)
                flagged.append(self._with_reason(o, f"总委托量超限(>{self.max_total_quantity:.3f})"))
                overflow -= qty

        # 3) 单笔最小数量
        for o in opening_orders:
            qty = float(o.get("quantity", 0) or 0)
            if 0 < qty < self.min_order_quantity:
                flagged.append(self._with_reason(o, f"单笔数量过小(<{self.min_order_quantity:.3f})"))

        # 4) 超时
        now = datetime.now()
        for o in orders:
            created_at = self._parse_order_time(o)
            if created_at and (now - created_at) > self.order_timeout:
                flagged.append(self._with_reason(o, f"委托超时(>{int(self.order_timeout.total_seconds()/60)}m)"))

        # 5) 价格偏离当前价过远（限价和止盈触发价都检查）
        if current_price > 0:
            for o in orders:
                reference_price = self._extract_order_price(o)
                if reference_price <= 0:
                    continue
                ratio = abs(reference_price - current_price) / current_price
                if ratio > self.max_price_distance_ratio:
                    flagged.append(self._with_reason(o, f"价格偏离过大(>{self.max_price_distance_ratio:.2%})"))

        # 6) 同类型间距过近
        flagged.extend(self._find_close_spacing_orders(orders))

        # 7) 止盈委托合法性
        flagged.extend(self._find_invalid_take_profit_orders(symbol, orders, current_price))

        # 去重（保留最先发现原因）
        unique: Dict[str, Dict] = {}
        for o in flagged:
            oid = str(o.get("order_id", ""))
            if not oid:
                continue
            if oid not in unique:
                unique[oid] = o
            else:
                existing = unique[oid].setdefault("unreasonable_reasons", [])
                if not isinstance(existing, list):
                    existing = [str(unique[oid].get("unreasonable_reason", ""))]
                    unique[oid]["unreasonable_reasons"] = existing
                for reason in o.get("unreasonable_reasons", [o.get("unreasonable_reason", "")]):
                    if reason and reason not in existing:
                        existing.append(reason)
                unique[oid]["unreasonable_reason"] = " | ".join(existing)
        return list(unique.values())

    def _find_close_spacing_orders(self, orders: List[Dict]) -> List[Dict]:
        buckets: Dict[str, List[Dict]] = {}
        for o in orders:
            t = str(o.get("type", "LIMIT") or "LIMIT").upper()
            buckets.setdefault(t, []).append(o)

        close_orders: List[Dict] = []
        for order_type, same_type_orders in buckets.items():
            priced = [o for o in same_type_orders if self._extract_order_price(o) > 0]
            if len(priced) <= 1:
                continue
            sorted_orders = sorted(priced, key=self._extract_order_price)
            for i in range(len(sorted_orders) - 1):
                p1 = self._extract_order_price(sorted_orders[i])
                p2 = self._extract_order_price(sorted_orders[i + 1])
                spacing = abs(p2 - p1)
                if spacing < self.min_price_spacing:
                    close_orders.append(self._with_reason(sorted_orders[i], f"同类型({order_type})间距过近(<{self.min_price_spacing})"))
        return close_orders

    def _find_invalid_take_profit_orders(self, symbol: str, orders: List[Dict], current_price: float) -> List[Dict]:
        """检查止盈委托是否合法：仅允许普通 LIMIT，禁止条件止盈委托。"""
        invalid: List[Dict] = []
        for o in orders:
            order_type = str(o.get("type", "") or "").upper()
            side = str(o.get("side", "") or "").upper()
            qty = float(o.get("quantity", 0) or 0)
            price = float(o.get("price", 0) or 0)

            # 条件委托一律视为不合规
            if order_type in {"TAKE_PROFIT", "TAKE_PROFIT_MARKET", "STOP", "STOP_MARKET", "STOP_LOSS", "STOP_LOSS_LIMIT"}:
                invalid.append(self._with_reason(o, "止盈类型错误(禁止条件委托，需普通LIMIT)"))
                continue

            # 非 LIMIT 且看起来是止盈语义的委托，判为不合理
            if order_type not in {"", "LIMIT"}:
                invalid.append(self._with_reason(o, "止盈类型错误(必须LIMIT)"))
                continue

            # 对 LIMIT 做基础价格/数量与方向检查（不再要求 reduceOnly）
            if order_type == "LIMIT":
                reason = None
                if qty <= 0:
                    reason = "止盈数量不合法"
                elif price <= 0:
                    reason = "止盈价格不合法"
                elif current_price > 0:
                    if side == "SELL" and price <= current_price:
                        reason = "多头止盈价格不合理(应高于现价)"
                    if side == "BUY" and price >= current_price:
                        reason = "空头止盈价格不合理(应低于现价)"

                if reason:
                    invalid.append(self._with_reason(o, reason))
                    logger.warning("[RATIONALITY] %s 检测到不合理止盈单: order=%s reason=%s", symbol, o.get("order_id"), reason)

        return invalid

    def _cancel_unreasonable_orders(self, symbol: str, orders: List[Dict]) -> List[str]:
        ids = [str(o.get("order_id")) for o in orders if o.get("order_id")]
        if not ids:
            return []
        result = self.order_executor.cancel_orders(symbol, ids)
        return ids if result.get("success") else []

    def _build_reasons(self, orders: List[Dict]) -> List[str]:
        counts: Dict[str, int] = {}
        for o in orders:
            reasons = o.get("unreasonable_reasons") or [o.get("unreasonable_reason", "未知原因")]
            for reason in reasons:
                reason = str(reason or "未知原因")
                counts[reason] = counts.get(reason, 0) + 1
        return [f"{k}：{v}个" for k, v in sorted(counts.items(), key=lambda x: x[0])]

    def _build_summary(self, orders: List[Dict], current_price: float) -> Dict:
        opening_orders = [o for o in orders if not bool(o.get("reduceOnly") or o.get("closePosition"))]
        return {
            "current_price": current_price,
            "order_count": len(orders),
            "opening_order_count": len(opening_orders),
            "opening_total_quantity": sum(float(o.get("quantity", 0) or 0) for o in opening_orders),
        }

    def _with_reason(self, order: Dict, reason: str) -> Dict:
        d = dict(order)
        reasons = list(d.get("unreasonable_reasons", []))
        if reason not in reasons:
            reasons.append(reason)
        d["unreasonable_reasons"] = reasons
        d["unreasonable_reason"] = " | ".join(reasons)
        return d

    def _extract_order_price(self, order: Dict) -> float:
        price = float(order.get("price", 0) or 0)
        if price > 0:
            return price
        return float(order.get("stop_price", 0) or 0)

    def _parse_order_time(self, order: Dict) -> datetime:
        for field in ["time", "timestamp", "updateTime", "createTime"]:
            ts = order.get(field)
            if isinstance(ts, (int, float)) and ts > 0:
                return datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts)
            if isinstance(ts, str):
                try:
                    return datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass
        return datetime.now()

    def update_config(self, **kwargs):
        self.max_orders = int(kwargs.get("max_orders", self.max_orders))
        self.min_price_spacing = float(kwargs.get("min_price_spacing", self.min_price_spacing))
        self.order_timeout = timedelta(minutes=int(kwargs.get("order_timeout_minutes", self.order_timeout.total_seconds() / 60)))
        self.min_order_quantity = float(kwargs.get("min_order_quantity", self.min_order_quantity))
        self.max_total_quantity = float(kwargs.get("max_total_quantity", self.max_total_quantity))
        self.max_price_distance_ratio = float(kwargs.get("max_price_distance_ratio", self.max_price_distance_ratio))


# 便捷函数
def check_orders(order_executor, symbol: str, side: Optional[str] = None, **kwargs) -> Dict:
    checker = OrderRationalityChecker(order_executor, **kwargs)
    return checker.check_and_cleanup(symbol, side)
