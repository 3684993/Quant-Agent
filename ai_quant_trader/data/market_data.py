import pandas as pd
import time
from typing import List, Optional
from exchange.binance_client import BinanceClient
from core.logger import logger


class MarketDataService:
    KLINE_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
    
    TIMEFRAME_MAP = {
        "1m": "1m",
        "5m": "5m", 
        "15m": "15m"
    }
    
    def __init__(self, binance_client: BinanceClient, symbol: str = "BTCUSDT", kline_limit: int = 200):
        self.client = binance_client
        self.symbol = symbol
        self.kline_limit = kline_limit
        self.max_retries = 3
        self.retry_delay = 2
        logger.info(f"MarketDataService initialized for {symbol} with limit {kline_limit}")
    
    def get_klines(self, timeframe: str, limit: Optional[int] = None) -> pd.DataFrame:
        if timeframe not in self.TIMEFRAME_MAP:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {list(self.TIMEFRAME_MAP.keys())}")
        
        limit = limit or self.kline_limit
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching {limit} klines for {self.symbol} {timeframe} (attempt {attempt + 1})")
                
                klines = self.client.client.klines(
                    symbol=self.symbol,
                    interval=self.TIMEFRAME_MAP[timeframe],
                    limit=limit
                )
                
                df = self._parse_klines(klines)
                logger.info(f"Successfully fetched {len(df)} klines for {self.symbol} {timeframe}")
                
                return df
                
            except Exception as e:
                logger.error(f"Failed to fetch klines (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    raise
    
    def _parse_klines(self, klines: List) -> pd.DataFrame:
        data = []
        for kline in klines:
            data.append({
                "timestamp": pd.to_datetime(kline[0], unit="ms"),
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5])
            })
        
        df = pd.DataFrame(data, columns=self.KLINE_COLUMNS)
        return df
    
    def get_all_timeframes(self) -> dict:
        result = {}
        for timeframe in self.TIMEFRAME_MAP.keys():
            try:
                result[timeframe] = self.get_klines(timeframe)
            except Exception as e:
                logger.error(f"Failed to get klines for {timeframe}: {e}")
                result[timeframe] = pd.DataFrame(columns=self.KLINE_COLUMNS)
        
        return result
