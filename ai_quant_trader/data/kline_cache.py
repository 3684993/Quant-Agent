import pandas as pd
from typing import Dict, Optional
from core.logger import logger


class KlineCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        logger.info("KlineCache initialized")
    
    def update(self, symbol: str, timeframe: str, dataframe: pd.DataFrame) -> None:
        if symbol not in self._cache:
            self._cache[symbol] = {}
        
        self._cache[symbol][timeframe] = dataframe.copy()
        
        logger.info(
            f"Cache updated: {symbol} {timeframe} - "
            f"{len(dataframe)} candles, "
            f"latest: {dataframe['timestamp'].iloc[-1] if len(dataframe) > 0 else 'N/A'}"
        )
    
    def get(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        if symbol not in self._cache:
            logger.warning(f"Symbol {symbol} not found in cache")
            return None
        
        if timeframe not in self._cache[symbol]:
            logger.warning(f"Timeframe {timeframe} not found in cache for {symbol}")
            return None
        
        return self._cache[symbol][timeframe].copy()
    
    def get_all_symbols(self) -> list:
        return list(self._cache.keys())
    
    def get_all_timeframes(self, symbol: str) -> list:
        if symbol not in self._cache:
            return []
        return list(self._cache[symbol].keys())
    
    def clear(self, symbol: Optional[str] = None) -> None:
        if symbol:
            if symbol in self._cache:
                del self._cache[symbol]
                logger.info(f"Cache cleared for {symbol}")
        else:
            self._cache.clear()
            logger.info("All cache cleared")
    
    def get_cache_info(self) -> dict:
        info = {}
        for symbol, timeframes in self._cache.items():
            info[symbol] = {}
            for tf, df in timeframes.items():
                info[symbol][tf] = {
                    "candles": len(df),
                    "start_time": df["timestamp"].iloc[0] if len(df) > 0 else None,
                    "end_time": df["timestamp"].iloc[-1] if len(df) > 0 else None
                }
        return info
