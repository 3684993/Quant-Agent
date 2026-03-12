"""AI Quant Trader v1.0 orchestrator entrypoint (compatibility module)."""

from system.orchestrator import SystemOrchestrator


def create_orchestrator() -> SystemOrchestrator:
    """Factory for external callers that import `system_orchestrator`."""
    return SystemOrchestrator()


__all__ = ["SystemOrchestrator", "create_orchestrator"]
