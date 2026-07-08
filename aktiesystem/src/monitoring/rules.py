"""Larmregler för marknadsbevakningen.

VIKTIGT: ett larm är en INDIKATOROBSERVATION ("RSI gick under 30"), aldrig
en köp- eller säljrekommendation. Vad du gör med informationen är ditt
beslut — det står även i varje notis.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.indicators.technical import rsi, sma

#: Läggs sist i varje larmmeddelande.
DISCLAIMER_SUFFIX = "Observation, inget råd."


@dataclass(frozen=True)
class Alert:
    """Ett utlöst larm. ``alert_id`` är unikt per (ticker, regel, dag)."""

    alert_id: str
    ticker: str
    rule: str
    title: str
    message: str


def _crossed_below(series: pd.Series, level: float) -> bool:
    """Sant om serien gick från >= level till < level i sista steget."""
    if len(series) < 2 or series.iloc[-1] != series.iloc[-1]:
        return False
    return series.iloc[-2] >= level > series.iloc[-1]


def _crossed_above(series: pd.Series, level: float) -> bool:
    """Sant om serien gick från <= level till > level i sista steget."""
    if len(series) < 2 or series.iloc[-1] != series.iloc[-1]:
        return False
    return series.iloc[-2] <= level < series.iloc[-1]


def _rsi_alerts(ticker: str, prices: pd.DataFrame, rules: dict[str, Any]) -> list[Alert]:
    """RSI-korsningar under översåld-/över överköpt-nivå."""
    close = prices["close"]
    if len(close) < 16:
        return []
    rsi_series = rsi(close, 14)
    date = prices.index[-1].date().isoformat()
    value = float(rsi_series.iloc[-1])
    alerts = []
    oversold = rules.get("rsi_oversold")
    if oversold is not None and _crossed_below(rsi_series, float(oversold)):
        alerts.append(
            Alert(
                f"{ticker}|rsi_oversold|{date}",
                ticker,
                "rsi_oversold",
                f"{ticker}: RSI under {oversold:.0f}",
                f"RSI 14 är {value:.1f} och gick under din larmnivå {oversold:.0f} "
                f"({date}). Nivåer under 30 brukar kallas översålda. {DISCLAIMER_SUFFIX}",
            )
        )
    overbought = rules.get("rsi_overbought")
    if overbought is not None and _crossed_above(rsi_series, float(overbought)):
        alerts.append(
            Alert(
                f"{ticker}|rsi_overbought|{date}",
                ticker,
                "rsi_overbought",
                f"{ticker}: RSI över {overbought:.0f}",
                f"RSI 14 är {value:.1f} och gick över din larmnivå {overbought:.0f} "
                f"({date}). Nivåer över 70 brukar kallas överköpta. {DISCLAIMER_SUFFIX}",
            )
        )
    return alerts


def _sma_cross_alerts(ticker: str, prices: pd.DataFrame, rules: dict[str, Any]) -> list[Alert]:
    """Kursen korsar SMA 200 (upp eller ned)."""
    if not rules.get("sma_cross") or len(prices) < 201:
        return []
    close = prices["close"]
    sma_200 = sma(close, 200)
    distance = close - sma_200
    date = prices.index[-1].date().isoformat()
    if _crossed_above(distance, 0.0):
        direction, text = "upp", "uppåt genom"
    elif _crossed_below(distance, 0.0):
        direction, text = "ned", "nedåt genom"
    else:
        return []
    return [
        Alert(
            f"{ticker}|sma_cross_{direction}|{date}",
            ticker,
            "sma_cross",
            f"{ticker}: kursen korsade SMA 200",
            f"Stängningskursen {float(close.iloc[-1]):.2f} korsade {text} 200-dagars "
            f"glidande medelvärde {float(sma_200.iloc[-1]):.2f} ({date}). {DISCLAIMER_SUFFIX}",
        )
    ]


def _day_move_alerts(ticker: str, prices: pd.DataFrame, rules: dict[str, Any]) -> list[Alert]:
    """Dagsrörelse större än tröskeln (i procent)."""
    threshold = rules.get("day_move_percent")
    if threshold is None or len(prices) < 2:
        return []
    close = prices["close"]
    move = float(close.iloc[-1] / close.iloc[-2] - 1.0)
    if abs(move) < float(threshold) / 100.0:
        return []
    date = prices.index[-1].date().isoformat()
    return [
        Alert(
            f"{ticker}|day_move|{date}",
            ticker,
            "day_move",
            f"{ticker}: stor dagsrörelse ({move:+.1%})",
            f"Kursen rörde sig {move:+.1%} till {float(close.iloc[-1]):.2f} ({date}), "
            f"mer än din larmnivå ±{float(threshold):.1f} %. {DISCLAIMER_SUFFIX}",
        )
    ]


def sentiment_alert(
    ticker: str, mean_compound: float, headline_count: int, rules: dict[str, Any], date: str
) -> list[Alert]:
    """Larm när snittsentimentet i senaste nyheterna är starkt negativt/positivt.

    Kräver minst 3 rubriker — enstaka rubriker är för brusigt.
    """
    threshold = rules.get("sentiment_threshold")
    if threshold is None or headline_count < 3:
        return []
    level = float(threshold)
    if mean_compound <= -abs(level):
        tone = "negativt"
    elif mean_compound >= abs(level):
        tone = "positivt"
    else:
        return []
    return [
        Alert(
            f"{ticker}|sentiment_{tone}|{date}",
            ticker,
            "sentiment",
            f"{ticker}: starkt {tone} nyhetssentiment",
            f"Snittsentimentet i de {headline_count} senaste rubrikerna är "
            f"{mean_compound:+.2f} (skala -1 till +1). VADER-sentiment är en grov "
            f"approximation, särskilt för icke-engelska rubriker. {DISCLAIMER_SUFFIX}",
        )
    ]


def evaluate_price_rules(ticker: str, prices: pd.DataFrame, rules: dict[str, Any]) -> list[Alert]:
    """Utvärderar alla prisbaserade regler för en ticker.

    Args:
        ticker: Tickern som utvärderas.
        prices: OHLCV-frame, senaste bar sist.
        rules: ``monitoring.rules``-sektionen ur config.yaml.

    Returns:
        Utlösta larm (kan vara tom lista). Reglerna triggar bara på
        NYA korsningar/händelser i den senaste baren, inte på tillstånd
        som varat länge — det begränsar naturligt notisflödet.
    """
    alerts: list[Alert] = []
    alerts.extend(_rsi_alerts(ticker, prices, rules))
    alerts.extend(_sma_cross_alerts(ticker, prices, rules))
    alerts.extend(_day_move_alerts(ticker, prices, rules))
    return alerts
