"""Event-driven backtestmotor.

Arkitekturen beskrivs i src/backtesting/README.md. Kärnprincipen:
signaler beräknas på dag T:s stängning och exekveras tidigast på dag
T+1:s öppningskurs — strategin får aldrig se data efter "nu".
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.backtesting.costs import CostModel
from src.backtesting.metrics import compute_metrics
from src.backtesting.strategy import Strategy
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class Trade:
    """En genomförd affär (en rad i affärsloggen)."""

    date: pd.Timestamp
    ticker: str
    side: str  # "köp" eller "sälj"
    shares: int
    price: float  # effektiv kurs inkl. slippage
    courtage: float


@dataclass
class BacktestResult:
    """Komplett resultat av ett backtest, med full spårbarhet."""

    strategy_name: str
    equity_curve: pd.Series
    drawdown_curve: pd.Series
    trades: pd.DataFrame
    metrics: dict[str, float]
    benchmark_equity: pd.Series | None
    warnings: list[str] = field(default_factory=list)


class BacktestEngine:
    """Kör en strategi mot historisk data, bar för bar."""

    def __init__(
        self,
        prices: dict[str, pd.DataFrame],
        strategy: Strategy,
        start_capital: float = 100_000.0,
        cost_model: CostModel | None = None,
        benchmark_close: pd.Series | None = None,
        risk_free_rate: float = 0.02,
        periods_per_year: float = 252.0,
    ) -> None:
        """Skapar motorn.

        Motorn är bar-agnostisk: den fungerar lika bra på dagsdata som på
        intradagsbarer (1h/15m) — "dag T+1:s öppning" betyder då "nästa
        bars öppning". Ange rätt ``periods_per_year`` för intradagsdata,
        annars blir Sharpe/Sortino/CAGR systematiskt fel.

        Args:
            prices: Per ticker: OHLCV-frame med DatetimeIndex (stigande).
            strategy: Strategi som implementerar Strategy-interfacet.
            start_capital: Startkapital.
            cost_model: Courtage-/slippagemodell (standard: CostModel()).
            benchmark_close: Stängningskurser för jämförelseindex (valfritt).
            risk_free_rate: Årlig riskfri ränta för Sharpe/Sortino.
            periods_per_year: Barer per år för annualisering (252 för
                dagsdata; se metrics.PERIODS_PER_YEAR för intradag).
        """
        if not prices:
            raise ValueError("Minst en ticker med prisdata krävs.")
        for ticker, frame in prices.items():
            missing = {"open", "close"} - set(frame.columns)
            if missing:
                raise ValueError(f"{ticker}: prisdata saknar kolumner {sorted(missing)}.")
            if not frame.index.is_monotonic_increasing:
                raise ValueError(f"{ticker}: prisdata måste vara sorterad på datum.")
        if start_capital <= 0:
            raise ValueError("Startkapitalet måste vara positivt.")
        self._prices = prices
        self._strategy = strategy
        self._start_capital = start_capital
        self._costs = cost_model or CostModel()
        self._benchmark_close = benchmark_close
        self._risk_free_rate = risk_free_rate
        self._periods_per_year = periods_per_year
        # Handelskalender = union av alla tickers datum.
        self._calendar = sorted(set().union(*(frame.index for frame in prices.values())))
        # Senast kända stängningskurs per ticker och kalenderdag (för värdering).
        self._marks = {
            ticker: frame["close"].reindex(self._calendar).ffill()
            for ticker, frame in prices.items()
        }

    def run(self) -> BacktestResult:
        """Kör backtestet över hela kalendern.

        Returns:
            BacktestResult med equity-kurva, affärslogg, nyckeltal,
            benchmarkjämförelse och eventuella varningar.
        """
        cash = self._start_capital
        positions: dict[str, int] = {ticker: 0 for ticker in self._prices}
        entry_costs: dict[str, float] = {}
        pending: dict[str, int] = {}
        equity_points: list[tuple[pd.Timestamp, float]] = []
        trades: list[Trade] = []
        closed_pnls: list[float] = []

        days_in_market = 0
        for today in self._calendar:
            cash = self._execute_pending(
                today, pending, positions, entry_costs, trades, closed_pnls, cash
            )
            equity = cash + sum(
                shares * self._mark_price(ticker, today)
                for ticker, shares in positions.items()
                if shares > 0
            )
            equity_points.append((today, equity))
            if any(shares > 0 for shares in positions.values()):
                days_in_market += 1
            signals = self._strategy.generate_signals(self._history_up_to(today))
            for ticker in self._prices:
                target = int(signals.get(ticker, 0))
                if target not in (0, 1):
                    raise ValueError(f"Strategin gav ogiltig signal {target} för {ticker}.")
                currently_long = positions[ticker] > 0
                if target == 1 and not currently_long or target == 0 and currently_long:
                    pending[ticker] = target
                else:
                    pending.pop(ticker, None)

        exposure = days_in_market / len(self._calendar) if self._calendar else 0.0
        return self._build_result(equity_points, trades, closed_pnls, exposure)

    def _history_up_to(self, today: pd.Timestamp) -> dict[str, pd.DataFrame]:
        """Historik t.o.m. idag — det enda strategin någonsin får se.

        Om strategin deklarerar ``max_lookback`` skickas bara de senaste
        så många barerna (fortfarande enbart data t.o.m. idag) — det gör
        långa intradagsbacktester dramatiskt snabbare utan lookahead-risk.
        """
        lookback = self._strategy.max_lookback
        history = {}
        for ticker, frame in self._prices.items():
            sliced = frame.loc[:today]
            history[ticker] = sliced.tail(lookback) if lookback else sliced
        return history

    def _mark_price(self, ticker: str, date: pd.Timestamp) -> float:
        """Senast kända stängningskurs t.o.m. ett datum (för värdering)."""
        value = self._marks[ticker].loc[date]
        return 0.0 if pd.isna(value) else float(value)

    def _execute_pending(
        self,
        today: pd.Timestamp,
        pending: dict[str, int],
        positions: dict[str, int],
        entry_costs: dict[str, float],
        trades: list[Trade],
        closed_pnls: list[float],
        cash: float,
    ) -> float:
        """Exekverar köade ordrar på dagens öppningskurs. Returnerar ny kassa."""
        for ticker in list(pending):
            frame = self._prices[ticker]
            if today not in frame.index or pd.isna(frame.at[today, "open"]):
                continue  # ingen bar idag — ordern ligger kvar till nästa bar
            target = pending.pop(ticker)
            open_price = float(frame.at[today, "open"])
            if target == 1 and positions[ticker] == 0:
                cash = self._buy(today, ticker, open_price, positions, entry_costs, trades, cash)
            elif target == 0 and positions[ticker] > 0:
                cash = self._sell(
                    today, ticker, open_price, positions, entry_costs, trades, closed_pnls, cash
                )
        return cash

    def _buy(
        self,
        date: pd.Timestamp,
        ticker: str,
        open_price: float,
        positions: dict[str, int],
        entry_costs: dict[str, float],
        trades: list[Trade],
        cash: float,
    ) -> float:
        """Köper för målvikten 1/N av aktuell equity, begränsat av kassan."""
        price = self._costs.buy_price(open_price)
        equity = cash + sum(
            shares * self._mark_price(tic, date) for tic, shares in positions.items() if shares > 0
        )
        budget = min(equity / len(self._prices), cash)
        shares = int(budget / price)
        # Se till att även courtaget ryms i kassan.
        while shares > 0 and shares * price + self._costs.courtage(shares * price) > cash:
            shares -= 1
        if shares <= 0:
            logger.debug("%s %s: kassan räcker inte till köp.", date.date(), ticker)
            return cash
        value = shares * price
        courtage = self._costs.courtage(value)
        positions[ticker] = shares
        entry_costs[ticker] = value + courtage
        trades.append(Trade(date, ticker, "köp", shares, price, courtage))
        return cash - value - courtage

    def _sell(
        self,
        date: pd.Timestamp,
        ticker: str,
        open_price: float,
        positions: dict[str, int],
        entry_costs: dict[str, float],
        trades: list[Trade],
        closed_pnls: list[float],
        cash: float,
    ) -> float:
        """Säljer hela innehavet och bokför realiserad vinst/förlust."""
        shares = positions[ticker]
        price = self._costs.sell_price(open_price)
        value = shares * price
        courtage = self._costs.courtage(value)
        closed_pnls.append(value - courtage - entry_costs.pop(ticker))
        positions[ticker] = 0
        trades.append(Trade(date, ticker, "sälj", shares, price, courtage))
        return cash + value - courtage

    def _build_result(
        self,
        equity_points: list[tuple[pd.Timestamp, float]],
        trades: list[Trade],
        closed_pnls: list[float],
        exposure: float,
    ) -> BacktestResult:
        """Sätter ihop resultatobjektet inklusive benchmark och varningar."""
        equity = pd.Series(
            [value for _, value in equity_points],
            index=pd.DatetimeIndex([date for date, _ in equity_points], name="date"),
            name="equity",
        )
        benchmark_equity = None
        if self._benchmark_close is not None and len(self._benchmark_close.dropna()) >= 2:
            bench = self._benchmark_close.reindex(equity.index).ffill().dropna()
            if len(bench) >= 2:
                benchmark_equity = (bench / bench.iloc[0] * self._start_capital).rename("benchmark")
        metrics, warnings = compute_metrics(
            equity,
            closed_pnls,
            self._risk_free_rate,
            benchmark_equity,
            periods_per_year=self._periods_per_year,
        )
        # Andel handelsdagar med minst en öppen position — utan detta är
        # avkastningsjämförelser mot ett alltid-investerat index missvisande.
        metrics["exponering"] = exposure
        open_positions = sum(1 for t in trades if t.side == "köp") - len(closed_pnls)
        if open_positions > 0:
            warnings.append(
                f"{open_positions} position(er) var fortfarande öppna vid periodens slut; "
                "deras orealiserade resultat ingår i equity men inte i win rate."
            )
        trade_frame = pd.DataFrame(
            [
                {
                    "datum": t.date,
                    "ticker": t.ticker,
                    "typ": t.side,
                    "antal": t.shares,
                    "kurs": t.price,
                    "courtage": t.courtage,
                }
                for t in trades
            ]
        )
        return BacktestResult(
            strategy_name=self._strategy.name,
            equity_curve=equity,
            drawdown_curve=(equity / equity.cummax() - 1.0).rename("drawdown"),
            trades=trade_frame,
            metrics=metrics,
            benchmark_equity=benchmark_equity,
            warnings=warnings,
        )
