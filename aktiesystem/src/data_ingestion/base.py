"""Adapter-interface för marknadsdatakällor.

Alla datakällor (yfinance, Alpha Vantage, ...) implementerar samma
interface så att de kan bytas ut utan att resten av systemet påverkas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd


class DataSourceError(Exception):
    """Ett anrop mot en datakälla misslyckades definitivt (efter retries)."""


@dataclass
class FundamentalData:
    """Fundamentala nyckeltal för ett bolag vid en hämtningstidpunkt.

    Alla fält är Optional: None betyder "data saknas hos källan" och ska
    visas som saknad i UI — aldrig ersättas med ett gissat värde.
    """

    ticker: str
    fetched_at: str  # ISO 8601-tidsstämpel (UTC) för reproducerbarhet
    source: str
    name: str | None = None
    currency: str | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    forward_pe: float | None = None
    pb_ratio: float | None = None
    ev_ebitda: float | None = None
    profit_margin: float | None = None
    debt_to_equity: float | None = None
    dividend_yield: float | None = None
    free_cash_flow: float | None = None
    shares_outstanding: float | None = None
    total_debt: float | None = None
    total_cash: float | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class NewsItem:
    """En nyhetsrubrik kopplad till en ticker."""

    ticker: str
    title: str
    publisher: str | None
    published_at: str | None  # ISO 8601 eller None om källan saknar tid
    url: str | None


class MarketDataAdapter(ABC):
    """Abstrakt basklass för datakällor.

    Implementationer ska kasta :class:`DataSourceError` vid definitiva fel
    (efter egna retries) — aldrig returnera påhittade data.
    """

    #: Källans namn, lagras i cache/sync-logg för spårbarhet.
    source_name: str = "abstract"

    @abstractmethod
    def fetch_price_history(
        self, ticker: str, period: str = "10y", interval: str = "1d"
    ) -> pd.DataFrame:
        """Hämtar OHLCV-historik.

        Args:
            ticker: Ticker i källans format (Yahoo: "VOLV-B.ST").
            period: Historiklängd, t.ex. "1y", "10y", "max".
            interval: Barlängd: "1d" (dagsdata), "1h" eller "15m" (intradag).
                Intradagshistorik är typiskt begränsad hos källan.

        Returns:
            DataFrame med DatetimeIndex (stigande) och kolumnerna
            ``open, high, low, close, volume`` (små bokstäver).

        Raises:
            DataSourceError: Om hämtningen misslyckas eller ger tomt svar.
        """

    @abstractmethod
    def fetch_fundamentals(self, ticker: str) -> FundamentalData:
        """Hämtar fundamentala nyckeltal för ett bolag.

        Raises:
            DataSourceError: Om hämtningen misslyckas.
        """

    @abstractmethod
    def fetch_news(self, ticker: str, limit: int = 25) -> list[NewsItem]:
        """Hämtar de senaste nyhetsrubrikerna för en ticker.

        Returns:
            Lista med nyheter; tom lista om källan saknar nyheter (det är
            inte ett fel, men ska visas som "inga nyheter" i UI).

        Raises:
            DataSourceError: Om själva anropet misslyckas.
        """
