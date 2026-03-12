from datetime import datetime, timedelta

from core.target_position_engine import TargetPositionEngine
from core.risk_engine import RiskEngine
from core.position_manager import PositionManager


def test_signal_stability_requires_three_confirmations():
    tpe = TargetPositionEngine()
    ai = {
        "direction": "long",
        "target_size": 0.02,
        "confidence": 0.9,
        "current_price": 70000,
        "entry_range": [69900, 70100],
        "stop_loss": 69500,
        "take_profit": 71000,
    }
    state = {"has_position": False}

    r1 = tpe.update_target_position("BTCUSDT", ai, state, {"trend": "bullish"})
    r2 = tpe.update_target_position("BTCUSDT", ai, state, {"trend": "bullish"})
    r3 = tpe.update_target_position("BTCUSDT", ai, state, {"trend": "bullish"})

    assert r1["action"] == "hold"
    assert r2["action"] == "hold"
    assert r3["action"] == "open_long"


def test_risk_engine_trend_reverse_exit():
    pm = PositionManager()
    pm.update_position("BTCUSDT", position_size=0.01, entry_price=100.0, side="long", stop_loss=95, take_profit=110)
    pm.calculate_pnl(101)

    re = RiskEngine(position_manager=pm, base_risk_manager=None)
    state = pm.get_position_state()

    out = re.evaluate("BTCUSDT", state, current_price=101, trend_change=True)
    assert out["action"] == "force_close"
