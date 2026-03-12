from datetime import datetime, timedelta

from core.trade_guard import TradeGuard
from execution.position_manager import PositionManager


def test_trade_guard_min_hold_allows_early_close_on_net_profit():
    tg = TradeGuard()
    tg.position_metadata["BTCUSDT"] = {
        "entry_time": datetime.now() - timedelta(seconds=30),
        "expected_hold_minutes": 60,
    }

    # 盈利但持仓时间不足 120s，允许提前平仓
    state_profit = {
        "has_position": True,
        "current_pnl": 12.0,
        "fees": 1.0,
        "trend_strength": "normal",
    }
    d = {"action": "close_position"}
    r1 = tg.validate_decision(d, "BTCUSDT", state_profit)
    assert r1["action"] == "close_position"

    # 亏损且持仓时间不足，禁止平仓
    state_loss = {
        "has_position": True,
        "current_pnl": -2.0,
        "fees": 1.0,
        "trend_strength": "normal",
    }
    r2 = tg.validate_decision(d, "BTCUSDT", state_loss)
    assert r2["action"] == "hold"


def test_trade_guard_strong_trend_extends_hold_window():
    tg = TradeGuard()
    tg.position_metadata["BTCUSDT"] = {
        "entry_time": datetime.now() - timedelta(seconds=180),
        "expected_hold_minutes": 60,
    }

    # 强趋势下要求 240s，180s 仍不足，且净利润<=0 时禁止平仓
    state = {
        "has_position": True,
        "current_pnl": 0.0,
        "fees": 0.0,
        "trend_strength": "strong",
    }
    r = tg.validate_decision({"action": "close_position"}, "BTCUSDT", state)
    assert r["action"] == "hold"


def test_dynamic_trailing_stop_thresholds_long():
    pm = PositionManager()
    pm.update_position("BTCUSDT", position_size=0.01, entry_price=100.0, side="long", stop_loss=0)

    # >0.5% => SL = entry
    r1 = pm.dynamic_trailing_stop("BTCUSDT", 100.6)
    assert r1["adjusted"] is True
    assert abs(pm.get_position_state()["stop_loss"] - 100.0) < 1e-6

    # >1% => 锁定 0.3%
    r2 = pm.dynamic_trailing_stop("BTCUSDT", 101.2)
    assert r2["adjusted"] is True
    assert abs(pm.get_position_state()["stop_loss"] - 100.3) < 1e-6

    # >2% => 锁定 1%
    r3 = pm.dynamic_trailing_stop("BTCUSDT", 102.5)
    assert r3["adjusted"] is True
    assert abs(pm.get_position_state()["stop_loss"] - 101.0) < 1e-6
