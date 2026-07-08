"""Tester för körningsloggning (reproducerbarhet) och exponeringsmåttet."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.backtesting.costs import CostModel
from src.backtesting.engine import BacktestEngine
from src.backtesting.persistence import run_to_dict, save_backtest_run
from src.backtesting.strategy import Strategy

ZERO_COSTS = CostModel(
    courtage_fixed=0.0, courtage_percent=0.0, courtage_min=0.0, slippage_percent=0.0
)


def _prices(n: int) -> pd.DataFrame:
    closes = [100.0 + 0.2 * i for i in range(n)]
    index = pd.date_range("2024-01-01", periods=n, freq="B", name="date")
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1000.0] * n,
        },
        index=index,
    )


class AlwaysLong(Strategy):
    name = "alltid lång (test)"

    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        return {ticker: 1 for ticker in history}


class NeverLong(Strategy):
    name = "aldrig lång (test)"

    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        return {ticker: 0 for ticker in history}


class TestExposure:
    def test_always_long_has_high_exposure(self) -> None:
        result = BacktestEngine({"A": _prices(50)}, AlwaysLong(), 10_000, ZERO_COSTS).run()
        # Köpet sker dag 2 (signal dag 1 -> exekvering dag 2): 49/50 dagar i marknaden.
        assert result.metrics["exponering"] == pytest.approx(49 / 50)

    def test_never_long_has_zero_exposure(self) -> None:
        result = BacktestEngine({"A": _prices(50)}, NeverLong(), 10_000, ZERO_COSTS).run()
        assert result.metrics["exponering"] == 0.0


class TestPersistence:
    def _run(self):
        return BacktestEngine({"A": _prices(60)}, AlwaysLong(), 10_000, ZERO_COSTS).run()

    def test_saved_file_is_valid_json_with_key_fields(self, tmp_path: Path) -> None:
        result = self._run()
        path = save_backtest_run(result, ["A"], 10_000, ZERO_COSTS, directory=tmp_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["strategi"] == "alltid lång (test)"
        assert payload["tickers"] == ["A"]
        assert payload["startkapital"] == 10_000
        assert payload["period"]["handelsdagar"] == 60
        assert len(payload["equity_kurva"]) == 60
        assert "exponering" in payload["nyckeltal"]

    def test_nan_metrics_become_null_not_invented(self) -> None:
        result = BacktestEngine({"A": _prices(60)}, NeverLong(), 10_000, ZERO_COSTS).run()
        payload = run_to_dict(result, ["A"], 10_000, ZERO_COSTS)
        # Win rate är NaN utan affärer -> ska bli None i JSON, inte ett tal.
        assert payload["nyckeltal"]["win_rate"] is None

    def test_filename_contains_strategy_slug(self, tmp_path: Path) -> None:
        path = save_backtest_run(self._run(), ["A"], 10_000, ZERO_COSTS, directory=tmp_path)
        assert "alltid-l" in path.name and path.suffix == ".json"
