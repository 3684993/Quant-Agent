import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import logger
from config.settings import settings
from data.historical_loader import HistoricalLoader
from backtest.backtest_engine import BacktestEngine
from backtest.trade_simulator import TradeSimulator
from performance.performance_analyzer import PerformanceAnalyzer


class BacktestRunner:
    def __init__(
        self,
        symbol: str = None,
        interval: str = "15m",
        days: int = 30,
        initial_capital: float = 10000.0,
        use_ai: bool = False
    ):
        self.symbol = symbol or settings.symbol
        self.interval = interval
        self.days = days
        self.initial_capital = initial_capital
        self.use_ai = use_ai
        
        self.loader = HistoricalLoader()
        self.simulator = TradeSimulator(initial_capital=initial_capital)
        self.engine = BacktestEngine(simulator=self.simulator, use_ai=use_ai)
        self.analyzer = PerformanceAnalyzer()
        
        logger.info(
            f"BacktestRunner initialized: "
            f"symbol={self.symbol}, "
            f"interval={self.interval}, "
            f"days={self.days}, "
            f"capital={initial_capital}, "
            f"use_ai={use_ai}"
        )
    
    def run(self) -> dict:
        try:
            logger.info("="*60)
            logger.info("BACKTEST STARTING")
            logger.info("="*60)
            
            logger.info(f"Loading {self.days} days of historical data...")
            
            df = self.loader.load_recent_days(
                symbol=self.symbol,
                interval=self.interval,
                days=self.days
            )
            
            if df.empty:
                logger.error("No historical data loaded")
                return {}
            
            logger.info(f"Loaded {len(df)} candles")
            logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            
            logger.info("Running backtest...")
            
            result = self.engine.run(df, self.symbol)
            
            if not result:
                logger.error("Backtest failed")
                return {}
            
            logger.info("Analyzing performance...")
            
            stats = self.analyzer.analyze(
                result.get("trades", []),
                result.get("equity_curve", [])
            )
            
            stats["initial_capital"] = self.initial_capital
            stats["final_equity"] = result.get("final_equity", self.initial_capital)
            stats["total_return"] = result.get("total_return", 0)
            stats["symbol"] = self.symbol
            stats["interval"] = self.interval
            stats["days"] = self.days
            
            self.analyzer.print_report(stats, self.symbol)
            
            logger.info(self.analyzer.format_summary_log(stats, self.symbol))
            
            return {
                "stats": stats,
                "trades": result.get("trades", []),
                "equity_curve": result.get("equity_curve", [])
            }
            
        except Exception as e:
            logger.error(f"Backtest runner error: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def run_with_params(
        self,
        symbol: str = None,
        interval: str = None,
        days: int = None,
        initial_capital: float = None,
        use_ai: bool = None
    ) -> dict:
        if symbol:
            self.symbol = symbol
        if interval:
            self.interval = interval
        if days:
            self.days = days
        if initial_capital:
            self.initial_capital = initial_capital
            self.simulator = TradeSimulator(initial_capital=initial_capital)
            self.engine = BacktestEngine(simulator=self.simulator, use_ai=self.use_ai)
        if use_ai is not None:
            self.use_ai = use_ai
            self.engine = BacktestEngine(simulator=self.simulator, use_ai=use_ai)
        
        return self.run()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Quant Trader Backtest Runner")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Trading symbol")
    parser.add_argument("--interval", type=str, default="15m", help="Kline interval")
    parser.add_argument("--days", type=int, default=30, help="Number of days to backtest")
    parser.add_argument("--capital", type=float, default=10000.0, help="Initial capital")
    parser.add_argument("--use-ai", action="store_true", help="Use AI for decisions")
    
    args = parser.parse_args()
    
    runner = BacktestRunner(
        symbol=args.symbol,
        interval=args.interval,
        days=args.days,
        initial_capital=args.capital,
        use_ai=args.use_ai
    )
    
    runner.run()


if __name__ == "__main__":
    main()
