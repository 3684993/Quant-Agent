from datetime import datetime, timedelta

from core.execution_planner import ExecutionPlanner
from execution.order_manager import OrderManager
from execution.position_manager import PositionManager


def test_execution_planner_split_example():
    planner = ExecutionPlanner()
    orders = planner.generate_split_orders(
        symbol="BTCUSDT",
        side="long",
        target_size=0.02,
        base_price=70000.0,
        remaining_size=0.02,
    )
    assert len(orders) == 4
    assert all(abs(o["size"] - 0.005) < 1e-6 for o in orders)


def test_order_manager_rules():
    class MockExecutor:
        def __init__(self):
            self.orders = [
                {"order_id": "1", "side": "BUY", "price": 70100.0, "time": (datetime.now() - timedelta(minutes=80)).isoformat()},
                {"order_id": "2", "side": "BUY", "price": 70150.0, "time": datetime.now().isoformat()},
            ]

        def get_existing_orders(self, symbol):
            return self.orders

        def get_current_price(self, symbol):
            return 70000.0

        def cancel_orders(self, symbol, order_ids):
            self.orders = [o for o in self.orders if o["order_id"] not in order_ids]
            return {"success": True}

    om = OrderManager(MockExecutor())
    report = om.inspect_all_orders("BTCUSDT", intended_side="BUY")
    assert report["inspections"]["spacing_check"]["meets_requirement"] is False
    assert report["inspections"]["expiry_check"]["expired_order_ids"] == ["1"]


def test_position_manager_unified_fields():
    pm = PositionManager()
    pm.update_position("BTCUSDT", position_size=0.01, entry_price=70000, side="long")
    pm.calculate_pnl(70100)
    state = pm.get_position_state()

    for key in ["entry_price", "position_size", "entry_time", "pnl", "fees"]:
        assert key in state
