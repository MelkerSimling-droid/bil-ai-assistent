"""Tester för cache och tjänstelager. Körs helt offline med en fejk-adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from src.data_ingestion.base import DataSourceError, FundamentalData, MarketDataAdapter, NewsItem
from src.data_ingestion.cache import MarketDataCache
from src.data_ingestion.service import MarketDataService


def _sample_prices() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=5, freq="B", name="date")
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [101.0, 102.0, 103.0, 104.0, 105.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "volume": [1000.0, 1100.0, 1200.0, 1300.0, 1400.0],
        },
        index=index,
    )


class FakeAdapter(MarketDataAdapter):
    """Adapter som svarar med kända data eller kastar fel på kommando."""

    source_name = "fake"

    def __init__(self) -> None:
        self.fail = False
        self.price_calls = 0

    def fetch_price_history(self, ticker: str, period: str = "10y") -> pd.DataFrame:
        self.price_calls += 1
        if self.fail:
            raise DataSourceError("simulerat nätverksfel")
        return _sample_prices()

    def fetch_fundamentals(self, ticker: str) -> FundamentalData:
        if self.fail:
            raise DataSourceError("simulerat nätverksfel")
        return FundamentalData(
            ticker=ticker,
            fetched_at=datetime.now(UTC).isoformat(),
            source=self.source_name,
            pe_ratio=12.5,
        )

    def fetch_news(self, ticker: str, limit: int = 25) -> list[NewsItem]:
        return []


@pytest.fixture()
def service(tmp_path: Path) -> tuple[MarketDataService, FakeAdapter, MarketDataCache]:
    adapter = FakeAdapter()
    cache = MarketDataCache(tmp_path / "test.sqlite")
    return MarketDataService(adapter, cache, max_cache_age_hours=12), adapter, cache


def test_prices_roundtrip_through_cache(service) -> None:
    svc, adapter, cache = service
    frame = svc.get_price_history("TEST")
    cached = cache.load_prices("TEST")
    assert cached is not None
    pd.testing.assert_frame_equal(frame, cached, check_freq=False)


def test_fresh_cache_avoids_api_call(service) -> None:
    svc, adapter, _ = service
    svc.get_price_history("TEST")
    svc.get_price_history("TEST")
    assert adapter.price_calls == 1  # andra anropet gick mot cachen


def test_api_failure_falls_back_to_cache(service) -> None:
    svc, adapter, _ = service
    svc.get_price_history("TEST")
    adapter.fail = True
    frame = svc.get_price_history("TEST", force_refresh=True)
    assert len(frame) == 5  # cachad data, inte påhittad


def test_api_failure_without_cache_raises(service) -> None:
    svc, adapter, _ = service
    adapter.fail = True
    with pytest.raises(DataSourceError):
        svc.get_price_history("OKAND")


def test_fundamentals_roundtrip(service) -> None:
    svc, _, cache = service
    data = svc.get_fundamentals("TEST")
    cached = cache.load_fundamentals("TEST")
    assert cached is not None
    assert cached.pe_ratio == data.pe_ratio == 12.5
    assert cached.ev_ebitda is None  # saknat värde förblir None, fylls aldrig i


def test_sync_watchlist_reports_per_ticker_status(service) -> None:
    svc, adapter, _ = service
    results = svc.sync_watchlist(["A"])
    assert results["A"].startswith("ok")
    adapter.fail = True
    results = svc.sync_watchlist(["B"])
    assert results["B"].startswith("fel")


def test_sync_log_records_timestamp_and_params(service) -> None:
    svc, _, cache = service
    svc.get_price_history("TEST")
    assert cache.last_synced_at("TEST", "prices") is not None
    assert not cache.is_fresh("TEST", "fundamentals", 12)
