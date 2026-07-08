"""Tester för scorecard-modulen (Morgonkollens beräkningar)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analysis.scorecard import build_scorecard, scorecards_table


def _prices(closes: list[float]) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(closes), freq="B", name="date")
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


class TestTrend:
    def test_uptrend_detected(self) -> None:
        card = build_scorecard("UPP", _prices([100.0 + 0.5 * i for i in range(250)]))
        assert card.trend_label.startswith("upptrend")

    def test_downtrend_detected(self) -> None:
        card = build_scorecard("NED", _prices([300.0 - 0.5 * i for i in range(250)]))
        assert card.trend_label.startswith("nedtrend")

    def test_short_history_is_labelled_not_guessed(self) -> None:
        card = build_scorecard("KORT", _prices([100.0] * 50))
        assert "för kort" in card.trend_label


class TestFields:
    def test_day_change_hand_computed(self) -> None:
        card = build_scorecard("X", _prices([100.0] * 249 + [110.0]))
        assert card.day_change == pytest.approx(0.10)

    def test_52w_levels(self) -> None:
        # Topp 200, botten 100, senast 150: -25 % från högsta, +50 % från lägsta.
        closes = [100.0] * 50 + [200.0] * 50 + [150.0] * 150
        card = build_scorecard("X", _prices(closes))
        assert card.dist_from_52w_high == pytest.approx(-0.25)
        assert card.dist_from_52w_low == pytest.approx(0.50)

    def test_rsi_label_oversold(self) -> None:
        closes = [300.0 - i for i in range(250)]
        card = build_scorecard("X", _prices(closes))
        assert card.rsi_value is not None and card.rsi_value < 30
        assert "översålt" in card.rsi_label

    def test_volatility_matches_std(self) -> None:
        rng = np.random.default_rng(9)
        closes = list(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 300))))
        card = build_scorecard("X", _prices(closes))
        returns = pd.Series(closes).pct_change().dropna().tail(252)
        expected = float(returns.std() * np.sqrt(252))
        assert card.volatility_annual == pytest.approx(expected, rel=1e-6)

    def test_empty_prices_rejected(self) -> None:
        with pytest.raises(ValueError):
            build_scorecard("TOM", pd.DataFrame())


class TestTable:
    def test_missing_values_shown_as_missing(self) -> None:
        card = build_scorecard("KORT", _prices([100.0]))
        table = scorecards_table([card])
        assert table.iloc[0]["Idag"] == "data saknas"
        assert table.iloc[0]["RSI 14"] == "data saknas"

    def test_one_row_per_card(self) -> None:
        cards = [
            build_scorecard("A", _prices([100.0 + i for i in range(250)])),
            build_scorecard("B", _prices([200.0 - 0.1 * i for i in range(250)])),
        ]
        table = scorecards_table(cards)
        assert list(table["Ticker"]) == ["A", "B"]
