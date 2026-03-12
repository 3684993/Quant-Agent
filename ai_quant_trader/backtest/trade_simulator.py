from typing import Dict, List, Optional
from datetime import datetime
from core.logger import logger


class TradeSimulator:
    def __init__(
        self,
        initial_capital: float = 10000.0,
        fee_rate: float = 0.0004,
        slippage_rate: float = 0.0002
    ):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        
        self.cash = initial_capital
        self.position: Optional[Dict] = None
        self.trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        
        self.peak_equity = initial_capital
        self.max_drawdown = 0.0
        
        logger.info(
            f"TradeSimulator initialized: "
            f"capital={initial_capital}, "
            f"fee={fee_rate}, "
            f"slippage={slippage_rate}"
        )
    
    def open_position(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        timestamp: datetime = None
    ) -> Dict:
        try:
            if self.position:
                logger.warning("Position already exists, cannot open new")
                return {"success": False, "error": "Position exists"}
            
            execution_price = self._apply_slippage(price, side)
            position_value = size * execution_price
            fee = position_value * self.fee_rate
            
            self.position = {
                "symbol": symbol,
                "side": side,
                "size": size,
                "entry_price": execution_price,
                "entry_time": timestamp or datetime.now(),
                "fee_paid": fee
            }
            
            self.cash -= (position_value + fee)
            
            logger.info(
                f"Opened {side} position: {size} @ {execution_price:.2f} "
                f"(fee: {fee:.2f})"
            )
            
            return {
                "success": True,
                "execution_price": execution_price,
                "fee": fee
            }
            
        except Exception as e:
            logger.error(f"Open position error: {e}")
            return {"success": False, "error": str(e)}
    
    def close_position(
        self,
        price: float,
        timestamp: datetime = None
    ) -> Dict:
        try:
            if not self.position:
                logger.warning("No position to close")
                return {"success": False, "error": "No position"}
            
            side = self.position["side"]
            close_side = "sell" if side == "long" else "buy"
            
            execution_price = self._apply_slippage(price, close_side)
            position_value = self.position["size"] * execution_price
            fee = position_value * self.fee_rate
            
            self.cash += (position_value - fee)
            
            pnl = self._calculate_pnl(execution_price)
            pnl_pct = (pnl / (self.position["entry_price"] * self.position["size"])) * 100
            
            trade = {
                "symbol": self.position["symbol"],
                "side": self.position["side"],
                "entry_price": self.position["entry_price"],
                "exit_price": execution_price,
                "size": self.position["size"],
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "entry_time": self.position["entry_time"],
                "exit_time": timestamp or datetime.now(),
                "hold_minutes": self._calculate_hold_minutes(timestamp),
                "total_fees": self.position["fee_paid"] + fee
            }
            
            self.trades.append(trade)
            
            logger.info(
                f"Closed {side} position: {self.position['size']} @ {execution_price:.2f} "
                f"PnL: {pnl:.2f} ({pnl_pct:.2f}%)"
            )
            
            self.position = None
            
            return {
                "success": True,
                "execution_price": execution_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "trade": trade
            }
            
        except Exception as e:
            logger.error(f"Close position error: {e}")
            return {"success": False, "error": str(e)}
    
    def _apply_slippage(self, price: float, side: str) -> float:
        if side in ["long", "buy"]:
            return price * (1 + self.slippage_rate)
        else:
            return price * (1 - self.slippage_rate)
    
    def _calculate_pnl(self, exit_price: float) -> float:
        if not self.position:
            return 0.0
        
        entry_price = self.position["entry_price"]
        size = self.position["size"]
        side = self.position["side"]
        
        if side == "long":
            return (exit_price - entry_price) * size
        else:
            return (entry_price - exit_price) * size
    
    def _calculate_hold_minutes(self, exit_time: datetime = None) -> int:
        if not self.position:
            return 0
        
        entry_time = self.position.get("entry_time")
        if not entry_time:
            return 0
        
        exit_time = exit_time or datetime.now()
        return int((exit_time - entry_time).total_seconds() / 60)
    
    def update_equity(self, current_price: float, timestamp: datetime = None):
        try:
            equity = self.get_equity(current_price)
            
            self.equity_curve.append({
                "timestamp": timestamp or datetime.now(),
                "equity": equity,
                "cash": self.cash,
                "position_value": self._get_position_value(current_price)
            })
            
            if equity > self.peak_equity:
                self.peak_equity = equity
            
            drawdown = (self.peak_equity - equity) / self.peak_equity
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
                
        except Exception as e:
            logger.error(f"Update equity error: {e}")
    
    def get_equity(self, current_price: float) -> float:
        return self.cash + self._get_position_value(current_price)
    
    def _get_position_value(self, current_price: float) -> float:
        if not self.position:
            return 0.0
        
        size = self.position["size"]
        side = self.position["side"]
        
        if side == "long":
            return size * current_price
        else:
            return size * current_price
    
    def get_position_state(self) -> Dict:
        if not self.position:
            return {"has_position": False}
        
        return {
            "has_position": True,
            "symbol": self.position["symbol"],
            "side": self.position["side"],
            "position_size": self.position["size"],
            "entry_price": self.position["entry_price"],
            "entry_time": self.position["entry_time"]
        }
    
    def get_trade_history(self) -> List[Dict]:
        return self.trades
    
    def get_equity_curve(self) -> List[Dict]:
        return self.equity_curve
    
    def reset(self):
        self.cash = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
        self.peak_equity = self.initial_capital
        self.max_drawdown = 0.0
        logger.info("TradeSimulator reset")
