"""Nyckeltal för backtestresultat: avkastning, risk och affärsstatistik."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.risk.risk import TRADING_DAYS_PER_YEAR, max_drawdown

#: Barer per år för vanliga intervall: dagsdata 252 handelsdagar; intradag
#: ≈ 252 dagar × antal barer per handelsdag (svensk börs ~8,5 h öppettid).
PERIODS_PER_YEAR = {"1d": 252.0, "1h": 252.0 * 8.5, "15m": 252.0 * 34.0}


def _sharpe_ratio(per_bar: pd.Series, risk_free_rate: float, periods_per_year: float) -> float:
    """Annualiserad Sharpe-kvot på avkastningar per bar."""
    excess = per_bar - risk_free_rate / periods_per_year
    std = float(excess.std())
    if std == 0 or np.isnan(std):
        # Ingen volatilitet: kvoten är odefinierad — redovisa ärligt.
        return float("inf") if float(excess.mean()) > 0 else 0.0
    return float(excess.mean() / std * np.sqrt(periods_per_year))


def _sortino_ratio(per_bar: pd.Series, risk_free_rate: float, periods_per_year: float) -> float:
    """Annualiserad Sortino-kvot (straffar bara nedsidesvolatilitet)."""
    excess = per_bar - risk_free_rate / periods_per_year
    downside = excess.clip(upper=0.0)
    downside_deviation = float(np.sqrt((downside**2).mean()))
    if downside_deviation == 0 or np.isnan(downside_deviation):
        # Inga negativa barer: kvoten är odefinierad — redovisa ärligt.
        return float("inf") if float(excess.mean()) > 0 else 0.0
    return float(excess.mean() / downside_deviation * np.sqrt(periods_per_year))


def compute_metrics(
    equity: pd.Series,
    closed_pnls: list[float],
    risk_free_rate: float = 0.02,
    benchmark_equity: pd.Series | None = None,
    periods_per_year: float = TRADING_DAYS_PER_YEAR,
) -> tuple[dict[str, float], list[str]]:
    """Beräknar nyckeltal för en equity-kurva och en lista realiserade affärer.

    Args:
        equity: Portföljvärde per bar (dag eller intradagsbar).
        closed_pnls: Realiserad vinst/förlust per avslutad affär (rundresa).
        risk_free_rate: Årlig riskfri ränta som decimal.
        benchmark_equity: Buy-and-hold-kurva för jämförelseindex, normerad
            till samma startkapital (eller None om index saknas).
        periods_per_year: Antal barer per år för annualisering — 252 för
            dagsdata; se PERIODS_PER_YEAR för intradagsintervall. Fel värde
            ger systematiskt fel Sharpe/Sortino/CAGR.

    Returns:
        (metrics, warnings): nyckeltal samt varningar som UI alltid ska visa.
    """
    if len(equity) < 2:
        raise ValueError("Equity-kurvan måste ha minst två punkter.")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year måste vara positivt.")
    per_bar = equity.pct_change().dropna()
    years = max(len(per_bar) / periods_per_year, 1e-9)
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)

    wins = [p for p in closed_pnls if p > 0]
    losses = [p for p in closed_pnls if p <= 0]
    metrics: dict[str, float] = {
        "total_avkastning": total_return,
        "cagr": float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0),
        "sharpe": _sharpe_ratio(per_bar, risk_free_rate, periods_per_year),
        "sortino": _sortino_ratio(per_bar, risk_free_rate, periods_per_year),
        "max_drawdown": max_drawdown(equity),
        "antal_affarer": float(len(closed_pnls)),
        "win_rate": float(len(wins) / len(closed_pnls)) if closed_pnls else float("nan"),
        "snittvinst": float(np.mean(wins)) if wins else float("nan"),
        "snittforlust": float(np.mean(losses)) if losses else float("nan"),
    }

    warnings: list[str] = []
    if benchmark_equity is not None and len(benchmark_equity) >= 2:
        bench_return = float(benchmark_equity.iloc[-1] / benchmark_equity.iloc[0] - 1.0)
        metrics["benchmark_avkastning"] = bench_return
        metrics["overavkastning_mot_index"] = total_return - bench_return
    else:
        warnings.append("Benchmarkdata saknas — ingen indexjämförelse kunde göras.")

    if not closed_pnls:
        warnings.append("Strategin genomförde inga avslutade affärer under perioden.")
    elif len(closed_pnls) < 10:
        warnings.append(
            f"Endast {len(closed_pnls)} avslutade affärer — resultatet har lågt "
            "statistiskt värde och kan bero på slump."
        )
    return metrics, warnings
