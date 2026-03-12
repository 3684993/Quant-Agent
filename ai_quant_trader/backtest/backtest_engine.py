import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
from core.logger import logger
from indicators.indicator_engine import IndicatorEngine
from ai.feature_compressor import FeatureCompressor
from ai.decision_engine import DecisionEngine
from ai.llm_client import LLMClient
from agents.orderbook_agent import OrderBookAgent
from agents.liquidity_agent import LiquidityAgent
from agents.profit_optimizer import ProfitOptimizer
from backtest.trade_simulator import TradeSimulator


class BacktestEngine:
    def __init__(
        self,
        simulator: TradeSimulator = None,
        use_ai: bool = False,
        initial_capital: float = 10000.0
    ):
        self.simulator = simulator or TradeSimulator(initial_capital=initial_capital)
        self.use_ai = use_ai
        
        self.indicator_engine = IndicatorEngine()
        self.feature_compressor = FeatureCompressor()
        self.orderbook_agent = OrderBookAgent()
        self.liquidity_agent = LiquidityAgent()
        self.profit_optimizer = ProfitOptimizer()
        
        if use_ai:
            self.llm_client = LLMClient()
            self.decision_engine = DecisionEngine(self.llm_client)
        else:
            self.decision_engine = None
        
        self.results: List[Dict] = []
        
        logger.info(f"BacktestEngine initialized (use_ai={use_ai})")
    
    def run(
        self,
        df: pd.DataFrame,
        symbol: str = "BTCUSDT"
    ) -> Dict:
        try:
            logger.info(f"Running backtest on {len(df)} candles for {symbol}")
            
            self.simulator.reset()
            self.results = []
            
            lookback = 50
            
            for i in range(lookback, len(df)):
                current_candle = df.iloc[i]
                current_price = current_candle["close"]
                current_time = current_candle["timestamp"]
                
                historical_df = df.iloc[i-lookback:i+1].copy()
                
                indicators = self.indicator_engine.calculate_indicators(historical_df)
                
                market_summary = self.feature_compressor.compress(indicators)
                
                orderbook_result = self.orderbook_agent.analyze(
                    indicators, 
                    market_summary.get("market_summary", {})
                )
                
                liquidity_result = self.liquidity_agent.analyze(indicators, orderbook_result)
                
                profit_result = self.profit_optimizer.optimize(
                    indicators,
                    market_summary.get("market_summary", {}),
                    indicators.get("market_regime", {})
                )
                
                position_state = self.simulator.get_position_state()
                
                decision = self._generate_decision(
                    symbol=symbol,
                    current_price=current_price,
                    indicators=indicators,
                    market_summary=market_summary,
                    orderbook_result=orderbook_result,
                    liquidity_result=liquidity_result,
                    profit_result=profit_result,
                    position_state=position_state
                )
                
                self._execute_decision(decision, symbol, current_price, current_time)
                
                self.simulator.update_equity(current_price, current_time)
            
            final_equity = self.simulator.get_equity(df.iloc[-1]["close"])
            
            return {
                "symbol": symbol,
                "total_candles": len(df),
                "initial_capital": self.simulator.initial_capital,
                "final_equity": final_equity,
                "total_return": ((final_equity - self.simulator.initial_capital) / self.simulator.initial_capital) * 100,
                "trades": self.simulator.get_trade_history(),
                "equity_curve": self.simulator.get_equity_curve(),
                "max_drawdown": self.simulator.max_drawdown * 100
            }
            
        except Exception as e:
            logger.error(f"Backtest run error: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _generate_decision(
        self,
        symbol: str,
        current_price: float,
        indicators: Dict,
        market_summary: Dict,
        orderbook_result: Dict,
        liquidity_result: Dict,
        profit_result: Dict,
        position_state: Dict
    ) -> Dict:
        try:
            if self.use_ai and self.decision_engine:
                context = {
                    "symbol": symbol,
                    "price": current_price,
                    "indicators": indicators,
                    "momentum": indicators.get("momentum", {}),
                    "market_regime": indicators.get("market_regime", {}),
                    "market_summary": market_summary.get("market_summary", {}),
                    "orderbook": orderbook_result,
                    "liquidity": liquidity_result,
                    "profit_optimizer": profit_result,
                    "position": position_state
                }
                
                return self.decision_engine.generate_trade_decision(context)
            else:
                return self._generate_rule_based_decision(
                    indicators, market_summary, position_state, current_price, profit_result
                )
                
        except Exception as e:
            logger.error(f"Generate decision error: {e}")
            return {"action": "hold"}
    
    def _generate_rule_based_decision(
        self,
        indicators: Dict,
        market_summary: Dict,
        position_state: Dict,
        current_price: float,
        profit_result: Dict
    ) -> Dict:
        try:
            has_position = position_state.get("has_position", False)
            trend = market_summary.get("market_summary", {}).get("trend", "neutral")
            momentum = market_summary.get("market_summary", {}).get("momentum", "neutral")
            rsi = indicators.get("rsi", 50)
            macd = indicators.get("macd", {}).get("hist", 0)
            
            if has_position:
                position_side = position_state.get("side", "long")
                entry_price = position_state.get("entry_price", current_price)
                
                if position_side == "long":
                    pnl_pct = (current_price - entry_price) / entry_price * 100
                    
                    if pnl_pct > 2.0 or rsi > 70 or (trend == "bearish" and momentum == "weakening"):
                        return {"action": "close_position"}
                else:
                    pnl_pct = (entry_price - current_price) / entry_price * 100
                    
                    if pnl_pct > 2.0 or rsi < 30 or (trend == "bullish" and momentum == "strengthening"):
                        return {"action": "close_position"}
                
                return {"action": "hold"}
            else:
                if trend == "bullish" and momentum == "strengthening" and rsi < 70 and macd > 0:
                    entry_range = profit_result.get("optimal_entry", [current_price, current_price])
                    return {
                        "action": "open_long",
                        "entry_range": entry_range,
                        "size": [0.01, 0.02],
                        "stop_loss": profit_result.get("stop_loss", current_price * 0.98),
                        "take_profit": profit_result.get("take_profit", current_price * 1.02)
                    }
                elif trend == "bearish" and momentum == "weakening" and rsi > 30 and macd < 0:
                    entry_range = profit_result.get("optimal_entry", [current_price, current_price])
                    return {
                        "action": "open_short",
                        "entry_range": entry_range,
                        "size": [0.01, 0.02],
                        "stop_loss": profit_result.get("stop_loss", current_price * 1.02),
                        "take_profit": profit_result.get("take_profit", current_price * 0.98)
                    }
                
                return {"action": "hold"}
                
        except Exception as e:
            logger.error(f"Rule-based decision error: {e}")
            return {"action": "hold"}
    
    def _execute_decision(
        self,
        decision: Dict,
        symbol: str,
        current_price: float,
        current_time: datetime
    ):
        try:
            action = decision.get("action", "hold")
            position_state = self.simulator.get_position_state()
            
            if action == "open_long" and not position_state.get("has_position"):
                entry_range = decision.get("entry_range", [current_price])
                price = entry_range[0] if isinstance(entry_range, list) else entry_range
                size = 0.01
                
                self.simulator.open_position(symbol, "long", size, price, current_time)
                
            elif action == "open_short" and not position_state.get("has_position"):
                entry_range = decision.get("entry_range", [current_price])
                price = entry_range[0] if isinstance(entry_range, list) else entry_range
                size = 0.01
                
                self.simulator.open_position(symbol, "short", size, price, current_time)
                
            elif action == "close_position" and position_state.get("has_position"):
                self.simulator.close_position(current_price, current_time)
                
        except Exception as e:
            logger.error(f"Execute decision error: {e}")
