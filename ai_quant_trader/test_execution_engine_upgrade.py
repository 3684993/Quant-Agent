from datetime import datetime, timedelta

from core.entry_timing_filter import EntryTimingFilter
from core.execution_planner import ExecutionPlanner
from core.order_adjuster import OrderAdjuster
from core.order_manager import OrderManager


class MockExecutor:
    def __init__(self):
        self.current_price = 70100.0
        self.orders = []
        self.cancelled = []
        self.created = []

    def get_existing_orders(self, symbol):
        return list(self.orders)

    def get_current_price(self, symbol):
        return self.current_price

    def cancel_orders(self, symbol, order_ids=None):
        order_ids = order_ids or [o["order_id"] for o in self.orders]
        self.cancelled.extend(order_ids)
        self.orders = [o for o in self.orders if str(o.get("order_id")) not in {str(i) for i in order_ids}]
        return {"success": True}

    def open_position(self, symbol, side, size, order_type="limit", price=None, reduce_only=False):
        oid = f"new_{len(self.created)+1}"
        order = {"order_id": oid, "symbol": symbol, "side": "BUY" if side == "long" else "SELL", "price": price, "quantity": size, "time": datetime.now().isoformat()}
        self.orders.append(order)
        self.created.append(order)
        return {"success": True, "order": order}


def test_entry_timing_wait_and_release():
    f = EntryTimingFilter()
    indicators = {"bollinger": {"upper": 102, "middle": 100, "lower": 98}, "rsi": 70}

    first = f.evaluate("BTCUSDT", "long", 101.8, indicators)
    assert first["allow_entry"] is False
    assert first["state"] == "WAIT_PULLBACK"

    second = f.evaluate("BTCUSDT", "long", 100.0, indicators)
    assert second["allow_entry"] is True


def test_execution_planner_split_and_distance_control():
    planner = ExecutionPlanner(min_trade_size=0.005, max_trade_size=0.02, max_pending_orders=4, price_step=100)
    orders = planner.generate_split_orders("BTCUSDT", "long", 0.02, 70100, 0.02, current_price=70100)
    assert len(orders) == 4
    assert [o["price"] for o in orders] == [70100, 70000, 69900, 69800]


def test_order_adjuster_replaces_far_order():
    ex = MockExecutor()
    ex.orders = [
        {"order_id": "1", "side": "BUY", "price": 69500, "quantity": 0.005, "time": (datetime.now() - timedelta(seconds=30)).isoformat()},
    ]
    om = OrderManager(ex)
    adjuster = OrderAdjuster(om, ex)

    result = adjuster.adjust_orders("BTCUSDT", trend_direction="long", trend_strength=0.2, pullback_detected=False)

    assert result["success"] is True
    assert "1" in ex.cancelled
    assert len(ex.created) >= 1
