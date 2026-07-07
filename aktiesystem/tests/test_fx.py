"""Tester för valutamodulen (offline, fejk-adapter)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data_ingestion.base import DataSourceError, FundamentalData, MarketDataAdapter, NewsItem
from src.data_ingestion.cache import MarketDataCache
from src.data_ingestion.fx import fx_pair_ticker, get_fx_rate
from src.data_ingestion.service import MarketDataService


class FxFakeAdapter(MarketDataAdapter):
    """Svarar bara på valutaparet USDSEK=X."""

    source_name = "fake-fx"

    def fetch_price_history(self, ticker: str, period: str = "10y") -> pd.DataFrame:
        if ticker != "USDSEK=X":
            raise DataSourceError(f"okänd ticker {ticker}")
        index = pd.date_range("2026-07-01", periods=3, freq="B", name="date")
        return pd.DataFrame(
            {
                "open": [10.4, 10.5, 10.6],
                "high": [10.5, 10.6, 10.7],
                "low": [10.3, 10.4, 10.5],
                "close": [10.45, 10.55, 10.65],
                "volume": [0.0, 0.0, 0.0],
            },
            index=index,
        )

    def fetch_fundamentals(self, ticker: str) -> FundamentalData:
        raise DataSourceError("stöds ej")

    def fetch_news(self, ticker: str, limit: int = 25) -> list[NewsItem]:
        return []


@pytest.fixture()
def service(tmp_path: Path) -> MarketDataService:
    return MarketDataService(FxFakeAdapter(), MarketDataCache(tmp_path / "fx.sqlite"))


def test_pair_ticker_format() -> None:
    assert fx_pair_ticker("usd", "sek") == "USDSEK=X"


def test_same_currency_is_one(service: MarketDataService) -> None:
    assert get_fx_rate(service, "SEK", "SEK") == (1.0, "samma valuta")


def test_rate_uses_latest_close(service: MarketDataService) -> None:
    result = get_fx_rate(service, "USD", "SEK")
    assert result is not None
    rate, rate_date = result
    assert rate == pytest.approx(10.65)
    assert rate_date == "2026-07-03"


def test_missing_pair_returns_none_not_a_guess(service: MarketDataService) -> None:
    assert get_fx_rate(service, "JPY", "SEK") is None
