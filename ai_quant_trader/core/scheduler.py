import time
import signal
import sys
from typing import Dict, List, Optional
from datetime import datetime
from core.logger import logger
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
from learning.trade_memory import TradeMemory
from learning.reward_engine import RewardEngine
from learning.strategy_optimizer import StrategyOptimizer
from core.trade_guard import TradeGuard
from config.settings import settings
from core.target_position_engine import TargetPositionEngine


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
        self.target_position_engine = TargetPositionEngine()
        
        self.trade_guard = TradeGuard(
            min_order_interval_seconds=settings.min_order_interval_seconds,
            trend_confirmation_count=settings.trend_confirmation_count
        )
        
        if order_executor:
            order_executor.trade_guard = self.trade_guard
        self.order_executor = order_executor
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"Scheduler initialized with {self.interval}s interval")
        logger.info(f"Monitoring symbols: {self.symbols}")
        logger.info(f"Timeframes: {self.timeframes}")
        logger.info(f"TradeGuard: interval={settings.min_order_interval_seconds}s, trend_confirm={settings.trend_confirmation_count}")
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def _execute_cycle(self) -> bool:
        self._cycle_count += 1
        cycle_start = datetime.now()
        
        # 使用新的格式化输出
        formatted_output.print_cycle_header(self._cycle_count, cycle_start)
        
        try:
            for symbol in self.symbols:
                primary_timeframe = self.timeframes[-1] if self.timeframes else "15m"
                
                df = self.market_data.get_klines(primary_timeframe)
                
                if df.empty:
                    formatted_output.print_warning(f"[{symbol}] 数据为空")
                    continue
                
                self.cache.update(symbol, primary_timeframe, df)
                
                latest = df.iloc[-1]
                current_price = latest['close']
                volume = latest['volume']
                
                indicators = self.indicator_engine.calculate_indicators(df)
                
                regime = indicators.get("market_regime", {})
                momentum = indicators.get("momentum", {})
                
                # 使用新的格式化输出
                trend = regime.get('state', 'neutral')
                formatted_output.print_market_status(symbol, current_price, volume, trend)
                
                # 使用新的格式化输出 - 技术指标
                formatted_output.print_indicators(symbol, indicators)
                
                market_summary = self.feature_compressor.compress(indicators)
                
                # 订单簿和流动性分析（保持原有日志，但简化显示）
                orderbook_result = self.orderbook_agent.analyze(indicators, market_summary.get("market_summary", {}))
                liquidity_result = self.liquidity_agent.analyze(indicators, orderbook_result)
                
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
                        
                    sl_tp_result = self.position_manager.check_local_sl_tp(symbol, current_price)
                    if sl_tp_result.get("triggered"):
                        formatted_output.print_warning(f"本地止盈止损触发: {sl_tp_result.get('trigger_type')}")
                        if self.order_executor:
                            close_result = self.order_executor.close_position(
                                symbol, 
                                position_state.get("side", "long"),
                                position_state.get("position_size", 0)
                            )
                            formatted_output.print_execution_result(symbol, close_result)
                            
                            if close_result.get("success"):
                                self._save_trade_to_memory(
                                    symbol, position_state, current_price, regime, market_summary
                                )
                                self.position_manager.update_position(
                                    symbol=symbol,
                                    position_size=0,
                                    entry_price=0
                                )
                                self.trade_guard.clear_position(symbol)
                        continue
                
                risk_result = self.risk_manager.check_risk(position_state)
                
                if risk_result.get("action") == "force_close":
                    formatted_output.print_warning(f"风险触发 - 强制平仓")
                    if self.order_executor:
                        close_result = self.order_executor.close_position(
                            symbol, 
                            position_state.get("side", "long"),
                            position_state.get("position_size", 0)
                        )
                        formatted_output.print_execution_result(symbol, close_result)
                        
                        if close_result.get("success"):
                            self._save_trade_to_memory(
                                symbol, position_state, current_price, regime, market_summary
                            )
                            self.position_manager.update_position(
                                symbol=symbol,
                                position_size=0,
                                entry_price=0
                            )
                            self.trade_guard.clear_position(symbol)
                    continue
                
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

                entry_risk = self.risk_manager.check_entry_risk(execution_decision, position_state)
                
                if entry_risk.get("status") == "approved" and self.order_executor:
                    # 使用独立的委托管理模块进行全面巡查
                    
                    # 1. 初始化委托管理模块（如果尚未初始化）
                    if not hasattr(self, 'order_manager') or self.order_manager is None:
                        from core.order_manager import OrderManager
                        # 检查market_analyzer是否存在，如果不存在则传入None
                        market_analyzer = getattr(self, 'market_analyzer', None)
                        self.order_manager = OrderManager(self.order_executor, market_analyzer)
                    
                    # 2. 全面巡查委托订单
                    inspection_result = self.order_manager.inspect_all_orders(symbol)
                    
                    if inspection_result.get("success"):
                        formatted_output.print_info(f"委托巡查完成: {symbol}")
                        
                        # 显示巡查摘要
                        total_orders = inspection_result.get("total_orders", 0)
                        recommendations = inspection_result.get("recommendations", [])
                        
                        formatted_output.print_info(f"活跃委托: {total_orders}个")
                        for rec in recommendations:
                            if "正常" not in rec:
                                formatted_output.print_warning(f"巡查建议: {rec}")
                    
                    # 3. 自动清理不合理的委托
                    cleanup_result = self.order_manager.auto_cleanup_orders(symbol)
                    
                    if cleanup_result.get("success"):
                        cleanup_actions = cleanup_result.get("cleanup_actions", [])
                        for action in cleanup_actions:
                            formatted_output.print_warning(f"自动清理: {action}")
                    
                    # 4. 委托前最终检查
                    existing_orders_after_cleanup = self.order_executor.get_existing_orders(symbol)
                    if len(existing_orders_after_cleanup) >= 4:
                        formatted_output.print_warning(f"委托数量已达上限: {len(existing_orders_after_cleanup)}/4，跳过新委托")
                        exec_result = {
                            "success": False,
                            "action": "hold",
                            "message": f"委托数量已达上限: {len(existing_orders_after_cleanup)}/4"
                        }
                    else:
                        # 5. 使用智能执行决策（只有在检查通过后才执行）
                        exec_result = self.order_executor.execute_intelligent_decision(
                            execution_decision, symbol, current_price, position_state
                        )
                    
                    # 使用新的格式化输出 - 执行结果
                    formatted_output.print_execution_result(symbol, exec_result)
                    
                    if exec_result.get("success"):
                        action = decision.get("action", "hold")
                        
                        if action in ["open_long", "open_short"]:
                            orders = exec_result.get("orders", [])
                            total_size = exec_result.get("total_size", 0)
                            
                            if orders:
                                # 计算加权平均价格
                                total_value = sum(o.get("price", 0) * o.get("size", 0) for o in orders)
                                avg_price = total_value / total_size if total_size > 0 else current_price
                                side = "long" if action == "open_long" else "short"
                                
                                self.position_manager.update_position(
                                    symbol=symbol,
                                    position_size=total_size,
                                    entry_price=avg_price,
                                    side=side,
                                    expected_hold_minutes=decision.get("expected_hold_minutes", 60),
                                    stop_loss=execution_decision.get("stop_loss", 0),
                                    take_profit=execution_decision.get("take_profit", 0)
                                )
                                
                                # 显示止盈止损信息
                                if self.order_executor:
                                    sl_tp_result = self.order_executor.set_stop_loss_take_profit(
                                        symbol, side, execution_decision.get("stop_loss", 0), 
                                        execution_decision.get("take_profit", 0), total_size
                                    )
                                    formatted_output.print_sl_tp_info(symbol, sl_tp_result)
                        
                        elif action == "add_position":
                            orders = exec_result.get("orders", [])
                            added_size = exec_result.get("added_size", 0)
                            
                            if orders:
                                # 计算加权平均价格
                                total_value = sum(o.get("price", 0) * o.get("size", 0) for o in orders)
                                avg_price = total_value / added_size if added_size > 0 else current_price
                                
                                self.position_manager.add_to_position(
                                    symbol=symbol,
                                    add_size=added_size,
                                    add_price=avg_price
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
                        
                        elif action == "reverse_position":
                            self._last_position_state = position_state.copy()
                            
                            self._save_trade_to_memory(
                                symbol, self._last_position_state, current_price, regime, market_summary
                            )
            
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
        
        self._running = True
        
        while self._running:
            try:
                self._execute_cycle()
                
                if self._running:
                    self._run_intra_cycle_tasks(wait_seconds=self.interval)
                    
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                time.sleep(5)
    
    def _run_intra_cycle_tasks(self, wait_seconds: int) -> None:
        """主周期内执行轻量任务，避免整段休眠。"""
        check_every = max(1, int(getattr(settings, "intra_cycle_check_seconds", 5)))
        elapsed = 0
        logger.info(f"Main cycle={self.interval}s, intra-cycle checks every {check_every}s")

        while self._running and elapsed < max(0, int(wait_seconds)):
            try:
                for symbol in self.symbols:
                    # 1) 订单巡检与委托管理
                    if hasattr(self, 'order_manager') and self.order_manager and self.order_executor:
                        self.order_manager.inspect_all_orders(symbol)
                        self.order_manager.auto_cleanup_orders(symbol)

                    # 2) 持仓管理
                    if self.position_manager and self.binance_client:
                        self.position_manager.sync_position_from_exchange(self.binance_client, symbol)
                        pos = self.position_manager.get_position_state()

                        # 3) 风险检查
                        if pos.get('has_position') and self.risk_manager:
                            risk = self.risk_manager.check_risk(pos)
                            if risk.get('action') == 'force_close' and self.order_executor:
                                self.order_executor.close_position(symbol, pos.get('side', 'long'), pos.get('position_size', 0))
                                self.position_manager.update_position(symbol=symbol, position_size=0, entry_price=0)
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
