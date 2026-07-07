"""Tester för out-of-sample-delningen och det tudelade backtestet."""

from __future__ import annotations

import pandas as pd
import pytest

from src.backtesting.costs import CostModel
from src.backtesting.strategy import Strategy
from src.backtesting.validation import run_split_backtest, split_prices


def _prices(n: int, start_price: float = 100.0, trend: float = 0.1) -> pd.DataFrame:
    closes = [start_price + trend * i for i in range(n)]
    index = pd.date_range("2022-01-03", periods=n, freq="B", name="date")
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


ZERO_COSTS = CostModel(
    courtage_fixed=0.0, courtage_percent=0.0, courtage_min=0.0, slippage_percent=0.0
)


class AlwaysLong(Strategy):
    name = "alltid lång (test)"

    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        return {ticker: 1 for ticker in history}


class TestSplitPrices:
    def test_no_overlap_and_full_coverage(self) -> None:
        prices = {"A": _prices(200)}
        early, late, split_date = split_prices(prices, 0.7)
        assert len(early["A"]) + len(late["A"]) == 200
        assert early["A"].index.max() < split_date
        assert late["A"].index.min() == split_date

    def test_fraction_controls_split_point(self) -> None:
        prices = {"A": _prices(200)}
        early, late, _ = split_prices(prices, 0.5)
        assert len(early["A"]) == 100

    def test_out_of_sample_is_the_later_period(self) -> None:
        prices = {"A": _prices(200)}
        early, late, _ = split_prices(prices)
        assert early["A"].index.max() < late["A"].index.min()

    def test_too_short_history_rejected(self) -> None:
        with pytest.raises(ValueError, match="120"):
            split_prices({"A": _prices(50)})

    def test_invalid_fraction_rejected(self) -> None:
        with pytest.raises(ValueError, match="0.5 och 0.9"):
            split_prices({"A": _prices(200)}, 0.95)


class TestSplitBacktest:
    def test_both_periods_run_with_same_capital(self) -> None:
        prices = {"A": _prices(300)}
        result = run_split_backtest(prices, AlwaysLong(), 100_000, ZERO_COSTS)
        assert result.in_sample.equity_curve.iloc[0] == pytest.approx(100_000)
        assert result.out_of_sample.equity_curve.iloc[0] == pytest.approx(100_000)
        # Out-of-sample börjar där in-sample slutar.
        assert result.out_of_sample.equity_curve.index.min() == result.split_date

    def test_degradation_triggers_warning(self) -> None:
        # Stiger brant första 210 dagarna, faller sedan: en alltid-lång
        # strategi ser bra ut in-sample och dålig out-of-sample.
        rising = [100.0 + 0.5 * i for i in range(210)]
        falling = [rising[-1] - 0.5 * i for i in range(1, 91)]
        closes = rising + falling
        index = pd.date_range("2022-01-03", periods=len(closes), freq="B", name="date")
        frame = pd.DataFrame(
            {
                "open": closes,
                "high": [c + 1 for c in closes],
                "low": [c - 1 for c in closes],
                "close": closes,
                "volume": [1000.0] * len(closes),
            },
            index=index,
        )
        result = run_split_backtest({"A": frame}, AlwaysLong(), 100_000, ZERO_COSTS)
        assert any("overfitting" in w or "skepsis" in w for w in result.warnings)

    def test_consistent_performance_gives_soft_message(self) -> None:
        result = run_split_backtest({"A": _prices(300)}, AlwaysLong(), 100_000, ZERO_COSTS)
        assert any("utesluter inte" in w for w in result.warnings)
