from datetime import datetime, timedelta

from core.order_manager import OrderManager


class MockExecutor:
    def __init__(self):
        self.orders = []
        self.current_price = 70000.0
        self.cancelled = []

    def get_existing_orders(self, symbol):
        return self.orders

    def get_current_price(self, symbol):
        return self.current_price

    def cancel_orders(self, symbol, order_ids):
        self.cancelled.extend(order_ids)
        self.orders = [o for o in self.orders if o.get("order_id") not in order_ids]


def test_distance_uses_price_not_order_id_and_skip_market_orders():
    ex = MockExecutor()
    ex.orders = [
        {"order_id": 12761389307, "price": 70010.0, "side": "BUY", "time": datetime.now().isoformat()},
        {"order_id": 2, "price": 0.0, "side": "BUY", "time": datetime.now().isoformat()},  # market/no-price -> skip
    ]
    om = OrderManager(ex)
    report = om.inspect_all_orders("BTCUSDT", intended_side="BUY")

    # 第一单距离应按 price 计算: 10，不应被误判过远
    assert report["too_far_order_ids"] == []


def test_cancel_cooldown_blocks_recreation_window():
    ex = MockExecutor()
    ex.orders = [
        {"order_id": "stale1", "price": 71000.0, "side": "BUY", "time": (datetime.now() - timedelta(seconds=121)).isoformat()},
    ]
    om = OrderManager(ex)

    cleanup = om.auto_cleanup_orders("BTCUSDT")
    assert cleanup["cancelled"] == ["stale1"]
    assert om.can_create_orders("BTCUSDT") is False
