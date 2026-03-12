from __future__ import annotations

from typing import Dict

from core.logger import logger


class RiskEngine:
    """统一风险引擎：止损、止盈、动态止盈、趋势反转退出。"""

    def __init__(self, position_manager, base_risk_manager=None):
        self.position_manager = position_manager
        self.base_risk_manager = base_risk_manager

    def evaluate(self, symbol: str, position_state: Dict, current_price: float, trend_change: bool = False) -> Dict:
        if not position_state.get("has_position"):
            return {"action": "hold", "reason": "NO_POSITION"}

        # 1) 趋势反转优先退出
        if trend_change:
            return {"action": "force_close", "reason": "TREND_REVERSE_EXIT"}

        # 2) 本地止损止盈
        sltp = self.position_manager.check_local_sl_tp(symbol, current_price)
        if sltp.get("triggered"):
            return {"action": "force_close", "reason": sltp.get("trigger_type", "SLTP")}

        # 3) 动态止盈（追踪止损）
        trailing = self.position_manager.dynamic_trailing_stop(symbol, current_price)
        if trailing.get("adjusted"):
            logger.info(
                "TRAILING_STOP_TRIGGERED: %s old=%.4f new=%.4f", symbol,
                float(trailing.get("old_stop_loss", 0.0)),
                float(trailing.get("new_stop_loss", 0.0)),
            )

        # 4) 叠加基础风险规则
        if self.base_risk_manager:
            base = self.base_risk_manager.check_risk(position_state)
            if base.get("action") == "force_close":
                return {"action": "force_close", "reason": "BASE_RISK_ENGINE"}

        return {"action": "hold", "reason": "RISK_OK"}
