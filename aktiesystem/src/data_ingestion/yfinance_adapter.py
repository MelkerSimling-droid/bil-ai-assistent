"""Datakälla: Yahoo Finance via yfinance-biblioteket.

Ingen API-nyckel krävs. Yahoo tillhandahåller dagliga OHLCV-data och
grundläggande fundamenta. Vid fel kastas DataSourceError — systemet
fyller aldrig i gissade värden.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
import yfinance as yf

from src.data_ingestion.base import (
    DataSourceError,
    FundamentalData,
    MarketDataAdapter,
    NewsItem,
)
from src.utils.logging_setup import get_logger
from src.utils.retry import with_retries

logger = get_logger(__name__)

_EXPECTED_COLUMNS = ["open", "high", "low", "close", "volume"]


def _to_float(value: Any) -> float | None:
    """Konverterar ett råvärde till float, eller None om det inte går."""
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None  # NaN -> None


class YFinanceAdapter(MarketDataAdapter):
    """Hämtar marknadsdata från Yahoo Finance."""

    source_name = "yfinance"

    def __init__(self, max_retries: int = 4, backoff_base_seconds: float = 2.0) -> None:
        """Skapar adaptern.

        Args:
            max_retries: Antal försök per anrop innan fel kastas.
            backoff_base_seconds: Basväntetid för exponentiell backoff.
        """
        self._max_retries = max_retries
        self._backoff = backoff_base_seconds

    def fetch_price_history(self, ticker: str, period: str = "10y") -> pd.DataFrame:
        """Se :meth:`MarketDataAdapter.fetch_price_history`."""

        def _download() -> pd.DataFrame:
            frame = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)
            if frame is None or frame.empty:
                raise DataSourceError(f"Yahoo returnerade ingen kurshistorik för {ticker!r}.")
            return frame

        try:
            raw = with_retries(_download, f"OHLCV {ticker}", self._max_retries, self._backoff)
        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(f"Kunde inte hämta kurser för {ticker!r}: {exc}") from exc
        return self._normalize_ohlcv(raw, ticker)

    @staticmethod
    def _normalize_ohlcv(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Normaliserar Yahoos svar till open/high/low/close/volume.

        Raises:
            DataSourceError: Om förväntade kolumner saknas.
        """
        frame = raw.rename(columns=str.lower)
        missing = [col for col in _EXPECTED_COLUMNS if col not in frame.columns]
        if missing:
            raise DataSourceError(f"Kolumner saknas för {ticker!r}: {missing}")
        frame = frame[_EXPECTED_COLUMNS].copy()
        # Normalisera till tidszons-naiva datum (dagsupplösning räcker).
        frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
        frame.index.name = "date"
        frame = frame[~frame.index.duplicated(keep="last")].sort_index()
        # Rader där close saknas är oanvändbara — logga och släng dem öppet.
        invalid = frame["close"].isna().sum()
        if invalid:
            logger.warning("%s: %d rader utan stängningskurs togs bort.", ticker, invalid)
            frame = frame.dropna(subset=["close"])
        if frame.empty:
            raise DataSourceError(f"Ingen användbar kurshistorik för {ticker!r}.")
        return frame

    def fetch_fundamentals(self, ticker: str) -> FundamentalData:
        """Se :meth:`MarketDataAdapter.fetch_fundamentals`."""

        def _download() -> dict[str, Any]:
            info = yf.Ticker(ticker).info
            if not info or info.get("regularMarketPrice") is None and len(info) <= 2:
                raise DataSourceError(f"Yahoo returnerade inga fundamenta för {ticker!r}.")
            return info

        try:
            info = with_retries(_download, f"fundamenta {ticker}", self._max_retries, self._backoff)
        except DataSourceError:
            raise
        except Exception as exc:
            raise DataSourceError(f"Kunde inte hämta fundamenta för {ticker!r}: {exc}") from exc

        return FundamentalData(
            ticker=ticker,
            fetched_at=datetime.now(UTC).isoformat(),
            source=self.source_name,
            name=info.get("longName") or info.get("shortName"),
            currency=info.get("currency"),
            market_cap=_to_float(info.get("marketCap")),
            pe_ratio=_to_float(info.get("trailingPE")),
            forward_pe=_to_float(info.get("forwardPE")),
            pb_ratio=_to_float(info.get("priceToBook")),
            ev_ebitda=_to_float(info.get("enterpriseToEbitda")),
            profit_margin=_to_float(info.get("profitMargins")),
            debt_to_equity=_to_float(info.get("debtToEquity")),
            dividend_yield=_to_float(info.get("dividendYield")),
            free_cash_flow=_to_float(info.get("freeCashflow")),
            shares_outstanding=_to_float(info.get("sharesOutstanding")),
            total_debt=_to_float(info.get("totalDebt")),
            total_cash=_to_float(info.get("totalCash")),
        )

    def fetch_news(self, ticker: str, limit: int = 25) -> list[NewsItem]:
        """Se :meth:`MarketDataAdapter.fetch_news`."""

        def _download() -> list[dict[str, Any]]:
            return yf.Ticker(ticker).news or []

        try:
            raw_items = with_retries(
                _download, f"nyheter {ticker}", self._max_retries, self._backoff
            )
        except Exception as exc:
            raise DataSourceError(f"Kunde inte hämta nyheter för {ticker!r}: {exc}") from exc

        news: list[NewsItem] = []
        for item in raw_items[:limit]:
            # yfinance >= 0.2.5x lägger innehållet under "content".
            content = item.get("content", item)
            title = content.get("title")
            if not title:
                continue
            provider = content.get("provider") or {}
            published = content.get("pubDate") or content.get("providerPublishTime")
            if isinstance(published, (int, float)):
                published = datetime.fromtimestamp(published, tz=UTC).isoformat()
            url = (
                (content.get("canonicalUrl") or {}).get("url")
                if isinstance(content.get("canonicalUrl"), dict)
                else content.get("link")
            )
            news.append(
                NewsItem(
                    ticker=ticker,
                    title=str(title),
                    publisher=provider.get("displayName") if isinstance(provider, dict) else None,
                    published_at=str(published) if published else None,
                    url=url,
                )
            )
        return news
