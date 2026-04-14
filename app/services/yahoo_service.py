"""Service for Yahoo Finance historical data ingestion."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd
import yfinance as yf

from app.core.cache import TTLCache
from app.core.config import settings
from app.core.exceptions import DataFetchError, InvalidStockSymbolError
from app.utils.symbols import normalize_symbol, stock_code


logger = logging.getLogger(__name__)


class YahooFinanceService:
    def __init__(self, cache: TTLCache) -> None:
        self.cache = cache
        self._configure_yfinance_cache()

    @staticmethod
    def _configure_yfinance_cache() -> None:
        cache_dir = Path(settings.yfinance_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = str(cache_dir.resolve())

        try:
            yf.cache.set_cache_location(cache_path)
            yf.set_tz_cache_location(cache_path)
            logger.info("yfinance cache configured at %s", cache_path)
        except Exception:
            logger.warning("Unable to configure yfinance cache location", exc_info=True)

    @staticmethod
    def _retry_sleep(attempt: int) -> None:
        base_delay = max(50, settings.external_api_retry_delay_ms)
        delay_seconds = (base_delay * attempt) / 1000.0
        time.sleep(delay_seconds)

    def get_historical_data(
        self,
        symbol: str,
        period: str | None = None,
        interval: str | None = None,
    ) -> pd.DataFrame:
        period = period or settings.history_period
        interval = interval or settings.history_interval
        normalized_symbol = normalize_symbol(symbol)
        cache_key = f"history:{normalized_symbol}:{period}:{interval}"

        cached = self.cache.get(cache_key)
        if cached is not None:
            logger.info("Cache hit for historical data: %s", normalized_symbol)
            return cached.copy()

        retries = max(0, settings.external_api_retries)
        last_exception: Exception | None = None
        df = pd.DataFrame()

        for attempt in range(1, retries + 2):
            try:
                df = yf.download(
                    tickers=normalized_symbol,
                    period=period,
                    interval=interval,
                    progress=False,
                    auto_adjust=False,
                    actions=False,
                    multi_level_index=False,
                )
                if not df.empty:
                    break
            except Exception as exc:  # pragma: no cover
                last_exception = exc
                logger.warning(
                    "Historical fetch attempt %s failed for %s",
                    attempt,
                    normalized_symbol,
                    exc_info=True,
                )
            if attempt <= retries:
                self._retry_sleep(attempt)

        if df.empty and last_exception is not None:
            raise DataFetchError("Unable to fetch stock data from Yahoo Finance") from last_exception

        if df.empty or "Close" not in df.columns:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

        if df.empty or "Close" not in df.columns:
            raise InvalidStockSymbolError(
                f"No historical data found for symbol '{normalized_symbol}'"
            )

        cleaned = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        cleaned.index = pd.to_datetime(cleaned.index)
        cleaned = cleaned.sort_index()
        cleaned = cleaned.ffill().bfill().dropna()

        if cleaned.empty:
            raise InvalidStockSymbolError(
                f"Insufficient historical data for symbol '{normalized_symbol}'"
            )

        self.cache.set(cache_key, cleaned)
        return cleaned.copy()

    def get_live_quote(self, symbol: str) -> Dict[str, object]:
        normalized_symbol = normalize_symbol(symbol)
        cache_key = f"live:{normalized_symbol}"

        cached = self.cache.get(cache_key)
        if cached is not None:
            return dict(cached)

        retries = max(0, settings.external_api_retries)
        last_exception: Exception | None = None
        intraday = pd.DataFrame()

        for attempt in range(1, retries + 2):
            try:
                ticker = yf.Ticker(normalized_symbol)
                intraday = ticker.history(period="1d", interval="1m")
                if intraday.empty:
                    intraday = ticker.history(period="5d", interval="1d")
                if not intraday.empty:
                    break
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Live quote attempt %s failed for %s",
                    attempt,
                    normalized_symbol,
                    exc_info=True,
                )
            if attempt <= retries:
                self._retry_sleep(attempt)

        if intraday.empty and last_exception is not None:
            raise DataFetchError("Unable to fetch live quote from Yahoo Finance") from last_exception

        if intraday.empty or "Close" not in intraday.columns:
            raise InvalidStockSymbolError(
                f"No live quote available for symbol '{normalized_symbol}'"
            )

        closes = intraday["Close"].dropna().astype(float)
        if closes.empty:
            raise InvalidStockSymbolError(
                f"No valid live close values for symbol '{normalized_symbol}'"
            )

        latest_price = float(closes.iloc[-1])
        previous_price = float(closes.iloc[-2]) if len(closes) > 1 else latest_price

        change = latest_price - previous_price
        change_percent = (change / previous_price * 100.0) if previous_price else 0.0

        payload = {
            "stock": stock_code(normalized_symbol),
            "exchange_symbol": normalized_symbol,
            "price": latest_price,
            "change": change,
            "change_percent": change_percent,
            "currency": "INR",
            "timestamp": datetime.now(timezone.utc),
        }

        self.cache.set(cache_key, payload)
        return payload

    def get_news_headlines(self, symbol: str, limit: int = 12) -> List[str]:
        normalized_symbol = normalize_symbol(symbol)
        cache_key = f"news:{normalized_symbol}:{limit}"

        cached = self.cache.get(cache_key)
        if cached is not None:
            return list(cached)

        headlines: list[str] = []
        retries = max(0, settings.external_api_retries)

        for attempt in range(1, retries + 2):
            try:
                ticker = yf.Ticker(normalized_symbol)
                for item in (ticker.news or [])[:limit]:
                    title = str(item.get("title", "")).strip()
                    if title:
                        headlines.append(title)
                break
            except Exception:
                logger.warning(
                    "News fetch attempt %s failed for %s",
                    attempt,
                    normalized_symbol,
                    exc_info=True,
                )
                if attempt <= retries:
                    self._retry_sleep(attempt)

        self.cache.set(cache_key, headlines)
        return headlines
