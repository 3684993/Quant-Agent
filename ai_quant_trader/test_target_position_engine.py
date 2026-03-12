from core.target_position_engine import TargetPositionEngine


def test_target_position_engine_outputs_action_from_target_position():
    tpe = TargetPositionEngine()
    ai_decision = {
        "direction": "long",
        "target_size": 0.02,
        "confidence": 0.9,
        "current_price": 70000,
        "entry_range": [69900, 70100],
        "stop_loss": 69500,
        "take_profit": 71000,
    }
    position_state = {"has_position": False}
    out = tpe.update_target_position("BTCUSDT", ai_decision, position_state, {"trend": "bullish"})
    assert out["action"] == "open_long"
    assert out["target_size"] == 0.02


def test_target_position_engine_flat_closes_existing_position():
    tpe = TargetPositionEngine()
    out = tpe.update_target_position(
        "BTCUSDT",
        {"direction": "flat", "target_size": 0, "confidence": 1.0, "current_price": 70000, "entry_range": [69900, 70100], "stop_loss": 0, "take_profit": 0},
        {"has_position": True, "side": "long", "position_size": 0.01},
        {"trend": "bearish"},
    )
    assert out["action"] == "close_position"
