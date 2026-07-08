"""Scorecard: en kompakt lägesbild per aktie, i klartext.

Syftet är att samla de vanligaste indikatorobservationerna på ett ställe
så att användaren slipper leta — men varje fält är en BESKRIVNING av
historisk data, inte en prognos eller rekommendation. Saknas underlag för
ett fält blir det None och visas som "data saknas".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.indicators.technical import macd, rsi, sma
from src.risk.risk import TRADING_DAYS_PER_YEAR

#: Ungefär ett handelsår — används för 52-veckorsnivåerna.
_TRADING_DAYS_52W = 252


@dataclass(frozen=True)
class Scorecard:
    """Lägesbild för en ticker. None = underlag saknas (visas öppet)."""

    ticker: str
    data_date: str
    last_close: float
    day_change: float | None  # decimal, t.ex. -0.012
    trend_label: str
    rsi_value: float | None
    rsi_label: str
    macd_label: str
    dist_from_52w_high: float | None  # decimal <= 0
    dist_from_52w_low: float | None  # decimal >= 0
    volatility_annual: float | None


def _trend_label(close: pd.Series) -> str:
    """Trendbeskrivning utifrån kursens läge mot SMA 50 och SMA 200."""
    if len(close) < 200:
        return "för kort historik för trendbedömning"
    price = float(close.iloc[-1])
    sma_50 = float(sma(close, 50).iloc[-1])
    sma_200 = float(sma(close, 200).iloc[-1])
    if price > sma_50 > sma_200:
        return "upptrend (kurs > SMA50 > SMA200)"
    if price < sma_50 < sma_200:
        return "nedtrend (kurs < SMA50 < SMA200)"
    return "blandad (kursen ligger mellan medelvärdena)"


def _rsi_fields(close: pd.Series) -> tuple[float | None, str]:
    """RSI-värde och klartextetikett enligt 30/70-konventionen."""
    if len(close) < 15:
        return None, "för kort historik"
    value = float(rsi(close, 14).iloc[-1])
    if value != value:
        return None, "för kort historik"
    if value < 30:
        label = "under 30 — brukar kallas översålt"
    elif value > 70:
        label = "över 70 — brukar kallas överköpt"
    else:
        label = "neutralt område (30–70)"
    return value, label


def _macd_label(close: pd.Series) -> str:
    """Beskriver MACD-histogrammets tecken och riktning."""
    if len(close) < 40:
        return "för kort historik"
    histogram = macd(close)["histogram"].dropna()
    if len(histogram) < 2:
        return "för kort historik"
    now, previous = float(histogram.iloc[-1]), float(histogram.iloc[-2])
    sign = "positivt" if now > 0 else "negativt"
    direction = "stigande" if now > previous else "fallande"
    return f"{sign} och {direction}"


def build_scorecard(ticker: str, prices: pd.DataFrame) -> Scorecard:
    """Bygger en lägesbild från daglig kurshistorik.

    Args:
        ticker: Tickern lägesbilden gäller.
        prices: Daglig OHLCV-frame, senaste dag sist.

    Returns:
        Scorecard där fält utan tillräckligt underlag är None/förklarade.

    Raises:
        ValueError: Om prisdatan är tom eller saknar close-kolumn.
    """
    if prices is None or prices.empty or "close" not in prices.columns:
        raise ValueError(f"{ticker}: användbar kurshistorik saknas.")
    close = prices["close"].dropna()
    if close.empty:
        raise ValueError(f"{ticker}: inga stängningskurser.")
    last = float(close.iloc[-1])

    day_change = float(close.iloc[-1] / close.iloc[-2] - 1.0) if len(close) >= 2 else None
    year = close.tail(_TRADING_DAYS_52W)
    high_52w, low_52w = float(year.max()), float(year.min())
    returns = close.pct_change().dropna()
    volatility = (
        float(returns.tail(_TRADING_DAYS_52W).std() * np.sqrt(TRADING_DAYS_PER_YEAR))
        if len(returns) >= 30
        else None
    )
    rsi_value, rsi_text = _rsi_fields(close)
    return Scorecard(
        ticker=ticker,
        data_date=close.index[-1].date().isoformat(),
        last_close=last,
        day_change=day_change,
        trend_label=_trend_label(close),
        rsi_value=rsi_value,
        rsi_label=rsi_text,
        macd_label=_macd_label(close),
        dist_from_52w_high=(last / high_52w - 1.0) if high_52w > 0 else None,
        dist_from_52w_low=(last / low_52w - 1.0) if low_52w > 0 else None,
        volatility_annual=volatility,
    )


def scorecards_table(cards: list[Scorecard]) -> pd.DataFrame:
    """Gör en visningsvänlig tabell av en lista lägesbilder."""

    def pct(value: float | None) -> str:
        return "data saknas" if value is None else f"{value:+.1%}"

    rows = []
    for card in cards:
        rows.append(
            {
                "Ticker": card.ticker,
                "Kurs": round(card.last_close, 2),
                "Idag": pct(card.day_change),
                "Trend": card.trend_label,
                "RSI 14": "data saknas" if card.rsi_value is None else f"{card.rsi_value:.0f}",
                "RSI-läge": card.rsi_label,
                "MACD-histogram": card.macd_label,
                "Från 52v-högsta": pct(card.dist_from_52w_high),
                "Från 52v-lägsta": pct(card.dist_from_52w_low),
                "Volatilitet (år)": (
                    "data saknas"
                    if card.volatility_annual is None
                    else f"{card.volatility_annual:.0%}"
                ),
                "Kursdatum": card.data_date,
            }
        )
    return pd.DataFrame(rows)
