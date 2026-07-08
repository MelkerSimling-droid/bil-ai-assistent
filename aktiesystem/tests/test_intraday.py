"""Tester för intradagskedjan: cache, service, VWAP och annualisering."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.backtesting.engine import BacktestEngine
from src.backtesting.metrics import PERIODS_PER_YEAR, compute_metrics
from src.backtesting.strategy import Strategy
from src.data_ingestion.base import DataSourceError, FundamentalData, MarketDataAdapter, NewsItem
from src.data_ingestion.cache import MarketDataCache
from src.data_ingestion.service import MarketDataService
from src.indicators.technical import vwap


def _intraday_frame(n_bars: int = 14) -> pd.DataFrame:
    """Två handelsdagar med timbarer (7 barer per dag)."""
    timestamps = []
    for day in ("2026-07-06", "2026-07-07"):
        timestamps.extend(pd.date_range(f"{day} 09:00", periods=7, freq="h"))
    timestamps = timestamps[:n_bars]
    closes = [100.0 + 0.5 * i for i in range(len(timestamps))]
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1000.0] * len(timestamps),
        },
        index=pd.DatetimeIndex(timestamps, name="date"),
    )


class IntradayFakeAdapter(MarketDataAdapter):
    source_name = "fake-intraday"

    def __init__(self) -> None:
        self.calls = 0

    def fetch_price_history(
        self, ticker: str, period: str = "10y", interval: str = "1d"
    ) -> pd.DataFrame:
        self.calls += 1
        if interval == "1d":
            raise DataSourceError("bara intradag i denna fejk")
        return _intraday_frame()

    def fetch_fundamentals(self, ticker: str) -> FundamentalData:
        raise DataSourceError("stöds ej")

    def fetch_news(self, ticker: str, limit: int = 25) -> list[NewsItem]:
        return []


class TestIntradayService:
    def _service(self, tmp_path: Path) -> tuple[MarketDataService, IntradayFakeAdapter]:
        adapter = IntradayFakeAdapter()
        return MarketDataService(adapter, MarketDataCache(tmp_path / "x.sqlite")), adapter

    def test_roundtrip_preserves_timestamps(self, tmp_path: Path) -> None:
        service, _ = self._service(tmp_path)
        frame = service.get_intraday_history("TEST", "1h")
        assert frame.index[0].hour == 9
        assert len(frame) == 14

    def test_fresh_cache_avoids_api_call(self, tmp_path: Path) -> None:
        service, adapter = self._service(tmp_path)
        service.get_intraday_history("TEST", "1h")
        cached = service.get_intraday_history("TEST", "1h")
        assert adapter.calls == 1
        assert len(cached) == 14

    def test_intervals_are_cached_separately(self, tmp_path: Path) -> None:
        service, _ = self._service(tmp_path)
        service.get_intraday_history("TEST", "1h")
        cache = MarketDataCache(tmp_path / "x.sqlite")
        assert cache.load_intraday("TEST", "1h") is not None
        assert cache.load_intraday("TEST", "15m") is None

    def test_unsupported_interval_rejected(self, tmp_path: Path) -> None:
        service, _ = self._service(tmp_path)
        with pytest.raises(ValueError, match="stöds inte"):
            service.get_intraday_history("TEST", "3m")

    def test_daily_cache_untouched_by_intraday(self, tmp_path: Path) -> None:
        service, _ = self._service(tmp_path)
        service.get_intraday_history("TEST", "1h")
        cache = MarketDataCache(tmp_path / "x.sqlite")
        assert cache.load_prices("TEST") is None


class TestVwap:
    def test_hand_computed_single_session(self) -> None:
        # Bar 1: tp=(12+10+11)/3=11, vol 100 -> vwap 11
        # Bar 2: tp=(14+12+13)/3=13, vol 300
        #   -> vwap = (11*100 + 13*300) / 400 = 12.5
        index = pd.DatetimeIndex(["2026-07-07 09:00", "2026-07-07 10:00"])
        high = pd.Series([12.0, 14.0], index=index)
        low = pd.Series([10.0, 12.0], index=index)
        close = pd.Series([11.0, 13.0], index=index)
        volume = pd.Series([100.0, 300.0], index=index)
        result = vwap(high, low, close, volume)
        assert result.iloc[0] == pytest.approx(11.0)
        assert result.iloc[1] == pytest.approx(12.5)

    def test_resets_between_sessions(self) -> None:
        # Ny handelsdag ska starta om ackumuleringen: första baren dag 2
        # har vwap = sitt eget typiska pris.
        index = pd.DatetimeIndex(["2026-07-06 09:00", "2026-07-07 09:00"])
        high = pd.Series([12.0, 22.0], index=index)
        low = pd.Series([10.0, 20.0], index=index)
        close = pd.Series([11.0, 21.0], index=index)
        volume = pd.Series([100.0, 100.0], index=index)
        result = vwap(high, low, close, volume)
        assert result.iloc[1] == pytest.approx(21.0)

    def test_zero_volume_gives_nan_not_a_guess(self) -> None:
        index = pd.DatetimeIndex(["2026-07-07 09:00"])
        result = vwap(
            pd.Series([12.0], index=index),
            pd.Series([10.0], index=index),
            pd.Series([11.0], index=index),
            pd.Series([0.0], index=index),
        )
        assert np.isnan(result.iloc[0])

    def test_length_mismatch_rejected(self) -> None:
        index = pd.DatetimeIndex(["2026-07-07 09:00"])
        series = pd.Series([1.0], index=index)
        with pytest.raises(ValueError):
            vwap(series, series, series, pd.Series([1.0, 2.0]))


class TestAnnualization:
    def test_same_curve_different_periods_changes_cagr(self) -> None:
        equity = pd.Series(
            [100.0 * 1.001**i for i in range(300)],
            index=pd.date_range("2026-01-01", periods=300, freq="h"),
        )
        daily_metrics, _ = compute_metrics(equity, [], periods_per_year=252.0)
        hourly_metrics, _ = compute_metrics(equity, [], periods_per_year=PERIODS_PER_YEAR["1h"])
        # Tolkat som timbarer motsvarar samma kurva kortare kalendertid
        # -> lägre CAGR än om varje bar vore en hel handelsdag... tvärtom:
        # färre år -> högre CAGR. Huvudsaken: värdena ska skilja sig markant.
        assert hourly_metrics["cagr"] != pytest.approx(daily_metrics["cagr"], rel=0.05)
        assert daily_metrics["total_avkastning"] == hourly_metrics["total_avkastning"]

    def test_engine_accepts_periods_per_year(self) -> None:
        class AlwaysLong(Strategy):
            name = "alltid lång (test)"

            def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
                return {t: 1 for t in history}

        result = BacktestEngine(
            {"A": _intraday_frame()},
            AlwaysLong(),
            10_000,
            periods_per_year=PERIODS_PER_YEAR["1h"],
        ).run()
        assert "sharpe" in result.metrics

    def test_invalid_periods_rejected(self) -> None:
        equity = pd.Series([100.0, 101.0], index=pd.date_range("2026-01-01", periods=2))
        with pytest.raises(ValueError, match="positivt"):
            compute_metrics(equity, [], periods_per_year=0)
