"""Exempelstrategier — referensimplementationer av Strategy-interfacet.

Dessa är avsiktligt enkla och INTE rekommendationer. De finns för att
testa motorn och visa hur egna strategier skrivs.
"""

from __future__ import annotations

import pandas as pd

from src.backtesting.strategy import Strategy
from src.indicators.technical import bollinger_bands, rsi, sma


class SmaCrossoverStrategy(Strategy):
    """Trendföljande: äg när snabbt SMA ligger över långsamt SMA.

    Klassisk "golden cross"-logik. Signal 1 när SMA(fast) > SMA(slow),
    annars 0. Kräver minst ``slow`` datapunkter, annars signal 0.
    """

    def __init__(self, fast: int = 50, slow: int = 200) -> None:
        if fast >= slow:
            raise ValueError(f"fast ({fast}) måste vara mindre än slow ({slow}).")
        self._fast = fast
        self._slow = slow
        self.name = f"SMA-korsning {fast}/{slow}"
        # SMA behöver exakt `slow` barer — mer historik ändrar inget.
        self.max_lookback = slow + 5

    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        """Se :meth:`Strategy.generate_signals`."""
        signals: dict[str, int] = {}
        for ticker, frame in history.items():
            close = frame["close"]
            if len(close) < self._slow:
                signals[ticker] = 0
                continue
            fast_now = float(sma(close, self._fast).iloc[-1])
            slow_now = float(sma(close, self._slow).iloc[-1])
            signals[ticker] = 1 if fast_now > slow_now else 0
        return signals


class RsiMeanReversionStrategy(Strategy):
    """Kontratrend: köp vid översålt RSI, sälj när RSI återhämtat sig.

    Signalen har hysteres: köpläge inleds när RSI < ``buy_below`` och
    varar tills RSI > ``exit_above``. Tillståndet härleds deterministiskt
    ur historiken vid varje anrop (ingen intern mutation).

    Av prestandaskäl beräknas tillstånd och RSI över ett rullande fönster
    om ``max_lookback`` barer (minst 20× perioden) i stället för hela
    historiken — Wilders utjämning gör att äldre data har försumbar vikt,
    men i sällsynta fall (en position som hållits öppen längre än hela
    fönstret utan att RSI passerat säljnivån) kan tillståndet skilja sig
    från en full-historik-beräkning. Se ANTAGANDEN.md.
    """

    def __init__(self, period: int = 14, buy_below: float = 30.0, exit_above: float = 55.0) -> None:
        if buy_below >= exit_above:
            raise ValueError("buy_below måste vara mindre än exit_above.")
        self._period = period
        self._buy_below = buy_below
        self._exit_above = exit_above
        self.name = f"RSI mean reversion ({period}, {buy_below:.0f}/{exit_above:.0f})"
        self.max_lookback = max(20 * period, 300)

    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        """Se :meth:`Strategy.generate_signals`."""
        signals: dict[str, int] = {}
        for ticker, frame in history.items():
            close = frame["close"]
            if len(close) < self._period + 1:
                signals[ticker] = 0
                continue
            rsi_series = rsi(close, self._period).dropna()
            state = 0
            for value in rsi_series:
                if state == 0 and value < self._buy_below:
                    state = 1
                elif state == 1 and value > self._exit_above:
                    state = 0
            signals[ticker] = state
        return signals


class BollingerReversionStrategy(Strategy):
    """Kontratrend: köp under nedre Bollingerbandet, sälj över mittbandet."""

    def __init__(self, period: int = 20, num_std: float = 2.0) -> None:
        self._period = period
        self._num_std = num_std
        self.name = f"Bollinger-reversion ({period}, {num_std}σ)"
        # Rullande fönster av prestandaskäl — samma resonemang och
        # begränsning som för RSI-strategin (se dess docstring).
        self.max_lookback = max(20 * period, 300)

    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        """Se :meth:`Strategy.generate_signals`."""
        signals: dict[str, int] = {}
        for ticker, frame in history.items():
            close = frame["close"]
            if len(close) < self._period:
                signals[ticker] = 0
                continue
            bands = bollinger_bands(close, self._period, self._num_std)
            state = 0
            for price, lower, middle in zip(close, bands["lower"], bands["middle"], strict=True):
                if pd.isna(lower):
                    continue
                if state == 0 and price < lower:
                    state = 1
                elif state == 1 and price > middle:
                    state = 0
            signals[ticker] = state
        return signals


class TimeSeriesMomentumStrategy(Strategy):
    """Tidsseriemomentum: äg när avkastningen senaste N barer är positiv.

    Klassiskt "trend following" — den mest väldokumenterade långsiktiga
    faktorn i finanslitteraturen (Moskowitz/Ooi/Pedersen 2012 m.fl.).
    Standard 252/21 motsvarar akademiska "12-1": tolv månaders avkastning
    exklusive senaste månaden (som ofta mean-reverterar på kort sikt).

    Att faktorn är väldokumenterad historiskt är ingen garanti för att den
    fortsätter fungera — som allt annat här är detta en referens, inget råd.
    """

    def __init__(self, lookback_bars: int = 252, skip_bars: int = 21) -> None:
        """Skapar strategin.

        Args:
            lookback_bars: Mätperiodens längd i barer (252 ≈ 12 månader
                på dagsdata).
            skip_bars: Antal senaste barer som exkluderas ur mätningen
                (21 ≈ 1 månad). 0 = mät ända fram till idag.
        """
        if skip_bars < 0 or lookback_bars <= skip_bars:
            raise ValueError(
                f"lookback_bars ({lookback_bars}) måste vara större än skip_bars ({skip_bars}) >= 0."
            )
        self._lookback = lookback_bars
        self._skip = skip_bars
        self.name = f"Tidsseriemomentum ({lookback_bars}/{skip_bars})"
        # Behöver exakt lookback + 1 barer — mer historik ändrar inget.
        self.max_lookback = lookback_bars + 5

    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        """Se :meth:`Strategy.generate_signals`."""
        signals: dict[str, int] = {}
        for ticker, frame in history.items():
            close = frame["close"]
            if len(close) < self._lookback + 1:
                signals[ticker] = 0
                continue
            end = float(close.iloc[-1 - self._skip]) if self._skip else float(close.iloc[-1])
            start = float(close.iloc[-1 - self._lookback])
            signals[ticker] = 1 if start > 0 and end / start - 1.0 > 0 else 0
        return signals


#: Strategier som dashboarden erbjuder (namn -> fabrik med standardparametrar).
AVAILABLE_STRATEGIES = {
    "SMA-korsning": SmaCrossoverStrategy,
    "RSI mean reversion": RsiMeanReversionStrategy,
    "Bollinger-reversion": BollingerReversionStrategy,
    "Tidsseriemomentum": TimeSeriesMomentumStrategy,
}
