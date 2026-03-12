import time
import signal
import sys
from typing import Dict, List, Optional
from datetime import datetime
from core.logger import logger, cleanup_old_logs
from core.formatted_output import formatted_output
from data.market_data import MarketDataService
from data.kline_cache import KlineCache
from indicators.indicator_engine import IndicatorEngine
from ai.feature_compressor import FeatureCompressor
from ai.llm_client import LLMClient
from ai.decision_engine import DecisionEngine
from agents.orderbook_agent import OrderBookAgent
from agents.liquidity_agent import LiquidityAgent
from agents.profit_optimizer import ProfitOptimizer
from agents.advanced_take_profit import advanced_take_profit
from agents.intelligent_close_decision import intelligent_close_decision
from core.position_manager import PositionManager
from execution.risk_manager import RiskManager
from execution.order_executor import OrderExecutor
from execution.execution_engine import ExecutionEngine
from learning.trade_memory import TradeMemory
from learning.reward_engine import RewardEngine
from learning.strategy_optimizer import StrategyOptimizer
from core.trade_guard import TradeGuard
from config.settings import settings
from core.target_position_engine import TargetPositionEngine
from core.risk_engine import RiskEngine
from core.entry_timing_filter import EntryTimingFilter
from core.order_adjuster import OrderAdjuster


