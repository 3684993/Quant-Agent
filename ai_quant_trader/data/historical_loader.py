import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List
from core.logger import logger
from config.settings import settings


class HistoricalLoader:
    def __init__(self, base_url: str = None, socks5_proxy: str = None):
        self.base_url = base_url or settings.binance_testnet_url or "https://demo-fapi.binance.com"
        self.socks5_proxy = socks5_proxy or settings.socks5_proxy
        
        self.proxies = None
        if self.socks5_proxy:
            proxy_url = self.socks5_proxy
            if proxy_url.startswith("socks5://") and not proxy_url.startswith("socks5h://"):
                proxy_url = proxy_url.replace("socks5://", "socks5h://")
            self.proxies = {
                "http": proxy_url,
                "https": proxy_url
            }
        
        logger.info(f"HistoricalLoader initialized with base_url: {self.base_url}")
    
    def load_klines(
        self,
        symbol: str,
        interval: str = "15m",
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 1500
    ) -> pd.DataFrame:
        try:
            all_klines = []
            current_start = start_time
            current_end = end_time or datetime.now()
            
            while current_start is None or current_start < current_end:
                params = {
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit
                }
                
                if current_start:
                    params["startTime"] = int(current_start.timestamp() * 1000)
                
                if current_end:
                    params["endTime"] = int(current_end.timestamp() * 1000)
                
                logger.info(f"Fetching klines: {symbol} {interval} from {current_start or 'earliest'}")
                
                response = requests.get(
                    f"{self.base_url}/fapi/v1/klines",
                    params=params,
                    proxies=self.proxies,
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    break
                
                klines = response.json()
                
                if not klines:
                    logger.info("No more klines available")
                    break
                
                all_klines.extend(klines)
                
                last_timestamp = klines[-1][0]
                current_start = datetime.fromtimestamp(last_timestamp / 1000) + timedelta(milliseconds=1)
                
                if len(klines) < limit:
                    break
            
            df = self._parse_klines(all_klines)
            
            if start_time:
                df = df[df["timestamp"] >= start_time]
            if end_time:
                df = df[df["timestamp"] <= end_time]
            
            logger.info(f"Loaded {len(df)} klines for {symbol} {interval}")
            
            return df
            
        except Exception as e:
            logger.error(f"Load klines error: {e}")
            return pd.DataFrame()
    
    def _parse_klines(self, klines: List) -> pd.DataFrame:
        try:
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
            
            df = pd.DataFrame(data)
            return df
            
        except Exception as e:
            logger.error(f"Parse klines error: {e}")
            return pd.DataFrame()
    
    def load_recent_days(
        self,
        symbol: str,
        interval: str = "15m",
        days: int = 30
    ) -> pd.DataFrame:
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            return self.load_klines(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time
            )
            
        except Exception as e:
            logger.error(f"Load recent days error: {e}")
            return pd.DataFrame()
    
    def save_to_csv(self, df: pd.DataFrame, filepath: str) -> bool:
        try:
            df.to_csv(filepath, index=False)
            logger.info(f"Saved {len(df)} candles to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Save to CSV error: {e}")
            return False
    
    def load_from_csv(self, filepath: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(filepath)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            logger.info(f"Loaded {len(df)} candles from {filepath}")
            return df
        except Exception as e:
            logger.error(f"Load from CSV error: {e}")
            return pd.DataFrame()
