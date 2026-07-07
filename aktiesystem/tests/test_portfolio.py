"""Tester för portföljoptimering och rebalansering."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.portfolio.optimization import efficient_frontier, rebalancing_plan


def _returns(n_days: int = 500, seed: int = 5) -> pd.DataFrame:
    """Tre syntetiska tillgångar med olika avkastning/vol och låg korrelation."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "LUGN": rng.normal(0.0003, 0.005, n_days),
            "MEDEL": rng.normal(0.0005, 0.010, n_days),
            "VILD": rng.normal(0.0008, 0.020, n_days),
        }
    )


class TestEfficientFrontier:
    def test_weights_sum_to_one_and_nonnegative(self) -> None:
        result = efficient_frontier(_returns(), n_points=10)
        for point in [result.min_volatility, result.max_sharpe, *result.frontier]:
            weights = np.array(list(point.weights.values()))
            assert np.isclose(weights.sum(), 1.0, atol=1e-4)
            assert (weights >= -1e-8).all()  # long-only som standard

    def test_min_volatility_is_lowest_on_frontier(self) -> None:
        result = efficient_frontier(_returns(), n_points=10)
        min_vol = result.min_volatility.volatility
        assert all(point.volatility >= min_vol - 1e-6 for point in result.frontier)

    def test_max_sharpe_beats_equal_weights(self) -> None:
        returns = _returns()
        result = efficient_frontier(returns, n_points=10, risk_free_rate=0.02)

        def sharpe(point) -> float:
            return (point.expected_return - 0.02) / point.volatility

        mean = returns.mean().to_numpy() * 252
        cov = returns.cov().to_numpy() * 252
        equal = np.full(3, 1 / 3)
        equal_sharpe = (float(equal @ mean) - 0.02) / float(np.sqrt(equal @ cov @ equal))
        assert sharpe(result.max_sharpe) >= equal_sharpe - 1e-9

    def test_frontier_returns_are_increasing(self) -> None:
        result = efficient_frontier(_returns(), n_points=10)
        rets = [point.expected_return for point in result.frontier]
        assert all(b >= a - 1e-9 for a, b in zip(rets, rets[1:], strict=False))

    def test_requires_two_assets(self) -> None:
        with pytest.raises(ValueError, match="två tillgångar"):
            efficient_frontier(_returns()[["LUGN"]])

    def test_requires_enough_history(self) -> None:
        with pytest.raises(ValueError, match="60"):
            efficient_frontier(_returns(30))

    def test_rejects_nan(self) -> None:
        returns = _returns()
        returns.iloc[5, 1] = np.nan
        with pytest.raises(ValueError, match="NaN"):
            efficient_frontier(returns)


class TestRebalancing:
    def test_hand_computed(self) -> None:
        # Portfölj 100 000: A=70 000, B=30 000. Mål 50/50
        # -> sälj A för 20 000, köp B för 20 000.
        plan = rebalancing_plan({"A": 70_000, "B": 30_000}, {"A": 0.5, "B": 0.5})
        a = plan[plan["ticker"] == "A"].iloc[0]
        b = plan[plan["ticker"] == "B"].iloc[0]
        assert a["handla_for"] == pytest.approx(-20_000)
        assert b["handla_for"] == pytest.approx(20_000)

    def test_new_holding_gets_full_buy(self) -> None:
        plan = rebalancing_plan({"A": 100_000}, {"A": 0.8, "NY": 0.2})
        ny = plan[plan["ticker"] == "NY"].iloc[0]
        assert ny["nuvarande_varde"] == 0.0
        assert ny["handla_for"] == pytest.approx(20_000)

    def test_trades_net_to_zero(self) -> None:
        plan = rebalancing_plan(
            {"A": 50_000, "B": 30_000, "C": 20_000}, {"A": 0.2, "B": 0.3, "C": 0.5}
        )
        assert plan["handla_for"].sum() == pytest.approx(0.0)

    def test_invalid_weight_sum_rejected(self) -> None:
        with pytest.raises(ValueError, match="summera"):
            rebalancing_plan({"A": 1000}, {"A": 0.5})

    def test_negative_weights_rejected(self) -> None:
        with pytest.raises(ValueError, match="Negativa"):
            rebalancing_plan({"A": 1000, "B": 1000}, {"A": 1.5, "B": -0.5})
