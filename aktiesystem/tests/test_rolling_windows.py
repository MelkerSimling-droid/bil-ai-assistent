"""Tester för rullande fönster-utvärderingen."""

from __future__ import annotations

import pandas as pd
import pytest

from src.backtesting.costs import CostModel
from src.backtesting.strategy import Strategy
from src.backtesting.validation import rolling_window_evaluation

ZERO_COSTS = CostModel(
    courtage_fixed=0.0, courtage_percent=0.0, courtage_min=0.0, slippage_percent=0.0
)


def _frame(closes: list[float]) -> pd.DataFrame:
    index = pd.date_range("2021-01-04", periods=len(closes), freq="B", name="date")
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1000.0] * len(closes),
        },
        index=index,
    )


class AlwaysLong(Strategy):
    name = "alltid lång (test)"

    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        return {ticker: 1 for ticker in history}


class TestRollingWindows:
    def test_windows_cover_calendar_without_overlap(self) -> None:
        prices = {"A": _frame([100.0 + 0.1 * i for i in range(300)])}
        windows, _ = rolling_window_evaluation(
            prices, AlwaysLong(), 10_000, ZERO_COSTS, n_windows=4
        )
        assert len(windows) == 4
        total_days = sum(len(w.result.equity_curve) for w in windows)
        assert total_days == 300
        for earlier, later in zip(windows, windows[1:], strict=False):
            assert earlier.end < later.start

    def test_each_window_starts_with_same_capital(self) -> None:
        prices = {"A": _frame([100.0 + 0.1 * i for i in range(300)])}
        windows, _ = rolling_window_evaluation(
            prices, AlwaysLong(), 10_000, ZERO_COSTS, n_windows=2
        )
        for window in windows:
            assert window.result.equity_curve.iloc[0] == pytest.approx(10_000)

    def test_inconsistent_results_trigger_warning(self) -> None:
        # Stiger i första kvartilen, faller sedan hela vägen: bara 1 av 4
        # delperioder blir positiv för en alltid-lång strategi.
        rising = [100.0 + 0.5 * i for i in range(75)]
        falling = [rising[-1] - 0.2 * i for i in range(1, 226)]
        prices = {"A": _frame(rising + falling)}
        _, warnings = rolling_window_evaluation(
            prices, AlwaysLong(), 10_000, ZERO_COSTS, n_windows=4
        )
        assert any("inte konsekvent" in w for w in warnings)

    def test_consistent_results_give_soft_message(self) -> None:
        prices = {"A": _frame([100.0 + 0.2 * i for i in range(300)])}
        _, warnings = rolling_window_evaluation(
            prices, AlwaysLong(), 10_000, ZERO_COSTS, n_windows=4
        )
        assert any("gott tecken" in w for w in warnings)

    def test_too_short_history_rejected(self) -> None:
        prices = {"A": _frame([100.0] * 100)}
        with pytest.raises(ValueError, match="handelsdagar"):
            rolling_window_evaluation(prices, AlwaysLong(), 10_000, ZERO_COSTS, n_windows=4)

    def test_invalid_window_count_rejected(self) -> None:
        prices = {"A": _frame([100.0] * 600)}
        with pytest.raises(ValueError, match="n_windows"):
            rolling_window_evaluation(prices, AlwaysLong(), 10_000, ZERO_COSTS, n_windows=1)
