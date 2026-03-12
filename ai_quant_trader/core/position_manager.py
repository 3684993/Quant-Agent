from __future__ import annotations

from execution.position_manager import PositionManager as _ExecutionPositionManager
from core.logger import logger


class PositionManager(_ExecutionPositionManager):
    """Core PositionManager with unified access contract."""

    def dynamic_trailing_stop(self, symbol: str, current_price: float):
        result = super().dynamic_trailing_stop(symbol, current_price)
        if result.get("adjusted"):
            logger.info(
                "TRAILING_STOP_TRIGGERED: %s old=%.4f new=%.4f profit=%.2f%%",
                symbol,
                float(result.get("old_stop_loss", 0.0)),
                float(result.get("new_stop_loss", 0.0)),
                float(result.get("profit_pct", 0.0)),
            )
        return result
