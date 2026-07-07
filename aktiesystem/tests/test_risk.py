"""Tester för riskmodulen mot handräknade referensvärden."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.risk.risk import (
    correlation_matrix,
    daily_returns,
    drawdown_series,
    historical_var,
    max_drawdown,
    portfolio_volatility,
    position_size_fixed_risk,
)


class TestPositionSizing:
    def test_hand_computed(self) -> None:
        # 100 000 kr, 1 % risk = 1 000 kr. Entry 100, stop 95 -> 5 kr/aktie.
        # 1000/5 = 200 aktier, position 20 000 kr.
        result = position_size_fixed_risk(100_000, 0.01, 100.0, 95.0)
        assert result.shares == 200
        assert result.position_value == 20_000.0
        assert result.risk_amount == 1_000.0

    def test_position_capped_at_portfolio_value(self) -> None:
        # Snäv stop: 10 000/0.1 = 100 000 aktier à 100 kr = 10 Mkr -> orimligt.
        # Ska begränsas till 100 000/100 = 1 000 aktier (ingen belåning).
        result = position_size_fixed_risk(100_000, 0.10, 100.0, 99.9)
        assert result.shares == 1_000

    def test_stop_above_entry_rejected(self) -> None:
        with pytest.raises(ValueError, match="Stop loss"):
            position_size_fixed_risk(100_000, 0.01, 100.0, 105.0)

    def test_extreme_risk_rejected(self) -> None:
        with pytest.raises(ValueError):
            position_size_fixed_risk(100_000, 0.5, 100.0, 95.0)


class TestReturnsAndVolatility:
    def test_daily_returns_hand_computed(self) -> None:
        returns = daily_returns(pd.Series([100.0, 110.0, 99.0]))
        assert returns.tolist() == pytest.approx([0.10, -0.10])

    def test_single_asset_volatility_matches_std(self) -> None:
        rng = np.random.default_rng(7)
        returns = pd.DataFrame({"A": rng.normal(0, 0.01, 500)})
        vol = portfolio_volatility(returns, np.array([1.0]))
        expected = float(returns["A"].std() * np.sqrt(252))
        assert vol == pytest.approx(expected)

    def test_diversification_lowers_volatility(self) -> None:
        # Två okorrelerade tillgångar med samma vol: 50/50-portfölj ska ha
        # lägre vol än endera ensam (diversifieringseffekten).
        rng = np.random.default_rng(11)
        returns = pd.DataFrame({"A": rng.normal(0, 0.01, 1000), "B": rng.normal(0, 0.01, 1000)})
        solo = portfolio_volatility(returns, np.array([1.0, 0.0]))
        blended = portfolio_volatility(returns, np.array([0.5, 0.5]))
        assert blended < solo

    def test_weights_must_sum_to_one(self) -> None:
        returns = pd.DataFrame({"A": [0.01, -0.01], "B": [0.0, 0.0]})
        with pytest.raises(ValueError, match="summera"):
            portfolio_volatility(returns, np.array([0.7, 0.7]))


class TestCorrelation:
    def test_perfectly_correlated(self) -> None:
        base = pd.Series(np.random.default_rng(3).normal(0, 0.01, 100))
        returns = pd.DataFrame({"A": base, "B": base * 2})
        matrix = correlation_matrix(returns)
        assert matrix.loc["A", "B"] == pytest.approx(1.0)

    def test_requires_two_assets(self) -> None:
        with pytest.raises(ValueError):
            correlation_matrix(pd.DataFrame({"A": [0.01, 0.02]}))


class TestDrawdown:
    def test_hand_computed(self) -> None:
        # Topp 120, botten 90: 90/120 - 1 = -0.25.
        equity = pd.Series([100.0, 120.0, 90.0, 110.0])
        assert max_drawdown(equity) == pytest.approx(-0.25)

    def test_monotonic_growth_has_zero_drawdown(self) -> None:
        assert max_drawdown(pd.Series([100.0, 101.0, 102.0])) == pytest.approx(0.0)

    def test_drawdown_series_zero_at_new_highs(self) -> None:
        series = drawdown_series(pd.Series([100.0, 120.0, 90.0, 130.0]))
        assert series.iloc[1] == pytest.approx(0.0)
        assert series.iloc[2] == pytest.approx(-0.25)
        assert series.iloc[3] == pytest.approx(0.0)


class TestVaR:
    def test_hand_computed_quantile(self) -> None:
        # 100 avkastningar: -0.01 till -0.10 (10 st) och 90 st +0.01.
        # 5 %-kvantilen ligger bland de stora förlusterna.
        losses = [-(i + 1) / 100 for i in range(10)]
        gains = [0.01] * 90
        returns = pd.Series(losses + gains)
        var = historical_var(returns, confidence=0.95, portfolio_value=100_000)
        expected = -float(np.quantile(returns, 0.05)) * 100_000
        assert var == pytest.approx(expected)
        assert var > 0

    def test_all_positive_returns_gives_zero_var(self) -> None:
        returns = pd.Series([0.01] * 50)
        assert historical_var(returns, 0.95) == 0.0

    def test_too_few_observations_rejected(self) -> None:
        with pytest.raises(ValueError, match="30"):
            historical_var(pd.Series([0.01] * 10), 0.95)
