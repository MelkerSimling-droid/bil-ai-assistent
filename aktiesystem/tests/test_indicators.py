"""Tester för tekniska indikatorer mot handräknade referensvärden.

Varje referensvärde i denna fil är uträknat för hand (härledningen står i
kommentarer) — testerna beror inte på något externt bibliotek.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.indicators.technical import atr, bollinger_bands, compute_all, ema, macd, obv, rsi, sma


def _series(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values)))


class TestSMA:
    def test_hand_computed(self) -> None:
        # [1,2,3,4,5], period 3: (1+2+3)/3=2, (2+3+4)/3=3, (3+4+5)/3=4
        result = sma(_series([1, 2, 3, 4, 5]), 3)
        assert result.iloc[:2].isna().all()
        assert result.iloc[2:].tolist() == [2.0, 3.0, 4.0]

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError):
            sma(_series([1, 2]), 3)


class TestEMA:
    def test_hand_computed(self) -> None:
        # [2,4,6,8,10], period 3: seed=SMA(2,4,6)=4; alpha=0.5
        # idx3: 0.5*8+0.5*4=6; idx4: 0.5*10+0.5*6=8
        result = ema(_series([2, 4, 6, 8, 10]), 3)
        assert result.iloc[:2].isna().all()
        assert result.iloc[2:].tolist() == pytest.approx([4.0, 6.0, 8.0])

    def test_constant_series_equals_constant(self) -> None:
        result = ema(_series([5.0] * 30), 10)
        assert result.dropna().tolist() == pytest.approx([5.0] * 21)


class TestRSI:
    def test_all_gains_is_100(self) -> None:
        result = rsi(_series(list(range(1, 20))), 14)
        assert result.iloc[14:].tolist() == pytest.approx([100.0] * 5)

    def test_all_losses_is_0(self) -> None:
        result = rsi(_series(list(range(20, 1, -1))), 14)
        assert result.iloc[14:].tolist() == pytest.approx([0.0] * 5)

    def test_hand_computed_alternating(self) -> None:
        # [10,11,10,11,10], period 3. Deltas: +1,-1,+1,-1.
        # Seed idx3: avg_gain=mean(1,0,1)=2/3, avg_loss=mean(0,1,0)=1/3
        #   -> RS=2 -> RSI=100-100/3=66.667
        # idx4: avg_gain=(2/3*2+0)/3=4/9, avg_loss=(1/3*2+1)/3=5/9
        #   -> RS=0.8 -> RSI=100-100/1.8=44.444
        result = rsi(_series([10, 11, 10, 11, 10]), 3)
        assert result.iloc[3] == pytest.approx(66.6667, abs=1e-3)
        assert result.iloc[4] == pytest.approx(44.4444, abs=1e-3)

    def test_warmup_is_nan(self) -> None:
        result = rsi(_series(list(range(1, 20))), 14)
        assert result.iloc[:14].isna().all()


class TestMACD:
    def test_equals_ema_difference(self) -> None:
        close = _series([float(100 + np.sin(i / 5) * 10) for i in range(80)])
        result = macd(close)
        expected = ema(close, 12) - ema(close, 26)
        pd.testing.assert_series_equal(
            result["macd"].dropna(), expected.dropna(), check_names=False
        )

    def test_constant_price_gives_zero(self) -> None:
        result = macd(_series([50.0] * 60))
        assert result["macd"].dropna().abs().max() == pytest.approx(0.0)
        assert result["histogram"].dropna().abs().max() == pytest.approx(0.0)

    def test_fast_must_be_less_than_slow(self) -> None:
        with pytest.raises(ValueError):
            macd(_series([1.0] * 100), fast=26, slow=12)


class TestBollinger:
    def test_hand_computed(self) -> None:
        # [1,2,3,4,5], period 3, 2 std. Vid idx2: middle=2,
        # std(ddof=0) av (1,2,3) = sqrt(2/3) ≈ 0.81650
        result = bollinger_bands(_series([1, 2, 3, 4, 5]), 3, 2.0)
        std = np.sqrt(2.0 / 3.0)
        assert result["middle"].iloc[2] == pytest.approx(2.0)
        assert result["upper"].iloc[2] == pytest.approx(2.0 + 2 * std)
        assert result["lower"].iloc[2] == pytest.approx(2.0 - 2 * std)

    def test_bands_symmetric_around_middle(self) -> None:
        close = _series([float(50 + np.cos(i / 3) * 5) for i in range(40)])
        result = bollinger_bands(close, 20).dropna()
        upper_gap = result["upper"] - result["middle"]
        lower_gap = result["middle"] - result["lower"]
        pd.testing.assert_series_equal(upper_gap, lower_gap, check_names=False)


class TestATR:
    def test_hand_computed(self) -> None:
        # Se härledning: TR dag1-3 = 2 -> seed ATR=2; dag4 TR=4
        # -> ATR = (2*2+4)/3 = 8/3
        high = _series([12, 13, 14, 15, 18])
        low = _series([10, 11, 12, 13, 14])
        close = _series([11, 12, 13, 14, 16])
        result = atr(high, low, close, 3)
        assert result.iloc[:3].isna().all()
        assert result.iloc[3] == pytest.approx(2.0)
        assert result.iloc[4] == pytest.approx(8.0 / 3.0)


class TestOBV:
    def test_hand_computed(self) -> None:
        # close [10,11,11,10,12], vol [100,200,300,400,500]
        # riktning [0,+1,0,-1,+1] -> kumulativt [0,200,200,-200,300]
        close = _series([10, 11, 11, 10, 12])
        volume = _series([100, 200, 300, 400, 500])
        assert obv(close, volume).tolist() == [0.0, 200.0, 200.0, -200.0, 300.0]

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError):
            obv(_series([1, 2]), _series([1, 2, 3]))


class TestComputeAll:
    def test_adds_expected_columns(self) -> None:
        rng = np.random.default_rng(42)
        n = 250
        index = pd.date_range("2023-01-01", periods=n)
        close = pd.Series(100 + rng.normal(0, 1, n).cumsum(), index=index)
        prices = pd.DataFrame(
            {
                "open": close.shift(1).fillna(100.0),
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": pd.Series(rng.integers(1000, 5000, n).astype(float), index=index),
            },
            index=index,
        )
        result = compute_all(prices)
        for column in [
            "sma_20",
            "sma_50",
            "sma_200",
            "ema_20",
            "rsi_14",
            "macd",
            "signal",
            "histogram",
            "bb_upper",
            "atr_14",
            "obv",
        ]:
            assert column in result.columns
        assert result["rsi_14"].iloc[:14].isna().all()
        assert result["rsi_14"].dropna().between(0, 100).all()

    def test_missing_columns_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_all(pd.DataFrame({"close": [1.0, 2.0]}))
