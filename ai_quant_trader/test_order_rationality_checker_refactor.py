from datetime import datetime, timedelta

from execution.order_rationality_checker import OrderRationalityChecker


class MockExecutor:
    def __init__(self, orders, current_price=70000.0):
        self._orders = orders
        self.current_price = current_price
        self.cancelled = []

    def get_existing_orders(self, symbol, side=None):
        if side:
            return [o for o in self._orders if o.get("side") == side]
        return list(self._orders)

    def get_current_price(self, symbol):
        return self.current_price

    def cancel_orders(self, symbol, order_ids):
        self.cancelled.extend(order_ids)
        return {"success": True, "cancelled": order_ids}


def test_cleanup_detects_quantity_total_and_spacing_violations():
    now_ms = int(datetime.now().timestamp() * 1000)
    orders = [
        {"order_id": "1", "side": "BUY", "type": "LIMIT", "price": 69990, "quantity": 0.004, "time": now_ms},
        {"order_id": "2", "side": "BUY", "type": "LIMIT", "price": 69995, "quantity": 0.01, "time": now_ms},
        {"order_id": "3", "side": "BUY", "type": "LIMIT", "price": 70000, "quantity": 0.01, "time": now_ms},
    ]
    ex = MockExecutor(orders)
    checker = OrderRationalityChecker(
        ex,
        max_orders=4,
        min_price_spacing=10,
        min_order_quantity=0.005,
        max_total_quantity=0.02,
    )

    result = checker.check_and_cleanup("BTCUSDT")
    assert result["cancelled_count"] >= 1
    assert any("单笔数量过小" in r for r in result["reasons"])
    assert any("同类型(LIMIT)间距过近" in r for r in result["reasons"])


def test_cleanup_rejects_conditional_take_profit_and_accepts_limit_reduce_only():
    now_ms = int(datetime.now().timestamp() * 1000)
    orders = [
        {
            "order_id": "tp_bad",
            "side": "SELL",
            "type": "TAKE_PROFIT",  # 条件委托，禁止
            "stop_price": 71000,
            "price": 0,
            "quantity": 0.01,
            "closePosition": False,
            "reduceOnly": False,
            "time": now_ms,
        },
        {
            "order_id": "tp_ok",
            "side": "SELL",
            "type": "LIMIT",
            "price": 71000,
            "quantity": 0.01,
            "reduceOnly": True,
            "closePosition": False,
            "time": now_ms,
        }
    ]
    ex = MockExecutor(orders, current_price=70000)
    checker = OrderRationalityChecker(ex)

    result = checker.check_and_cleanup("BTCUSDT")
    assert "tp_bad" in result["cancelled_orders"]
    assert any("禁止条件委托" in r for r in result["reasons"])
    assert "tp_ok" not in result["cancelled_orders"]


def test_cleanup_detects_timeout_and_far_price():
    old_ms = int((datetime.now() - timedelta(minutes=120)).timestamp() * 1000)
    orders = [
        {"order_id": "old", "side": "BUY", "type": "LIMIT", "price": 76000, "quantity": 0.01, "time": old_ms},
    ]
    ex = MockExecutor(orders, current_price=70000)
    checker = OrderRationalityChecker(ex, order_timeout_minutes=60, max_price_distance_ratio=0.02)

    result = checker.check_and_cleanup("BTCUSDT")
    assert "old" in result["cancelled_orders"]
    assert any("委托超时" in r for r in result["reasons"])
    assert any("价格偏离过大" in r for r in result["reasons"])


def test_place_limit_take_profit_submits_limit_reduce_only():
    from execution.order_executor import OrderExecutor

    class DummyRawClient:
        def __init__(self):
            self.last_params = None

        def new_order(self, **params):
            self.last_params = params
            return {"orderId": 12345, "status": "NEW"}

    class DummyBinanceClient:
        def __init__(self):
            self.client = DummyRawClient()

        def get_open_orders(self, symbol):
            return []

    ex = OrderExecutor(DummyBinanceClient(), testnet=False)
    ex.tick_sizes["BTCUSDT"] = 0.1
    ex.step_sizes["BTCUSDT"] = 0.001

    result = ex.place_limit_take_profit("BTCUSDT", "long", 0.006, 71586.0)
    assert result["success"] is True
    params = ex.client.client.last_params
    assert params["type"] == "LIMIT"
    assert params["reduceOnly"] is True
    assert params["side"] == "SELL"
