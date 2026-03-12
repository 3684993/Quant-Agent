from ai.decision_engine import DecisionEngine


class MockLLM:
    def __init__(self, response):
        self.response = response

    def chat_json(self, messages, temperature=0.3, max_tokens=2000):
        return self.response


def test_entry_range_must_cover_current_price_and_follow_formula():
    engine = DecisionEngine(llm_client=MockLLM({
        "direction": "short",
        "target_size": 0.02,
        "current_price": 70131,
        "entry_range": [70050, 70200],
        "stop_loss": 70300,
        "take_profit": 69800,
        "expected_hold_minutes": 60,
        "confidence": 0.9,
    }))

    context = {
        "price": 70131,
        "indicators": {"atr": 80},
        "market_summary": {"volatility": "high", "trend": "down", "macd_signal": "down"},
        "position": {"has_position": False},
    }

    result = engine.generate_trade_decision(context)
    assert result["current_price"] == 70131
    # ATR*0.5=40, max(40,100)=100
    assert result["entry_range"] == [70031.0, 70231.0]
    assert result["entry_range"][0] <= result["current_price"] <= result["entry_range"][1]


def test_output_contains_required_fields():
    engine = DecisionEngine(llm_client=MockLLM(None))
    context = {
        "price": 70131,
        "indicators": {"atr": 300},
        "market_summary": {"volatility": "medium"},
        "position": {"has_position": False},
    }

    result = engine.generate_trade_decision(context)
    for key in ["direction", "target_size", "current_price", "entry_range", "stop_loss", "take_profit", "confidence"]:
        assert key in result
