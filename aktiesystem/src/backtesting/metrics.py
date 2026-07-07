"""Nyckeltal för backtestresultat: avkastning, risk och affärsstatistik."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.risk.risk import TRADING_DAYS_PER_YEAR, max_drawdown


def _sharpe_ratio(daily: pd.Series, risk_free_rate: float) -> float:
    """Annualiserad Sharpe-kvot på dagliga avkastningar."""
    excess = daily - risk_free_rate / TRADING_DAYS_PER_YEAR
    std = float(excess.std())
    if std == 0 or np.isnan(std):
        # Ingen volatilitet: kvoten är odefinierad — redovisa ärligt.
        return float("inf") if float(excess.mean()) > 0 else 0.0
    return float(excess.mean() / std * np.sqrt(TRADING_DAYS_PER_YEAR))


def _sortino_ratio(daily: pd.Series, risk_free_rate: float) -> float:
    """Annualiserad Sortino-kvot (straffar bara nedsidesvolatilitet)."""
    excess = daily - risk_free_rate / TRADING_DAYS_PER_YEAR
    downside = excess.clip(upper=0.0)
    downside_deviation = float(np.sqrt((downside**2).mean()))
    if downside_deviation == 0 or np.isnan(downside_deviation):
        # Inga negativa dagar: kvoten är odefinierad — redovisa ärligt.
        return float("inf") if float(excess.mean()) > 0 else 0.0
    return float(excess.mean() / downside_deviation * np.sqrt(TRADING_DAYS_PER_YEAR))


def compute_metrics(
    equity: pd.Series,
    closed_pnls: list[float],
    risk_free_rate: float = 0.02,
    benchmark_equity: pd.Series | None = None,
) -> tuple[dict[str, float], list[str]]:
    """Beräknar nyckeltal för en equity-kurva och en lista realiserade affärer.

    Args:
        equity: Portföljvärde per handelsdag.
        closed_pnls: Realiserad vinst/förlust per avslutad affär (rundresa).
        risk_free_rate: Årlig riskfri ränta som decimal.
        benchmark_equity: Buy-and-hold-kurva för jämförelseindex, normerad
            till samma startkapital (eller None om index saknas).

    Returns:
        (metrics, warnings): nyckeltal samt varningar som UI alltid ska visa.
    """
    if len(equity) < 2:
        raise ValueError("Equity-kurvan måste ha minst två punkter.")
    daily = equity.pct_change().dropna()
    years = max(len(daily) / TRADING_DAYS_PER_YEAR, 1e-9)
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)

    wins = [p for p in closed_pnls if p > 0]
    losses = [p for p in closed_pnls if p <= 0]
    metrics: dict[str, float] = {
        "total_avkastning": total_return,
        "cagr": float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0),
        "sharpe": _sharpe_ratio(daily, risk_free_rate),
        "sortino": _sortino_ratio(daily, risk_free_rate),
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