class Scheduler:
    def __init__(
        self,
        market_data_service: MarketDataService,
        kline_cache: KlineCache,
        binance_client,
        indicator_engine: IndicatorEngine = None,
        feature_compressor: FeatureCompressor = None,
        llm_client: LLMClient = None,
        decision_engine: DecisionEngine = None,
        orderbook_agent: OrderBookAgent = None,
        liquidity_agent: LiquidityAgent = None,
        profit_optimizer: ProfitOptimizer = None,
        position_manager: PositionManager = None,
        risk_manager: RiskManager = None,
        order_executor: OrderExecutor = None,
        trade_memory: TradeMemory = None,
        reward_engine: RewardEngine = None,
        strategy_optimizer: StrategyOptimizer = None,
        interval: int = 60,
        symbols: List[str] = None,
        timeframes: List[str] = None
    ):
        self.market_data = market_data_service
        self.cache = kline_cache
        self.binance_client = binance_client
        self.indicator_engine = indicator_engine or IndicatorEngine()
        self.feature_compressor = feature_compressor or FeatureCompressor()
        self.llm_client = llm_client or LLMClient()
        self.decision_engine = decision_engine or DecisionEngine(self.llm_client)
        self.orderbook_agent = orderbook_agent or OrderBookAgent()
        self.liquidity_agent = liquidity_agent or LiquidityAgent()
        self.profit_optimizer = profit_optimizer or ProfitOptimizer()
        self.position_manager = position_manager or PositionManager()
        self.risk_manager = risk_manager or RiskManager()
        self.trade_memory = trade_memory or TradeMemory()
        self.reward_engine = reward_engine or RewardEngine()
        self.strategy_optimizer = strategy_optimizer or StrategyOptimizer()
        self.interval = interval
        self.symbols = symbols or [settings.symbol]
        self.timeframes = timeframes or settings.timeframes
        self._running = False
        self._cycle_count = 0
        
        self._last_position_state = None
        self._last_fill_time = datetime.now()
        self._last_log_cleanup = None
        self._order_check_state: Dict[str, Dict] = {}
        self._last_indicators: Dict[str, Dict] = {}
        self._last_market_summary: Dict[str, Dict] = {}
        self._last_trend_snapshot: Dict[str, Dict] = {}
        self._order_check_interval_active = 10
        self._order_check_interval_idle = 600
        self.target_position_engine = TargetPositionEngine()
        
        self.risk_engine = RiskEngine(self.position_manager, self.risk_manager)
        self.entry_timing_filter = EntryTimingFilter()
        self.order_manager = None
        self.order_adjuster = None

        self.trade_guard = TradeGuard(
            min_order_interval_seconds=settings.min_order_interval_seconds,
            trend_confirmation_count=settings.trend_confirmation_count
        )
        
        if order_executor:
            order_executor.trade_guard = self.trade_guard
        self.order_executor = order_executor
        self.execution_engine = None
        if self.order_executor:
            self.execution_engine = ExecutionEngine(
                order_executor=self.order_executor,
                binance_client=self.binance_client,
                position_manager=self.position_manager,
                cycle_interval_seconds=self.interval,
            )
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"Scheduler initialized with {self.interval}s interval")
        logger.info(f"Monitoring symbols: {self.symbols}")
        logger.info(f"Timeframes: {self.timeframes}")
        logger.info(f"TradeGuard: interval={settings.min_order_interval_seconds}s, trend_confirm={settings.trend_confirmation_count}")

        # Startup log cleanup (keep only last 2 hours)
        deleted = cleanup_old_logs(max_age_seconds=7200)
        self._last_log_cleanup = datetime.now()
        if deleted:
            logger.info("[LOG_CLEANUP] deleted=%d", deleted)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def _execute_cycle(self) -> bool:
        self._cycle_count += 1
        cycle_start = datetime.now()

        if not self._last_log_cleanup or (datetime.now() - self._last_log_cleanup).total_seconds() >= 600:
            deleted = cleanup_old_logs(max_age_seconds=7200)
            if deleted:
                logger.info("[LOG_CLEANUP] deleted=%d", deleted)
            self._last_log_cleanup = datetime.now()
        
        # 使用新的格式化输出
        formatted_output.print_cycle_header(self._cycle_count, cycle_start)
        
        try:
            for symbol in self.symbols:
                symbol_cycle_start = time.perf_counter()
                primary_timeframe = self.timeframes[-1] if self.timeframes else "15m"
                
                stage_start = time.perf_counter()
                df = self.market_data.get_klines(primary_timeframe)
                
                if df.empty:
                    formatted_output.print_warning(f"[{symbol}] 数据为空")
                    continue
                
                self.cache.update(symbol, primary_timeframe, df)
                
                latest = df.iloc[-1]
                current_price = latest['close']
                volume = latest['volume']
                self._log_stage(symbol, "market_data", stage_start)
                
                stage_start = time.perf_counter()
                indicators = self.indicator_engine.calculate_indicators(df)
                
                regime = indicators.get("market_regime", {})
                momentum = indicators.get("momentum", {})
                
                # 使用新的格式化输出
                trend = regime.get('state', 'neutral')
                formatted_output.print_market_status(symbol, current_price, volume, trend)
                
                # 使用新的格式化输出 - 技术指标
                formatted_output.print_indicators(symbol, indicators)
                logger.info(
                    "[ANALYSIS] symbol=%s trend=%s rsi=%.1f macd=%.2f atr=%.2f",
                    symbol,
                    trend,
                    float(indicators.get("rsi", 0) or 0),
                    float(indicators.get("macd", {}).get("macd", 0) or 0),
                    float(indicators.get("atr", 0) or 0),
                )
                
                market_summary = self.feature_compressor.compress(indicators)
                self._last_indicators[symbol] = indicators
                self._last_market_summary[symbol] = market_summary.get("market_summary", {}) if isinstance(market_summary, dict) else {}
                
                # 订单簿和流动性分析（保持原有日志，但简化显示）
                orderbook_result = self.orderbook_agent.analyze(indicators, market_summary.get("market_summary", {}))
                liquidity_result = self.liquidity_agent.analyze(indicators, orderbook_result)
                self._log_stage(symbol, "analysis", stage_start)
                
                stage_start = time.perf_counter()
                
                # 先同步持仓状态并计算盈亏
                self.position_manager.sync_position_from_exchange(self.binance_client, symbol)
                self.position_manager.calculate_pnl(current_price)
                self.position_manager.calculate_hold_minutes()
                position_state = self.position_manager.get_position_state()
                
                # 使用新的格式化输出 - 持仓状态
                formatted_output.print_position_status(symbol, position_state)
                
                # 传递持仓信息给profit_optimizer进行高级止盈优化
                profit_result = self.profit_optimizer.optimize(
                    indicators, 
                    market_summary.get("market_summary", {}), 
                    regime,
                    position_state  # 传递持仓信息
                )
                self._log_stage(symbol, "position_sync", stage_start)
                
                stage_start = time.perf_counter()
                if position_state.get("has_position"):
                    # 趋势变化检测
                    trend_change = self._detect_trend_change(symbol, indicators, market_summary)
                    
                    # 智能平仓决策分析
                    close_analysis = intelligent_close_decision.analyze_trend_strength(indicators, market_summary)
                    
                    formatted_output.print_info(
                        f"趋势分析: 强度{close_analysis.get('strength_level', '未知')}, "
                        f"可靠性{close_analysis.get('reliability', '低')}, "
                        f"趋势变化{'是' if trend_change else '否'}"
                    )
                    
                    # 动态止损调整 - 基于15分钟趋势
                    try:
                        # 获取历史价格数据用于趋势分析
                        historical_prices = df['close'].tolist()
                        atr = indicators.get('atr', current_price * 0.01)  # 默认ATR为价格的1%
                        
                        # 执行动态止损调整
                        stop_loss_adjustment = self.position_manager.dynamic_adjust_stop_loss(
                            symbol, historical_prices, atr
                        )
                        
                        if stop_loss_adjustment.get("adjusted", False):
                            formatted_output.print_warning(
                                f"动态止损调整: {stop_loss_adjustment.get('old_stop_loss', 0):.2f} "
                                f"-> {stop_loss_adjustment.get('new_stop_loss', 0):.2f}"
                            )
                    except Exception as e:
                        formatted_output.print_warning(f"动态止损调整失败: {e}")

                    # 新增：动态追踪止损（分级锁盈）
                    trailing_result = self.position_manager.dynamic_trailing_stop(symbol, current_price)
                    if trailing_result.get("adjusted", False):
                        formatted_output.print_warning(
                            f"动态追踪止损: {trailing_result.get('old_stop_loss', 0):.2f} "
                            f"-> {trailing_result.get('new_stop_loss', 0):.2f} "
                            f"(profit={trailing_result.get('profit_pct', 0):.2f}%)"
                        )
                    
                    # 检查是否应该设置收益委托
                    hold_minutes = position_state.get("hold_minutes", 0)
                    pnl_pct = position_state.get("current_pnl_pct", 0)
                    
                    if advanced_take_profit.should_set_profit_trailing(hold_minutes, pnl_pct):
                        formatted_output.print_info(
                            f"持仓{hold_minutes}分钟，盈利{pnl_pct:.2f}%，建议设置收益委托"
                        )
                        # 这里可以添加具体的收益委托逻辑
                        # 例如：自动调整止损到盈亏平衡点上方
                        
                    trend_dir = market_summary.get("market_summary", {}).get("trend", "")
                    if not trend_dir:
                        trend_dir = indicators.get("market_regime", {}).get("state", "")
                    sl_tp_result = self.position_manager.check_local_sl_tp(
                        symbol,
                        current_price,
                        trend_direction=trend_dir,
                        trend_strength=float(indicators.get("market_regime", {}).get("trend_strength", 0) or 0),
                    )
                    if sl_tp_result.get("triggered"):
                        formatted_output.print_warning(f"本地止盈止损触发: {sl_tp_result.get('trigger_type')}")
                        if self.execution_engine:
                            decision = {
                                "action": "close_position",
                                "exit_reason": sl_tp_result.get("trigger_type", ""),
                                "is_stop_loss": str(sl_tp_result.get("trigger_type", "")).upper() == "STOP_LOSS",
                            }
                            close_result = self.execution_engine.execute(
                                decision,
                                symbol,
                                current_price,
                                position_state,
                                indicators,
                            )
                            formatted_output.print_execution_result(symbol, close_result)

                            if close_result.get("completed"):
                                if float(close_result.get("filled_size", 0) or 0) > 0:
                                    self._last_fill_time = datetime.now()
                                self._save_trade_to_memory(
                                    symbol, position_state, current_price, regime, market_summary
                                )
                                self.position_manager.update_position(
                                    symbol=symbol,
                                    position_size=0,
                                    entry_price=0
                                )
                                self.trade_guard.clear_position(symbol)
                        self._log_stage(symbol, "risk_exit", stage_start)
                        self._log_stage(symbol, "cycle_total", symbol_cycle_start)
                        continue
                
                risk_result = self.risk_engine.evaluate(
                    symbol=symbol,
                    position_state=position_state,
                    current_price=current_price,
                    trend_change=trend_change if position_state.get("has_position") else False,
                    market_summary=market_summary.get("market_summary", {}),
                    indicators=indicators,
                )

                if risk_result.get("action") == "force_close":
                    formatted_output.print_warning(f"风险触发 - 强制平仓({risk_result.get('reason', 'UNKNOWN')})")
                    if self.execution_engine:
                        decision = {
                            "action": "close_position",
                            "exit_reason": str(risk_result.get("reason", "RISK_FORCE")),
                            "is_stop_loss": False,
                        }
                        close_result = self.execution_engine.execute(
                            decision,
                            symbol,
                            current_price,
                            position_state,
                            indicators,
                        )
                        formatted_output.print_execution_result(symbol, close_result)

                        if close_result.get("completed"):
                            if float(close_result.get("filled_size", 0) or 0) > 0:
                                self._last_fill_time = datetime.now()
                            self._save_trade_to_memory(
                                symbol, position_state, current_price, regime, market_summary
                            )
                            self.position_manager.update_position(
                                symbol=symbol,
                                position_size=0,
                                entry_price=0
                            )
                            self.trade_guard.clear_position(symbol)
                    self._log_stage(symbol, "risk_exit", stage_start)
                    self._log_stage(symbol, "cycle_total", symbol_cycle_start)
                    continue
                
                self._log_stage(symbol, "risk_exit", stage_start)
                stage_start = time.perf_counter()
                context = {
                    "symbol": symbol,
                    "price": current_price,
                    "indicators": indicators,
                    "momentum": momentum,
                    "market_regime": regime,
                    "market_summary": market_summary.get("market_summary", {}),
                    "orderbook": orderbook_result,
                    "liquidity": liquidity_result,
                    "profit_optimizer": profit_result,
                    "position": position_state
                }
                
                ai_decision = self.decision_engine.generate_trade_decision(context)

                execution_decision = self.target_position_engine.update_target_position(
                    symbol=symbol,
                    ai_decision=ai_decision,
                    position_state=position_state,
                    market_summary=market_summary.get("market_summary", {}),
                )

                # 入场时机过滤（仅影响开仓/加仓执行，不改变AI逻辑）
                action_for_timing = str(execution_decision.get("action", "hold"))
                if action_for_timing in ["open_long", "open_short", "add_position"]:
                    trend_for_timing = "long" if action_for_timing in ["open_long", "add_position"] else "short"
                    trend_strength = float(indicators.get("market_regime", {}).get("trend_strength", 0) or 0)
                    ai_confidence = float(execution_decision.get("confidence", 0) or 0)
                    timing = self.entry_timing_filter.evaluate(
                        symbol=symbol,
                        trend=trend_for_timing,
                        current_price=current_price,
                        indicators_1m=indicators,
                        trend_strength=trend_strength,
                        ai_confidence=ai_confidence,
                        last_fill_time=self._last_fill_time,
                    )
                    if not timing.get("allow_entry", True):
                        execution_decision["action"] = "hold"
                        execution_decision["timing_state"] = timing.get("state")
                        execution_decision["timing_reason"] = timing.get("reason")
                        formatted_output.print_warning(
                            "Entry timing blocked: mode=%s reason=%s bb_pos=%.3f rsi=%.2f trend_strength=%.2f ai_conf=%.2f"
                            % (
                                timing.get("entry_mode"),
                                timing.get("reason"),
                                float(timing.get("bb_position", 0) or 0),
                                float(timing.get("rsi", 0) or 0),
                                float(timing.get("trend_strength", 0) or 0),
                                float(timing.get("ai_confidence", 0) or 0),
                            )
                        )

                # 使用新的格式化输出 - AI决策（显示目标仓位）
                formatted_output.print_ai_decision(symbol, execution_decision)

                position_state_for_guard = dict(position_state)
                position_state_for_guard["trend_strength"] = close_analysis.get("strength_level", "normal") if position_state.get("has_position") else "normal"

                validated = self.trade_guard.validate_decision(
                    execution_decision, symbol, position_state_for_guard, self.binance_client
                )

                if validated.get("modified"):
                    formatted_output.print_warning(
                        f"决策被TradeGuard修改: {execution_decision.get('action')} -> {validated.get('action')} ({validated.get('reason', '未知')})"
                    )
                    execution_decision["action"] = validated["action"]

                logger.info(
                    "[AI_DECISION] symbol=%s action=%s target=%.4f confidence=%.2f",
                    symbol,
                    execution_decision.get("action", "hold"),
                    float(execution_decision.get("target_size", 0) or 0),
                    float(execution_decision.get("confidence", 0) or 0),
                )
                self._log_stage(symbol, "decision", stage_start)

                stage_start = time.perf_counter()
                action = str(execution_decision.get("action", "hold"))
                target_size = self._resolve_decision_size(execution_decision, position_state)
                if action in ["close_position", "reverse_position"] and target_size <= 0 and position_state.get("has_position"):
                    target_size = float(position_state.get("position_size", 0) or 0)
                    execution_decision["target_size"] = target_size
                if action == "hold":
                    logger.info(
                        "[EXECUTION] symbol=%s action=hold status=NOOP reason=decision_hold target=%.6f",
                        symbol,
                        target_size,
                    )
                    formatted_output.print_execution_result(symbol, {"action": "hold", "success": True})
                    self._log_stage(symbol, "execution", stage_start)
                    self._log_stage(symbol, "cycle_total", symbol_cycle_start)
                    continue
                if action in ["open_long", "open_short", "add_position", "close_position", "reverse_position"] and target_size <= 0:
                    logger.info(
                        "[EXECUTION] symbol=%s action=%s status=SKIP reason=target_size_zero target=%.6f",
                        symbol,
                        action,
                        target_size,
                    )
                    formatted_output.print_execution_result(symbol, {"action": "hold", "success": True})
                    execution_decision["action"] = "hold"
                    self._log_stage(symbol, "execution", stage_start)
                    self._log_stage(symbol, "cycle_total", symbol_cycle_start)
                    continue

                entry_risk = self.risk_manager.check_entry_risk(execution_decision, position_state)
                
                if entry_risk.get("status") == "approved" and self.execution_engine:
                    # 仅在无执行任务时做委托清理，避免干扰执行引擎
                    if not self.execution_engine.has_active_task(symbol):
                        if not hasattr(self, 'order_manager') or self.order_manager is None:
                            from core.order_manager import OrderManager
                            market_analyzer = getattr(self, 'market_analyzer', None)
                            self.order_manager = OrderManager(self.order_executor, market_analyzer)
                            self.order_adjuster = OrderAdjuster(self.order_manager, self.order_executor)
                        try:
                            if self._should_check_orders(symbol):
                                inspection = self.order_manager.inspect_all_orders(symbol)
                                self.order_manager.auto_cleanup_orders(symbol, report=inspection)
                                self._record_order_snapshot(symbol, inspection.get("total_orders", 0))
                        except Exception as e:
                            formatted_output.print_warning(f"委托巡查异常: {e}")

                    exec_result = self.execution_engine.execute(
                        execution_decision, symbol, current_price, position_state, indicators
                    )

                    formatted_output.print_execution_result(symbol, exec_result)
                    if not exec_result or not exec_result.get("success", True):
                        logger.info(
                            "[EXECUTION] symbol=%s action=%s status=ERROR reason=%s",
                            symbol,
                            execution_decision.get("action", "hold"),
                            str(exec_result.get("error", "unknown") if isinstance(exec_result, dict) else "unknown"),
                        )
                else:
                    logger.info(
                        "[EXECUTION] symbol=%s action=%s status=SKIP reason=entry_risk_%s",
                        symbol,
                        action,
                        str(entry_risk.get("reason", "unknown")),
                    )
                    formatted_output.print_execution_result(symbol, {"action": "hold", "success": True})

                    if exec_result.get("completed"):
                        if float(exec_result.get("filled_size", 0) or 0) > 0:
                            self._last_fill_time = datetime.now()
                        action = execution_decision.get("action", "hold")

                        if action in ["open_long", "open_short"]:
                            total_size = float(exec_result.get("filled_size", 0) or 0)
                            avg_price = float(exec_result.get("avg_price", 0) or current_price)
                            side = "long" if action == "open_long" else "short"

                            if total_size > 0:
                                self.position_manager.update_position(
                                    symbol=symbol,
                                    position_size=total_size,
                                    entry_price=avg_price,
                                    side=side,
                                    expected_hold_minutes=execution_decision.get("expected_hold_minutes", 60),
                                    stop_loss=execution_decision.get("stop_loss", 0),
                                    take_profit=execution_decision.get("take_profit", 0)
                                )

                                if self.trade_guard:
                                    self.trade_guard.record_position_entry(
                                        symbol=symbol,
                                        entry_price=avg_price,
                                        position_size=total_size,
                                        side=side,
                                        expected_hold_minutes=execution_decision.get("expected_hold_minutes", 60),
                                        stop_loss=execution_decision.get("stop_loss", 0),
                                        take_profit=execution_decision.get("take_profit", 0)
                                    )

                                if self.order_executor:
                                    sl_tp_result = self.order_executor.set_stop_loss_take_profit(
                                        symbol, side, execution_decision.get("stop_loss", 0),
                                        execution_decision.get("take_profit", 0), total_size
                                    )
                                    formatted_output.print_sl_tp_info(symbol, sl_tp_result)
                                logger.info(
                                    "[POSITION] symbol=%s action=%s size=%.4f price=%.2f",
                                    symbol,
                                    action,
                                    total_size,
                                    avg_price,
                                )

                        elif action == "add_position":
                            added_size = float(exec_result.get("filled_size", 0) or 0)
                            avg_price = float(exec_result.get("avg_price", 0) or current_price)
                            if added_size > 0:
                                self.position_manager.add_to_position(
                                    symbol=symbol,
                                    add_size=added_size,
                                    add_price=avg_price
                                )
                                logger.info(
                                    "[POSITION] symbol=%s action=add_position size=%.4f price=%.2f",
                                    symbol,
                                    added_size,
                                    avg_price,
                                )
                                if self.trade_guard:
                                    self.trade_guard.update_position_metadata(
                                        symbol=symbol,
                                        position_size=position_state.get("position_size", 0) + added_size,
                                        stop_loss=execution_decision.get("stop_loss", 0),
                                        take_profit=execution_decision.get("take_profit", 0)
                                    )

                        elif action == "close_position":
                            self._last_position_state = position_state.copy()
                            self._save_trade_to_memory(
                                symbol, self._last_position_state, current_price, regime, market_summary
                            )
                            self.position_manager.update_position(
                                symbol=symbol,
                                position_size=0,
                                entry_price=0
                            )
                            self.trade_guard.clear_position(symbol)
                            logger.info("[POSITION] symbol=%s action=close_position size=0 price=%.2f", symbol, current_price)

                        elif action == "reverse_position":
                            self._last_position_state = position_state.copy()
                            self._save_trade_to_memory(
                                symbol, self._last_position_state, current_price, regime, market_summary
                            )
                self._log_stage(symbol, "execution", stage_start)
                self._log_stage(symbol, "cycle_total", symbol_cycle_start)
            
            # 使用新的格式化输出 - 学习统计
            stats = self.strategy_optimizer.update(self.trade_memory.trades)
            formatted_output.print_learning_stats(symbol, stats)
            
            cycle_end = datetime.now()
            duration = (cycle_end - cycle_start).total_seconds()
            
            # 使用新的格式化输出 - 周期结束
            formatted_output.print_cycle_footer(self._cycle_count, duration)
            
            return True
            
        except Exception as e:
            formatted_output.print_error(f"周期 #{self._cycle_count} 失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _save_trade_to_memory(
        self, 
        symbol: str, 
        position_state: dict, 
        exit_price: float,
        regime: dict,
        market_summary: dict
    ):
        try:
            if not position_state or not position_state.get("has_position"):
                return
            
            entry_price = position_state.get("entry_price", 0)
            pnl_pct = position_state.get("current_pnl_pct", 0)
            hold_minutes = position_state.get("hold_minutes", 0)
            side = position_state.get("side", "long")
            
            self.trade_memory.save_trade(
                symbol=symbol,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl_pct=pnl_pct,
                hold_minutes=hold_minutes,
                market_regime=regime.get("state", "unknown"),
                trend=market_summary.get("trend", "neutral"),
                momentum=market_summary.get("momentum", "neutral"),
                volatility=market_summary.get("volatility", "low"),
                side=side
            )
            
            reward = self.reward_engine.calculate({
                "pnl_pct": pnl_pct,
                "drawdown_pct": position_state.get("drawdown_pct", 0),
                "hold_minutes": hold_minutes
            })
            logger.info(self.reward_engine.format_log(reward, symbol))
            
        except Exception as e:
            logger.error(f"Save trade to memory error: {e}")
    
    def start(self) -> None:
        logger.info("="*60)
        logger.info("AI Quant Trader System Starting...")
        logger.info(f"Trading Environment: {settings.trading_env}")
        logger.info(f"TradeGuard: min_interval={settings.min_order_interval_seconds}s")
        logger.info("="*60)

        try:
            if self.trade_memory:
                self.trade_memory.clear_history()
                logger.info("[LOG_CLEANUP] trade_memory_reset=1")
        except Exception as e:
            logger.error(f"[SYSTEM_ERROR] trade_memory_reset_failed: {e}")
        
        self._running = True
        
        while self._running:
            try:
                cycle_started = time.perf_counter()
                self._execute_cycle()
                
                if self._running:
                    elapsed = time.perf_counter() - cycle_started
                    wait_seconds = max(0, self.interval - elapsed)
                    self._run_intra_cycle_tasks(wait_seconds=wait_seconds)
                    
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(5)
    
    def _run_intra_cycle_tasks(self, wait_seconds: int) -> None:
        """主周期内执行轻量任务，避免整段休眠。"""
        check_every = max(1, int(getattr(settings, "intra_cycle_check_seconds", 5)))
        elapsed = 0
        logger.info("[STAGE] symbol=ALL stage=intra_cycle window=%ds check=%ds", int(wait_seconds), int(check_every))

        while self._running and elapsed < max(0, int(wait_seconds)):
            try:
                for symbol in self.symbols:
                    # 1) 订单巡检与委托管理
                    if (not self.execution_engine or not self.execution_engine.has_active_task(symbol)) and hasattr(self, 'order_manager') and self.order_manager and self.order_executor:
                        if self._should_check_orders(symbol):
                            inspection = self.order_manager.inspect_all_orders(symbol)
                            self.order_manager.auto_cleanup_orders(symbol, report=inspection)
                            self._record_order_snapshot(symbol, inspection.get("total_orders", 0))
                            if self.order_adjuster:
                                market_summary = {}
                                try:
                                    market_summary = self.market_data.get_market_summary(symbol)
                                except Exception:
                                    market_summary = {}
                                summary = market_summary.get("market_summary", {}) if isinstance(market_summary, dict) else {}
                                self.order_adjuster.adjust_orders(
                                    symbol=symbol,
                                    trend_direction=str(summary.get("trend", "neutral")),
                                    trend_strength=float(summary.get("trend_strength", 0) or 0),
                                    pullback_detected=not inspection.get("gap_ok", True),
                                    trend_changed=bool(inspection.get("trend_changed", False)),
                                )

                    # 2) 持仓管理
                    if self.position_manager and self.binance_client:
                        self.position_manager.sync_position_from_exchange(self.binance_client, symbol)
                        pos = self.position_manager.get_position_state()
                        trend_snapshot = self._get_trend_snapshot(symbol)
                        if trend_snapshot:
                            prev_snapshot = self._last_trend_snapshot.get(symbol)
                            trend_changed = prev_snapshot is None or prev_snapshot.get("trend") != trend_snapshot.get("trend")
                            strength_changed = prev_snapshot is None or abs(float(prev_snapshot.get("strength", 0) or 0) - float(trend_snapshot.get("strength", 0) or 0)) >= 0.1
                            if trend_changed or strength_changed:
                                logger.info(
                                    "[ANALYSIS] symbol=%s trend=%s strength=%.2f phase=intra_cycle",
                                    symbol,
                                    trend_snapshot.get("trend"),
                                    float(trend_snapshot.get("strength", 0) or 0),
                                )
                            self._last_trend_snapshot[symbol] = trend_snapshot

                        # 3) 风险检查
                        if pos.get('has_position') and self.risk_engine:
                            risk = self.risk_engine.evaluate(
                                symbol=symbol,
                                position_state=pos,
                                current_price=float(pos.get('current_price', 0) or 0),
                                trend_change=False,
                                market_summary={},
                                indicators={},
                            )
                            if risk.get('action') == 'force_close' and self.execution_engine:
                                decision = {
                                    "action": "close_position",
                                    "exit_reason": str(risk.get("reason", "RISK_FORCE")),
                                    "is_stop_loss": False,
                                }
                                exec_result = self.execution_engine.execute(
                                    decision, symbol, float(pos.get('current_price', 0) or 0), pos, {}
                                )
                                if exec_result and exec_result.get("completed"):
                                    self.position_manager.update_position(symbol=symbol, position_size=0, entry_price=0)

                        # 4) Execution engine heartbeat for active tasks
                        if self.execution_engine and self.execution_engine.has_active_task(symbol):
                            try:
                                tick_result = self.execution_engine.tick(symbol, float(pos.get('current_price', 0) or 0), {})
                                if tick_result and tick_result.get("completed") and tick_result.get("action") == "close_position":
                                    if float(tick_result.get("filled_size", 0) or 0) > 0:
                                        self._last_fill_time = datetime.now()
                                    self._save_trade_to_memory(symbol, pos, float(pos.get('current_price', 0) or 0), {}, {})
                                    self.position_manager.update_position(symbol=symbol, position_size=0, entry_price=0)
                                    self.trade_guard.clear_position(symbol)
                            except Exception as e:
                                logger.warning(f"Execution engine tick warning: {e}")
            except Exception as e:
                logger.warning(f"Intra-cycle task warning: {e}")

            sleep_s = min(check_every, max(0, int(wait_seconds) - elapsed))
            if sleep_s <= 0:
                break
            time.sleep(sleep_s)
            elapsed += sleep_s

    def stop(self) -> None:
        logger.info("Stopping scheduler...")
        self._running = False
    
    def run_once(self) -> bool:
        return self._execute_cycle()

    def _should_check_orders(self, symbol: str, force: bool = False) -> bool:
        state = self._order_check_state.setdefault(symbol, {"last_check": None, "open_count": 0})
        if force:
            return True
        now = datetime.now()
        has_task = self.execution_engine.has_active_task(symbol) if self.execution_engine else False
        open_count = int(state.get("open_count", 0) or 0)
        interval = self._order_check_interval_active if (has_task or open_count > 0) else self._order_check_interval_idle
        last_check = state.get("last_check")
        if not last_check:
            return True
        return (now - last_check).total_seconds() >= interval

    def _record_order_snapshot(self, symbol: str, count: int) -> None:
        state = self._order_check_state.setdefault(symbol, {"last_check": None, "open_count": 0})
        state["last_check"] = datetime.now()
        state["open_count"] = int(count or 0)

    def _log_stage(self, symbol: str, stage: str, started_at: float) -> None:
        try:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        except Exception:
            elapsed_ms = 0
        logger.info("[STAGE] symbol=%s stage=%s ms=%d", symbol, stage, elapsed_ms)

    def _resolve_decision_size(self, decision: Dict, position_state: Dict) -> float:
        size = decision.get("target_size")
        if size is None:
            size = decision.get("size", 0)
        if isinstance(size, list):
            size = size[0] if size else 0
        try:
            return float(size or 0.0)
        except Exception:
            return 0.0

    def _get_trend_snapshot(self, symbol: str) -> Dict:
        summary = {}
        if hasattr(self.market_data, "get_market_summary"):
            try:
                summary = self.market_data.get_market_summary(symbol)
            except Exception:
                summary = {}
        if isinstance(summary, dict):
            summary = summary.get("market_summary", summary)
        if not summary:
            summary = self._last_market_summary.get(symbol, {})
        trend = str(summary.get("trend") or summary.get("state") or "")
        strength = float(summary.get("trend_strength", 0) or 0)
        return {"trend": trend, "strength": strength}
    
    def _detect_trend_change(self, symbol: str, indicators: Dict, market_summary: Dict) -> bool:
        """检测趋势变化"""
        try:
            # 获取当前趋势
            current_trend = market_summary.get("trend", "neutral")
            current_momentum = market_summary.get("momentum", "neutral")
            
            # 获取技术指标
            rsi = indicators.get("rsi", 50)
            macd = indicators.get("macd", {}).get("macd", 0)
            
            # 检查趋势反转信号
            trend_change_signals = []
            
            # RSI超买超卖反转
            if current_trend == "bullish" and rsi > 70:
                trend_change_signals.append("RSI超买可能反转")
            elif current_trend == "bearish" and rsi < 30:
                trend_change_signals.append("RSI超卖可能反转")
            
            # MACD反转信号
            if current_trend == "bullish" and macd < 0:
                trend_change_signals.append("MACD转负")
            elif current_trend == "bearish" and macd > 0:
                trend_change_signals.append("MACD转正")
            
            # 动量减弱
            if current_momentum == "weakening":
                trend_change_signals.append("动量减弱")
            
            # 如果有多个趋势变化信号，认为趋势可能改变
            if len(trend_change_signals) >= 2:
                logger.info(f"趋势变化检测: {', '.join(trend_change_signals)}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"趋势变化检测失败: {e}")
            return False
