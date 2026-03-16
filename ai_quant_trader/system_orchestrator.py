"""AI Quant Trader v1.0 orchestrator entrypoint (compatibility module)."""

from system.orchestrator import SystemOrchestrator
from core.target_position_engine import TargetPositionEngine
from core.execution_planner import ExecutionPlanner
from core.order_manager import OrderManager
from core.order_adjuster import OrderAdjuster
from core.entry_timing_filter import EntryTimingFilter
from core.position_manager import PositionManager
from core.risk_engine import RiskEngine


def create_orchestrator() -> SystemOrchestrator:
    """Factory for external callers that import `system_orchestrator`."""
    return SystemOrchestrator()


__all__ = ["SystemOrchestrator", "create_orchestrator", "TargetPositionEngine", "ExecutionPlanner", "OrderManager", "OrderAdjuster", "EntryTimingFilter", "PositionManager", "RiskEngine"]
