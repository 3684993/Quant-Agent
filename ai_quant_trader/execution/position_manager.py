from typing import Dict, Optional
from datetime import datetime
from core.logger import logger
from utils.position_time_utils import position_time_utils
from risk.dynamic_stop_loss import dynamic_stop_loss


class PositionManager:
    def __init__(self):
        self.position: Optional[Dict] = None
        self.position_history: list = []
        self._last_sync_time: datetime = None
        
        self.position_metadata: Dict = {}
        
        logger.info("PositionManager initialized")
    
    def sync_position_from_exchange(self, binance_client, symbol: str) -> Dict:
        try:
            logger.info(f"Syncing position from exchange for {symbol}")
            
            positions = binance_client.client.get_position_risk(symbol=symbol)
            
            for pos in positions:
                if pos.get("symbol") == symbol:
                    position_amt = float(pos.get("positionAmt", 0) or 0)
                    entry_price = float(pos.get("entryPrice", 0) or 0)
                    unrealized_profit = float(pos.get("unRealizedProfit", 0) or 0)
                    
                    if abs(position_amt) > 0.00001:
                        side = "long" if position_amt > 0 else "short"
                        position_size = abs(position_amt)
                        
                        existing_metadata = self.position_metadata.get(symbol, {})
                        
                        # 使用持仓时间工具获取正确的开仓时间
                        entry_time = existing_metadata.get("entry_time", datetime.now())
                        
                        # 如果持仓时间为0分钟，尝试从交易所获取真实开仓时间
                        if existing_metadata.get("hold_minutes", 0) == 0:
                            exchange_entry_time = position_time_utils.get_position_entry_time(symbol, binance_client)
                            if exchange_entry_time:
                                entry_time = exchange_entry_time
                                logger.info(f"Recovered entry time from exchange: {symbol} at {entry_time}")
                        
                        expected_hold = existing_metadata.get("expected_hold_minutes", 60)
                        
                        # 计算正确的持仓时间
                        hold_minutes = position_time_utils.calculate_hold_minutes_with_fallback(
                            symbol, binance_client, entry_time
                        )
                        
                        self.position = {
                            "symbol": symbol,
                            "side": side,
                            "position_size": position_size,
                            "entry_price": entry_price,
                            "entry_time": entry_time,
                            "expected_hold_minutes": expected_hold,
                            "current_price": entry_price,
                            "current_pnl": unrealized_profit,
                            "current_pnl_pct": (unrealized_profit / (entry_price * position_size)) * 100 if entry_price > 0 else 0,
                            "max_profit": 0.0,
                            "max_profit_pct": 0.0,
                            "drawdown": 0.0,
                            "drawdown_pct": 0.0,
                            "hold_minutes": hold_minutes,
                            "peak_price": entry_price,
                            "stop_loss": existing_metadata.get("stop_loss", 0),
                            "take_profit": existing_metadata.get("take_profit", 0)
                        }
                        
                        # 更新持仓时间持久化存储
                        position_time_utils.update_position_entry_time(symbol, entry_time)
                        
                        self._last_sync_time = datetime.now()
                        logger.info(f"Position synced: {side} {position_size} @ {entry_price}, hold={hold_minutes}min")
                        return {"status": "synced", "position": self.position}
                    else:
                        self.position = None
                        if symbol in self.position_metadata:
                            del self.position_metadata[symbol]
                        # 清除持仓时间记录
                        position_time_utils.clear_position_entry_time(symbol)
                        logger.info("No position found on exchange")
                        return {"status": "no_position"}
            
            self.position = None
            position_time_utils.clear_position_entry_time(symbol)
            return {"status": "no_position"}
            
        except Exception as e:
            logger.error(f"Sync position from exchange error: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    def update_position(
        self,
        symbol: str,
        position_size: float,
        entry_price: float,
        side: str = "long",
        timestamp: datetime = None,
        expected_hold_minutes: int = 60,
        stop_loss: float = 0,
        take_profit: float = 0
    ) -> Dict:
        try:
            position_size = float(position_size) if position_size is not None else 0.0
            entry_price = float(entry_price) if entry_price is not None else 0.0
            
            if position_size == 0:
                if self.position:
                    self.position["close_time"] = timestamp or datetime.now()
                    self.position_history.append(self.position.copy())
                    logger.info(f"Position closed: {self.position.get('symbol', 'N/A')}")
                self.position = None
                if symbol in self.position_metadata:
                    del self.position_metadata[symbol]
                return {"status": "closed"}
            
            entry_time = timestamp or datetime.now()
            
            # 更新持仓时间持久化存储
            position_time_utils.update_position_entry_time(symbol, entry_time)
            
            self.position_metadata[symbol] = {
                "entry_time": entry_time,
                "entry_price": entry_price,
                "position_size": position_size,
                "side": side,
                "expected_hold_minutes": expected_hold_minutes,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "scale_in_count": 1
            }
            
            self.position = {
                "symbol": symbol,
                "side": side,
                "position_size": position_size,
                "entry_price": entry_price,
                "entry_time": entry_time,
                "expected_hold_minutes": expected_hold_minutes,
                "current_price": entry_price,
                "current_pnl": 0.0,
                "current_pnl_pct": 0.0,
                "max_profit": 0.0,
                "max_profit_pct": 0.0,
                "drawdown": 0.0,
                "drawdown_pct": 0.0,
                "hold_minutes": 0,
                "peak_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit
            }
            
            logger.info(f"Position opened: {symbol} {side} {position_size} @ {entry_price}")
            return {"status": "opened", "position": self.position}
            
        except Exception as e:
            logger.error(f"Update position error: {e}")
            return {"status": "error", "message": str(e)}
    
    def add_to_position(
        self,
        symbol: str,
        add_size: float,
        add_price: float
    ) -> Dict:
        try:
            if not self.position or self.position.get("symbol") != symbol:
                return {"status": "error", "message": "No position to add to"}
            
            current_size = float(self.position.get("position_size", 0))
            current_entry = float(self.position.get("entry_price", 0))
            
            new_size = current_size + add_size
            new_entry = (current_size * current_entry + add_size * add_price) / new_size if new_size > 0 else current_entry
            
            self.position["position_size"] = new_size
            self.position["entry_price"] = new_entry
            
            if symbol in self.position_metadata:
                self.position_metadata[symbol]["position_size"] = new_size
                self.position_metadata[symbol]["entry_price"] = new_entry
                self.position_metadata[symbol]["scale_in_count"] = \
                    self.position_metadata[symbol].get("scale_in_count", 1) + 1
            
            logger.info(f"Position scaled: {symbol} +{add_size} @ {add_price}, new total={new_size} @ {new_entry:.2f}")
            return {"status": "scaled", "new_size": new_size, "new_entry": new_entry}
            
        except Exception as e:
            logger.error(f"Add to position error: {e}")
            return {"status": "error", "message": str(e)}
    
    def calculate_pnl(self, current_price: float) -> Dict:
        try:
            current_price = float(current_price) if current_price is not None else 0.0
            
            if not self.position:
                return {"pnl": 0.0, "pnl_pct": 0.0, "exchange_pnl_pct": 0.0, "initial_margin": 0.0}
            
            entry_price = float(self.position.get("entry_price", 0))
            position_size = float(self.position.get("position_size", 0))
            side = self.position.get("side", "long")
            
            if entry_price <= 0 or position_size <= 0:
                return {"pnl": 0.0, "pnl_pct": 0.0, "exchange_pnl_pct": 0.0, "initial_margin": 0.0}
            
            # 计算未实现盈亏（USDT）
            if side == "long":
                pnl = (current_price - entry_price) * position_size
                pnl_pct = (current_price - entry_price) / entry_price * 100
            else:
                pnl = (entry_price - current_price) * position_size
                pnl_pct = (entry_price - current_price) / entry_price * 100
            
            # 计算交易所收益率：回报率 = 未实现盈亏 / 初始保证金
            leverage = 20  # 20倍杠杆
            initial_margin = (entry_price * position_size) / leverage
            
            if initial_margin > 0:
                exchange_pnl_pct = (pnl / initial_margin) * 100
            else:
                exchange_pnl_pct = 0
            
            self.position["current_price"] = current_price
            self.position["current_pnl"] = pnl
            self.position["current_pnl_pct"] = pnl_pct
            self.position["exchange_pnl_pct"] = exchange_pnl_pct
            self.position["initial_margin"] = initial_margin
            
            peak_price = float(self.position.get("peak_price", entry_price))
            if side == "long" and current_price > peak_price:
                self.position["peak_price"] = current_price
                peak_price = current_price
            elif side == "short" and current_price < peak_price:
                self.position["peak_price"] = current_price
                peak_price = current_price
            
            if side == "long":
                max_profit = (peak_price - entry_price) * position_size
                max_profit_pct = (peak_price - entry_price) / entry_price * 100
                drawdown = (peak_price - current_price) * position_size
                drawdown_pct = (peak_price - current_price) / peak_price * 100 if peak_price > 0 else 0
            else:
                max_profit = (entry_price - peak_price) * position_size
                max_profit_pct = (entry_price - peak_price) / entry_price * 100
                drawdown = (current_price - peak_price) * position_size
                drawdown_pct = (current_price - peak_price) / peak_price * 100 if peak_price > 0 else 0
            
            self.position["max_profit"] = max_profit
            self.position["max_profit_pct"] = max_profit_pct
            self.position["drawdown"] = drawdown
            self.position["drawdown_pct"] = drawdown_pct
            
            return {
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "max_profit": max_profit,
                "max_profit_pct": max_profit_pct,
                "drawdown": drawdown,
                "drawdown_pct": drawdown_pct
            }
            
        except Exception as e:
            logger.error(f"Calculate PnL error: {e}")
            import traceback
            traceback.print_exc()
            return {"pnl": 0.0, "pnl_pct": 0.0}
    
    def calculate_hold_minutes(self, binance_client=None) -> int:
        """计算持仓时间，支持从交易所获取真实开仓时间"""
        try:
            if not self.position:
                return 0
            
            symbol = self.position.get("symbol")
            entry_time = self.position.get("entry_time")
            
            if not entry_time or not symbol:
                return 0
            
            # 使用持仓时间工具计算持仓时间，包含交易所回退机制
            hold_minutes = position_time_utils.calculate_hold_minutes_with_fallback(
                symbol, binance_client, entry_time
            )
            
            self.position["hold_minutes"] = hold_minutes
            return hold_minutes
            
        except Exception as e:
            logger.error(f"Calculate hold minutes error: {e}")
            return 0
    
    def check_min_hold_time(self, symbol: str) -> Dict:
        if not self.position or self.position.get("symbol") != symbol:
            return {"allowed": True, "reason": "No position"}
        
        entry_time = self.position.get("entry_time")
        expected_hold = self.position.get("expected_hold_minutes", 30)
        
        if not entry_time:
            return {"allowed": True, "reason": "No entry time"}
        
        hold_minutes = (datetime.now() - entry_time).total_seconds() / 60
        
        if hold_minutes < expected_hold:
            return {
                "allowed": False,
                "reason": "MIN_HOLD_TIME_NOT_MET",
                "held_minutes": hold_minutes,
                "required_minutes": expected_hold,
                "remaining_minutes": expected_hold - hold_minutes
            }
        
        return {"allowed": True, "reason": "Min hold time satisfied"}
    
    def check_local_sl_tp(self, symbol: str, current_price: float) -> Dict:
        if not self.position or self.position.get("symbol") != symbol:
            return {"triggered": False}
        
        stop_loss = self.position.get("stop_loss", 0)
        take_profit = self.position.get("take_profit", 0)
        side = self.position.get("side", "long")
        
        if stop_loss <= 0 and take_profit <= 0:
            return {"triggered": False}
        
        triggered = False
        trigger_type = None
        
        if side == "long":
            if stop_loss > 0 and current_price <= stop_loss:
                triggered = True
                trigger_type = "STOP_LOSS"
                logger.info(f"[{symbol}] SLTP_SIMULATION_TRIGGERED: STOP_LOSS at {stop_loss}")
            elif take_profit > 0 and current_price >= take_profit:
                triggered = True
                trigger_type = "TAKE_PROFIT"
                logger.info(f"[{symbol}] SLTP_SIMULATION_TRIGGERED: TAKE_PROFIT at {take_profit}")
        else:
            if stop_loss > 0 and current_price >= stop_loss:
                triggered = True
                trigger_type = "STOP_LOSS"
                logger.info(f"[{symbol}] SLTP_SIMULATION_TRIGGERED: STOP_LOSS at {stop_loss}")
            elif take_profit > 0 and current_price <= take_profit:
                triggered = True
                trigger_type = "TAKE_PROFIT"
                logger.info(f"[{symbol}] SLTP_SIMULATION_TRIGGERED: TAKE_PROFIT at {take_profit}")
        
        return {
            "triggered": triggered,
            "trigger_type": trigger_type,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
    
    def get_position_state(self) -> Dict:
        try:
            if not self.position:
                return {
                    "has_position": False,
                    "symbol": None,
                    "position_size": 0,
                    "entry_price": 0,
                    "current_pnl": 0,
                    "current_pnl_pct": 0,
                    "max_profit": 0,
                    "drawdown": 0,
                    "hold_minutes": 0,
                    "expected_hold_minutes": 0,
                    "stop_loss": 0,
                    "take_profit": 0
                }
            
            return {
                "has_position": True,
                "symbol": self.position.get("symbol"),
                "side": self.position.get("side"),
                "position_size": float(self.position.get("position_size", 0)),
                "entry_price": float(self.position.get("entry_price", 0)),
                "current_price": float(self.position.get("current_price", 0)),
                "current_pnl": float(self.position.get("current_pnl", 0)),
                "current_pnl_pct": float(self.position.get("current_pnl_pct", 0)),
                "exchange_pnl_pct": float(self.position.get("exchange_pnl_pct", 0)),
                "initial_margin": float(self.position.get("initial_margin", 0)),
                "max_profit": float(self.position.get("max_profit", 0)),
                "max_profit_pct": float(self.position.get("max_profit_pct", 0)),
                "drawdown": float(self.position.get("drawdown", 0)),
                "drawdown_pct": float(self.position.get("drawdown_pct", 0)),
                "hold_minutes": int(self.position.get("hold_minutes", 0)),
                "expected_hold_minutes": int(self.position.get("expected_hold_minutes", 60)),
                "stop_loss": float(self.position.get("stop_loss", 0)),
                "take_profit": float(self.position.get("take_profit", 0)),
                "entry_time": self.position.get("entry_time")
            }
            
        except Exception as e:
            logger.error(f"Get position state error: {e}")
            return {"has_position": False}
    
    def set_stop_loss(self, symbol: str, stop_loss: float) -> None:
        if self.position and self.position.get("symbol") == symbol:
            self.position["stop_loss"] = stop_loss
            if symbol in self.position_metadata:
                self.position_metadata[symbol]["stop_loss"] = stop_loss
            logger.info(f"[{symbol}] Stop loss set to {stop_loss}")
    
    def set_take_profit(self, symbol: str, take_profit: float) -> None:
        if self.position and self.position.get("symbol") == symbol:
            self.position["take_profit"] = take_profit
            if symbol in self.position_metadata:
                self.position_metadata[symbol]["take_profit"] = take_profit
            logger.info(f"[{symbol}] Take profit set to {take_profit}")
    
    def format_position_log(self) -> str:
        try:
            state = self.get_position_state()
            
            if not state.get("has_position"):
                return "Position: None"
            
            return (
                f"Position: {state.get('side', 'N/A').upper()} "
                f"size={state.get('position_size', 0):.4f} "
                f"entry={state.get('entry_price', 0):.2f} "
                f"pnl={state.get('current_pnl_pct', 0):.2f}% "
                f"hold={state.get('hold_minutes', 0)}min"
            )
        except Exception as e:
            return f"Position: Error - {e}"
    
    def dynamic_adjust_stop_loss(self, symbol: str, historical_prices: list, atr: float) -> Dict:
        """
        动态调整止损价格
        
        Args:
            symbol: 交易对
            historical_prices: 历史价格列表
            atr: 平均真实波幅
            
        Returns:
            调整结果
        """
        try:
            if not self.position or self.position.get("symbol") != symbol:
                return {
                    "adjusted": False,
                    "reason": "No position",
                    "current_stop_loss": 0
                }
            
            # 获取当前持仓信息
            position_info = {
                "symbol": symbol,
                "side": self.position.get("side", "long"),
                "current_price": self.position.get("current_price", 0),
                "entry_price": self.position.get("entry_price", 0),
                "stop_loss": self.position.get("stop_loss", 0),
                "take_profit": self.position.get("take_profit", 0),
                "hold_minutes": self.position.get("hold_minutes", 0),
                "current_pnl_pct": self.position.get("current_pnl_pct", 0)
            }
            
            # 调用动态止损调整
            adjustment_result = dynamic_stop_loss.dynamic_stop_loss_adjustment(
                symbol, position_info, historical_prices, atr
            )
            
            # 如果调整成功，更新止损价格
            if adjustment_result.get("adjusted", False):
                new_stop_loss = adjustment_result.get("new_stop_loss", 0)
                old_stop_loss = adjustment_result.get("old_stop_loss", 0)
                
                # 更新持仓止损
                self.position["stop_loss"] = new_stop_loss
                if symbol in self.position_metadata:
                    self.position_metadata[symbol]["stop_loss"] = new_stop_loss
                
                logger.info(f"[{symbol}] 动态止损调整: {old_stop_loss:.2f} -> {new_stop_loss:.2f}")
                
                # 记录调整详情
                trend_analysis = adjustment_result.get("trend_analysis", {})
                logger.info(f"[{symbol}] 趋势分析: {trend_analysis.get('trend', 'neutral')} "
                          f"强度: {trend_analysis.get('strength', 0):.2f}% "
                          f"置信度: {trend_analysis.get('confidence', 0):.1f}")
            
            return adjustment_result
            
        except Exception as e:
            logger.error(f"Dynamic adjust stop loss error: {e}")
            return {
                "adjusted": False,
                "reason": f"Error: {str(e)}",
                "current_stop_loss": self.position.get("stop_loss", 0) if self.position else 0
            }
