"""Tjänstelager: kombinerar adapter + cache till ett enkelt API.

Detta är ingången övriga moduler och dashboarden använder. Vid nätverksfel
returneras cachad data om sådan finns (tydligt loggat); annars kastas felet
vidare så att UI kan visa "data saknas" — aldrig gissade värden.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.data_ingestion.base import DataSourceError, FundamentalData, MarketDataAdapter, NewsItem
from src.data_ingestion.cache import MarketDataCache
from src.data_ingestion.yfinance_adapter import YFinanceAdapter
from src.utils.config import load_config, resolve_path
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


class MarketDataService:
    """Hämtar marknadsdata med cache-först-strategi."""

    def __init__(
        self,
        adapter: MarketDataAdapter,
        cache: MarketDataCache,
        history_period: str = "10y",
        max_cache_age_hours: float = 12.0,
    ) -> None:
        """Skapar tjänsten.

        Args:
            adapter: Datakälla som implementerar MarketDataAdapter.
            cache: Lokal cache.
            history_period: Historiklängd vid hämtning, t.ex. "10y".
            max_cache_age_hours: Cache yngre än detta återanvänds utan API-anrop.
        """
        self._adapter = adapter
        self._cache = cache
        self._period = history_period
        self._max_age = max_cache_age_hours

    @classmethod
    def from_config(cls, config: dict[str, Any] | None = None) -> MarketDataService:
        """Bygger en tjänst utifrån config.yaml."""
        cfg = config or load_config()
        data_cfg = cfg["data"]
        adapter = YFinanceAdapter(
            max_retries=int(data_cfg.get("max_retries", 4)),
            backoff_base_seconds=float(data_cfg.get("backoff_base_seconds", 2.0)),
        )
        cache = MarketDataCache(resolve_path(data_cfg["cache_db"]))
        return cls(
            adapter,
            cache,
            history_period=str(data_cfg.get("history_period", "10y")),
            max_cache_age_hours=float(data_cfg.get("max_cache_age_hours", 12)),
        )

    def get_price_history(self, ticker: str, force_refresh: bool = False) -> pd.DataFrame:
        """Hämtar kurshistorik: färsk cache först, annars API med cache-fallback.

        Raises:
            DataSourceError: Om varken API eller cache kan leverera data.
        """
        if not force_refresh and self._cache.is_fresh(ticker, "prices", self._max_age):
            cached = self._cache.load_prices(ticker)
            if cached is not None:
                return cached
        try:
            frame = self._adapter.fetch_price_history(ticker, period=self._period)
        except DataSourceError as exc:
            cached = self._cache.load_prices(ticker)
            if cached is not None:
                logger.warning(
                    "API-fel för %s (%s) — använder cachad data, senast synkad %s.",
                    ticker,
                    exc,
                    self._cache.last_synced_at(ticker, "prices"),
                )
                return cached
            raise
        self._cache.store_prices(ticker, frame, self._adapter.source_name, f"period={self._period}")
        return frame

    def get_fundamentals(self, ticker: str, force_refresh: bool = False) -> FundamentalData:
        """Hämtar fundamenta med samma cache-först-strategi som kurser.

        Raises:
            DataSourceError: Om varken API eller cache kan leverera data.
        """
        if not force_refresh and self._cache.is_fresh(ticker, "fundamentals", self._max_age):
            cached = self._cache.load_fundamentals(ticker)
            if cached is not None:
                return cached
        try:
            data = self._adapter.fetch_fundamentals(ticker)
        except DataSourceError as exc:
            cached = self._cache.load_fundamentals(ticker)
            if cached is not None:
                logger.warning(
                    "API-fel för %s (%s) — använder cachade fundamenta från %s.",
                    ticker,
                    exc,
                    cached.fetched_at,
                )
                return cached
            raise
        self._cache.store_fundamentals(data)
        return data

    def get_news(self, ticker: str, limit: int = 25) -> list[NewsItem]:
        """Hämtar nyhetsrubriker (cacheas inte — färskvara).

        Raises:
            DataSourceError: Om anropet misslyckas.
        """
        return self._adapter.fetch_news(ticker, limit=limit)

    def sync_watchlist(self, tickers: list[str]) -> dict[str, str]:
        """Synkar kurser + fundamenta för en lista tickers.

        Fel för en ticker stoppar inte övriga; resultatet redovisar status
        per ticker så att inget fel passerar tyst.

        Returns:
            Dict ticker -> "ok" eller "fel: <beskrivning>".
        """
        results: dict[str, str] = {}
        for ticker in tickers:
            try:
                prices = self.get_price_history(ticker, force_refresh=True)
                self.get_fundamentals(ticker, force_refresh=True)
                results[ticker] = f"ok ({len(prices)} kursrader)"
            except DataSourceError as exc:
                logger.error("Synk misslyckades för %s: %s", ticker, exc)
                results[ticker] = f"fel: {exc}"
        return results
