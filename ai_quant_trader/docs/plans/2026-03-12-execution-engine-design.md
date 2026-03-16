Title: Execution Engine Design (Entry/Exit State Machine)
Date: 2026-03-12

Overview
This design adds a dedicated ExecutionEngine, SlippageEstimator, and ExecutionTracker,
while keeping OrderExecutor as the low-level order sender. The ExecutionEngine sits
between Scheduler and OrderExecutor, managing a task-based state machine for both
entry and exit flows. Each task tracks remaining quantity, order states, retries,
time budgets, and slippage controls. The goal is to improve fill reliability, handle
timeouts deterministically, and unify execution policy across open/add/close/SL/TP.

State Machine
ORDER_CREATED -> PASSIVE_LIMIT -> ADJUST_LIMIT -> AGGRESSIVE_LIMIT -> MARKET_FALLBACK
-> ORDER_FILLED / ORDER_CANCELLED / ORDER_TIMEOUT. Entry tasks use passive limits
and allow longer waits (max total 180s, per stage 90s). Exit tasks use faster limits
and shorter waits (max total 60s, per stage 15s). Transition occurs on stage timeout
or total budget exhaustion. On market fallback, slippage is estimated; if above limit,
the task is deferred to the next cycle instead of forcing a market order.

Pricing and Retry
Entry pricing starts from decision entry_range or current price and applies a fixed
price_step ladder. Adjustments move toward current price within max_price_adjust
(120 USDT). For entry, limits do not cross the spread until the final retry. Exit
pricing uses best bid/ask for fast fills, then more aggressive limit adjustments
before market fallback. Partial fills reduce remaining size; only the unfilled
portion is retried.

Slippage Estimation
SlippageEstimator prefers order book depth to compute weighted average fill price.
If the book is missing, stale (>2s), or depth is insufficient, it falls back to
mid-price plus ATR*0.1 correction. Slippage caps are 0.15% for normal orders and
0.30% for stop-loss exits.

Tracking and Logging
ExecutionTracker maintains per-symbol tasks and refreshes order status via exchange
queries. Every state change logs state, reason, price, remaining size, slippage, and
elapsed time. Scheduler integrates the engine and routes all entry/exit actions
through it, including risk-triggered closes and local SL/TP triggers.
