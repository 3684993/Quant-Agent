from __future__ import annotations

from typing import Dict, Optional

from core.logger import logger


class EntryTimingFilter:
    """Filter short-term extreme entries using 1m Bollinger/RSI/MA20."""

    def __init__(self) -> None:
        self._wait_state: Dict[str, Dict] = {}

    def evaluate(
        self,
        symbol: str,
        trend: str,
        current_price: float,
        indicators_1m: Optional[Dict],
    ) -> Dict:
        indicators_1m = indicators_1m or {}
        bb = indicators_1m.get("bollinger", {})
        upper = float(bb.get("upper", 0) or 0)
        lower = float(bb.get("lower", 0) or 0)
        ma20 = float(bb.get("middle", 0) or 0)
        rsi = float(indicators_1m.get("rsi", 50) or 50)

        bb_position = 0.5
        if upper > lower:
            bb_position = (float(current_price) - lower) / (upper - lower)

        trend_key = str(trend or "").lower()
        if trend_key in ["open_long", "long", "buy", "bullish", "trend_up"]:
            trend_key = "long"
        elif trend_key in ["open_short", "short", "sell", "bearish", "trend_down"]:
            trend_key = "short"

        state = self._wait_state.get(symbol)

        # Long-side wait rule from spec
        if trend_key == "long" and bb_position > 0.85 and rsi > 65:
            self._wait_state[symbol] = {
                "status": "WAIT_PULLBACK",
                "reason": "short_term_pullback_expected",
            }
            logger.warning(
                "ENTRY_TIMING_WAIT: %s state=WAIT_PULLBACK bb_pos=%.3f rsi=%.2f price=%.2f ma20=%.2f",
                symbol,
                bb_position,
                rsi,
                float(current_price),
                ma20,
            )
            return {
                "allow_entry": False,
                "state": "WAIT_PULLBACK",
                "reason": "short_term_pullback_expected",
                "bb_position": bb_position,
                "rsi": rsi,
                "ma20": ma20,
            }

        if state and state.get("status") == "WAIT_PULLBACK":
            pullback_ok = float(current_price) <= ma20 or bb_position < 0.6
            if not pullback_ok:
                logger.info(
                    "ENTRY_TIMING_WAIT: %s waiting pullback bb_pos=%.3f rsi=%.2f price=%.2f ma20=%.2f",
                    symbol,
                    bb_position,
                    rsi,
                    float(current_price),
                    ma20,
                )
                return {
                    "allow_entry": False,
                    "state": "WAIT_PULLBACK",
                    "reason": "pullback_not_ready",
                    "bb_position": bb_position,
                    "rsi": rsi,
                    "ma20": ma20,
                }
            self._wait_state.pop(symbol, None)

        return {
            "allow_entry": True,
            "state": "READY",
            "reason": "entry_timing_ok",
            "bb_position": bb_position,
            "rsi": rsi,
            "ma20": ma20,
        }
