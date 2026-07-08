"""Tester för backtestmotorn — särskilt att INGEN framtida data läcker.

De två viktigaste testerna:
* TestNoLookahead: strategin kan aldrig se data efter "nu", och en signal
  som uppstår dag T kan aldrig ge en affär före dag T+1.
* TestExecution: affärer fylls exakt på nästa dags öppningskurs
  justerad för slippage, med korrekt courtage.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.backtesting.costs import CostModel
from src.backtesting.engine import BacktestEngine
from src.backtesting.metrics import compute_metrics
from src.backtesting.strategies import (
    BollingerReversionStrategy,
    RsiMeanReversionStrategy,
    SmaCrossoverStrategy,
)
from src.backtesting.strategy import Strategy


def _prices(closes: list[float], opens: list[float] | None = None) -> pd.DataFrame:
    opens = opens or closes
    index = pd.date_range("2024-01-01", periods=len(closes), freq="B", name="date")
    return pd.DataFrame(
        {
            "open": opens,
            "high": [max(o, c) for o, c in zip(opens, closes, strict=True)],
            "low": [min(o, c) for o, c in zip(opens, closes, strict=True)],
            "close": closes,
            "volume": [1000.0] * len(closes),
        },
        index=index,
    )


ZERO_COSTS = CostModel(
    courtage_fixed=0.0, courtage_percent=0.0, courtage_min=0.0, slippage_percent=0.0
)


class AlwaysLongStrategy(Strategy):
    name = "alltid lång (test)"

    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        return {ticker: 1 for ticker in history}


class SpyStrategy(Strategy):
    """Registrerar exakt vad motorn låter strategin se."""

    name = "spion (test)"

    def __init__(self) -> None:
        self.seen_now: list[pd.Timestamp] = []
        self.max_seen: list[pd.Timestamp] = []

    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        latest = max(frame.index.max() for frame in history.values())
        self.seen_now.append(latest)
        self.max_seen.append(max(frame.index.max() for frame in history.values()))
        return {ticker: 0 for ticker in history}


class TestNoLookahead:
    def test_strategy_never_sees_future_data(self) -> None:
        prices = {"A": _prices([100, 101, 102, 103, 104, 105])}
        spy = SpyStrategy()
        BacktestEngine(prices, spy, cost_model=ZERO_COSTS).run()
        calendar = list(prices["A"].index)
        # Strategin anropas en gång per dag, och det senaste datum den ser
        # är exakt "idag" — aldrig något senare.
        assert spy.seen_now == calendar
        assert all(seen <= now for seen, now in zip(spy.max_seen, spy.seen_now, strict=True))

    def test_signal_on_day_t_cannot_trade_before_t_plus_1(self) -> None:
        # Kursen hoppar dag 5 (index 5). En strategi som köper när den ser
        # hoppet kan omöjligt handla före dag 6.
        closes = [100.0] * 5 + [200.0, 200.0, 200.0]

        class JumpChaser(Strategy):
            name = "hoppjagare (test)"

            def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
                return {
                    t: (1 if float(f["close"].iloc[-1]) > 150 else 0) for t, f in history.items()
                }

        prices = {"A": _prices(closes)}
        result = BacktestEngine(prices, JumpChaser(), cost_model=ZERO_COSTS).run()
        jump_day = prices["A"].index[5]
        first_trade_date = result.trades["datum"].min()
        assert first_trade_date > jump_day

    def test_last_day_signal_generates_no_trade(self) -> None:
        # En signal på sista dagen har ingen "nästa öppning" — ingen affär.
        closes = [100.0] * 5 + [200.0]

        class LastDayBuyer(Strategy):
            name = "sistadagsköpare (test)"

            def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
                return {
                    t: (1 if float(f["close"].iloc[-1]) > 150 else 0) for t, f in history.items()
                }

        result = BacktestEngine({"A": _prices(closes)}, LastDayBuyer(), cost_model=ZERO_COSTS).run()
        assert result.trades.empty


class TestExecution:
    def test_fill_at_next_open_with_slippage_and_courtage(self) -> None:
        # Signal uppstår dag 0 (alltid lång). Köpet ska ske dag 1 på
        # open=110 * (1+0.001), courtage = max(5, 0.1 % av värdet).
        costs = CostModel(
            courtage_fixed=0.0, courtage_percent=0.001, courtage_min=5.0, slippage_percent=0.001
        )
        prices = {"A": _prices([100, 111, 112, 113], opens=[100, 110, 111, 112])}
        result = BacktestEngine(
            prices, AlwaysLongStrategy(), start_capital=100_000, cost_model=costs
        ).run()
        buy = result.trades.iloc[0]
        assert buy["typ"] == "köp"
        assert buy["datum"] == prices["A"].index[1]
        expected_price = 110 * 1.001
        assert buy["kurs"] == pytest.approx(expected_price)
        assert buy["courtage"] == pytest.approx(max(5.0, 0.001 * buy["antal"] * expected_price))

    def test_cash_accounting_hand_computed(self) -> None:
        # Utan kostnader: 10 000 kr, open 100 -> 100 aktier, kassa 0.
        # Equity dag 2 = 100 aktier * close 120 = 12 000.
        prices = {"A": _prices([100, 100, 120], opens=[100, 100, 120])}
        result = BacktestEngine(
            prices, AlwaysLongStrategy(), start_capital=10_000, cost_model=ZERO_COSTS
        ).run()
        assert result.trades.iloc[0]["antal"] == 100
        assert result.equity_curve.iloc[-1] == pytest.approx(12_000.0)

    def test_courtage_reduces_final_equity(self) -> None:
        prices = {"A": _prices([100.0] * 10)}
        free = BacktestEngine(prices, AlwaysLongStrategy(), 10_000, ZERO_COSTS).run()
        priced = BacktestEngine(
            prices,
            AlwaysLongStrategy(),
            10_000,
            CostModel(
                courtage_fixed=0.0, courtage_percent=0.0, courtage_min=50.0, slippage_percent=0.0
            ),
        ).run()
        assert priced.equity_curve.iloc[-1] < free.equity_curve.iloc[-1]

    def test_round_trip_pnl_and_win_rate(self) -> None:
        # In dag 1 (open 100), ut dag 3 (open 130): vinst -> win rate 1.0.
        class InThenOut(Strategy):
            name = "in-ut (test)"

            def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
                bars = len(next(iter(history.values())))
                return {t: (1 if bars < 3 else 0) for t in history}

        prices = {"A": _prices([100, 100, 120, 130, 130], opens=[100, 100, 110, 130, 130])}
        result = BacktestEngine(prices, InThenOut(), 10_000, ZERO_COSTS).run()
        assert len(result.trades) == 2
        assert result.metrics["antal_affarer"] == 1.0
        assert result.metrics["win_rate"] == 1.0
        assert not any("öppna" in w for w in result.warnings)


class TestMetrics:
    def test_benchmark_comparison(self) -> None:
        equity = pd.Series([100.0, 110.0, 121.0], index=pd.date_range("2024-01-01", periods=3))
        bench = pd.Series([100.0, 105.0, 110.25], index=equity.index)
        metrics, _ = compute_metrics(equity, [1.0], benchmark_equity=bench)
        assert metrics["total_avkastning"] == pytest.approx(0.21)
        assert metrics["benchmark_avkastning"] == pytest.approx(0.1025)
        assert metrics["overavkastning_mot_index"] == pytest.approx(0.1075)

    def test_missing_benchmark_warns(self) -> None:
        equity = pd.Series([100.0, 101.0], index=pd.date_range("2024-01-01", periods=2))
        _, warnings = compute_metrics(equity, [1.0] * 20)
        assert any("Benchmark" in w for w in warnings)

    def test_few_trades_warns(self) -> None:
        equity = pd.Series([100.0, 101.0], index=pd.date_range("2024-01-01", periods=2))
        _, warnings = compute_metrics(equity, [1.0, -1.0])
        assert any("statistiskt" in w for w in warnings)

    def test_max_drawdown_in_metrics(self) -> None:
        equity = pd.Series([100.0, 120.0, 90.0], index=pd.date_range("2024-01-01", periods=3))
        metrics, _ = compute_metrics(equity, [])
        assert metrics["max_drawdown"] == pytest.approx(-0.25)

    def test_win_rate_nan_without_trades(self) -> None:
        equity = pd.Series([100.0, 101.0], index=pd.date_range("2024-01-01", periods=2))
        metrics, warnings = compute_metrics(equity, [])
        assert math.isnan(metrics["win_rate"])
        assert any("inga avslutade affärer" in w for w in warnings)


class TestExampleStrategies:
    def test_sma_crossover_goes_long_in_uptrend(self) -> None:
        closes = [100.0 + i for i in range(30)]
        strategy = SmaCrossoverStrategy(fast=3, slow=10)
        signals = strategy.generate_signals({"A": _prices(closes)})
        assert signals["A"] == 1

    def test_sma_crossover_flat_when_history_too_short(self) -> None:
        strategy = SmaCrossoverStrategy(fast=3, slow=10)
        assert strategy.generate_signals({"A": _prices([100.0] * 5)})["A"] == 0

    def test_rsi_strategy_buys_oversold_and_exits_after_recovery(self) -> None:
        strategy = RsiMeanReversionStrategy(period=3, buy_below=30, exit_above=55)
        falling = [100.0 - 3 * i for i in range(10)]
        assert strategy.generate_signals({"A": _prices(falling)})["A"] == 1
        recovered = falling + [falling[-1] + 5 * i for i in range(1, 8)]
        assert strategy.generate_signals({"A": _prices(recovered)})["A"] == 0

    def test_bollinger_strategy_signal_range(self) -> None:
        closes = [100 + (i % 7) - 3 for i in range(60)]
        signals = BollingerReversionStrategy(period=20).generate_signals(
            {"A": _prices([float(c) for c in closes])}
        )
        assert signals["A"] in (0, 1)

    def test_invalid_parameters_rejected(self) -> None:
        with pytest.raises(ValueError):
            SmaCrossoverStrategy(fast=200, slow=50)
        with pytest.raises(ValueError):
            RsiMeanReversionStrategy(buy_below=60, exit_above=50)


class TestMaxLookback:
    def test_engine_passes_only_tail_when_lookback_set(self) -> None:
        class TailSpy(Strategy):
            name = "svansspion (test)"
            max_lookback = 5

            def __init__(self) -> None:
                self.seen_lengths: list[int] = []
                self.last_dates: list[pd.Timestamp] = []

            def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
                frame = history["A"]
                self.seen_lengths.append(len(frame))
                self.last_dates.append(frame.index.max())
                return {"A": 0}

        prices = {"A": _prices([100.0 + i for i in range(20)])}
        spy = TailSpy()
        BacktestEngine(prices, spy, cost_model=ZERO_COSTS).run()
        assert max(spy.seen_lengths) == 5  # aldrig mer än lookback
        # Sista baren i slicen är fortfarande "idag" — inget lookahead.
        assert spy.last_dates == list(prices["A"].index)

    def test_sma_strategy_identical_with_and_without_lookback(self) -> None:
        closes = [100.0 + np.sin(i / 7) * 10 + i * 0.05 for i in range(120)]
        prices = {"A": _prices(closes)}

        limited = SmaCrossoverStrategy(fast=5, slow=20)
        unlimited = SmaCrossoverStrategy(fast=5, slow=20)
        unlimited.max_lookback = None

        result_limited = BacktestEngine(prices, limited, 10_000, ZERO_COSTS).run()
        result_unlimited = BacktestEngine(prices, unlimited, 10_000, ZERO_COSTS).run()
        # SMA behöver bara `slow` barer: resultaten ska vara identiska.
        pd.testing.assert_series_equal(result_limited.equity_curve, result_unlimited.equity_curve)
        assert len(result_limited.trades) == len(result_unlimited.trades)


class TestEngineValidation:
    def test_empty_prices_rejected(self) -> None:
        with pytest.raises(ValueError):
            BacktestEngine({}, AlwaysLongStrategy())

    def test_invalid_signal_rejected(self) -> None:
        class BadStrategy(Strategy):
            name = "trasig (test)"

            def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
                return {t: 2 for t in history}

        with pytest.raises(ValueError, match="ogiltig signal"):
            BacktestEngine({"A": _prices([100.0] * 3)}, BadStrategy(), cost_model=ZERO_COSTS).run()

    def test_missing_columns_rejected(self) -> None:
        frame = pd.DataFrame({"close": [1.0, 2.0]}, index=pd.date_range("2024-01-01", periods=2))
        with pytest.raises(ValueError, match="saknar kolumner"):
            BacktestEngine({"A": frame}, AlwaysLongStrategy())
