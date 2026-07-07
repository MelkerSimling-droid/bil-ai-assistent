"""Portföljoptimering enligt modern portföljteori (Markowitz).

Egen implementation med scipy.optimize i stället för PyPortfolioOpt för
att slippa tunga beroenden (cvxpy) — matematiken är densamma.

VIKTIGT: optimeringen bygger på HISTORISKA avkastningar och samvariationer.
Den säger inget säkert om framtiden, och "optimala" vikter är notoriskt
känsliga för skattningsfel i förväntad avkastning. Dashboarden visar därför
hela efficient frontier och avvägningar — inte en enskild "rätt" portfölj.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.risk.risk import TRADING_DAYS_PER_YEAR


@dataclass
class FrontierPoint:
    """En punkt på efficient frontier."""

    expected_return: float  # annualiserad
    volatility: float  # annualiserad
    weights: dict[str, float]


@dataclass
class OptimizationResult:
    """Efficient frontier plus två referensportföljer."""

    frontier: list[FrontierPoint]
    max_sharpe: FrontierPoint
    min_volatility: FrontierPoint
    tickers: list[str]


def _annualized_stats(returns: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Annualiserad förväntad avkastning (historiskt medel) och kovarians."""
    mean = returns.mean().to_numpy() * TRADING_DAYS_PER_YEAR
    covariance = returns.cov().to_numpy() * TRADING_DAYS_PER_YEAR
    return mean, covariance


def _portfolio_stats(
    weights: np.ndarray, mean: np.ndarray, covariance: np.ndarray
) -> tuple[float, float]:
    """(avkastning, volatilitet) för en viktvektor."""
    ret = float(weights @ mean)
    vol = float(np.sqrt(weights @ covariance @ weights))
    return ret, vol


def _solve(
    objective,
    n_assets: int,
    allow_short: bool,
    extra_constraints: list[dict] | None = None,
) -> np.ndarray:
    """Minimerar en målfunktion under summavillkor (och ev. long-only).

    Raises:
        RuntimeError: Om optimeraren inte konvergerar.
    """
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    constraints.extend(extra_constraints or [])
    bounds = None if allow_short else [(0.0, 1.0)] * n_assets
    result = minimize(
        objective,
        x0=np.full(n_assets, 1.0 / n_assets),
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 500},
    )
    if not result.success:
        raise RuntimeError(f"Optimeringen konvergerade inte: {result.message}")
    return result.x


def efficient_frontier(
    returns: pd.DataFrame,
    n_points: int = 40,
    risk_free_rate: float = 0.02,
    allow_short: bool = False,
) -> OptimizationResult:
    """Beräknar efficient frontier för en uppsättning tillgångar.

    Args:
        returns: Dagliga avkastningar, en kolumn per tillgång, utan NaN.
        n_points: Antal punkter längs frontier.
        risk_free_rate: Årlig riskfri ränta för Sharpe-beräkningen.
        allow_short: Om blankning (negativa vikter) tillåts.

    Returns:
        OptimizationResult med frontier samt max-Sharpe- och
        minsta-volatilitet-portföljerna.

    Raises:
        ValueError: Vid färre än två tillgångar eller för kort historik.
        RuntimeError: Om optimeringen misslyckas.
    """
    if returns.shape[1] < 2:
        raise ValueError("Minst två tillgångar krävs för portföljoptimering.")
    if len(returns) < 60:
        raise ValueError(f"Minst 60 dagars avkastningshistorik krävs, fick {len(returns)}.")
    if returns.isna().any().any():
        raise ValueError("Avkastningsdatan innehåller NaN — rensa den först.")

    tickers = list(returns.columns)
    mean, covariance = _annualized_stats(returns)
    n = len(tickers)

    def volatility(weights: np.ndarray) -> float:
        return float(np.sqrt(weights @ covariance @ weights))

    def negative_sharpe(weights: np.ndarray) -> float:
        ret, vol = _portfolio_stats(weights, mean, covariance)
        return -(ret - risk_free_rate) / vol if vol > 0 else 0.0

    def to_point(weights: np.ndarray) -> FrontierPoint:
        ret, vol = _portfolio_stats(weights, mean, covariance)
        return FrontierPoint(ret, vol, dict(zip(tickers, weights.round(6), strict=True)))

    min_vol_point = to_point(_solve(volatility, n, allow_short))
    max_sharpe_point = to_point(_solve(negative_sharpe, n, allow_short))

    # Frontier: minimera volatilitet för ett svep av målavkastningar.
    target_returns = np.linspace(min_vol_point.expected_return, float(mean.max()), n_points)
    frontier: list[FrontierPoint] = []
    for target in target_returns:
        constraint = {"type": "eq", "fun": lambda w, t=target: float(w @ mean) - t}
        try:
            weights = _solve(volatility, n, allow_short, [constraint])
        except RuntimeError:
            continue  # ouppnåelig målavkastning hoppas över, redovisas ej som punkt
        frontier.append(to_point(weights))

    if not frontier:
        raise RuntimeError("Ingen punkt på efficient frontier kunde beräknas.")
    return OptimizationResult(
        frontier=frontier,
        max_sharpe=max_sharpe_point,
        min_volatility=min_vol_point,
        tickers=tickers,
    )


def rebalancing_plan(
    current_values: dict[str, float], target_weights: dict[str, float]
) -> pd.DataFrame:
    """Beräknar köp-/säljbelopp för att nå målvikter.

    Args:
        current_values: Nuvarande marknadsvärde per ticker (0 för nya innehav).
        target_weights: Målvikter som decimaler; måste summera till ~1.

    Returns:
        DataFrame per ticker med nuvarande vikt, målvikt och belopp att
        köpa (positivt) eller sälja (negativt). Courtage ingår inte i
        beloppen — det redovisas i UI som en påminnelse.

    Raises:
        ValueError: Om målvikterna inte summerar till 1 eller är negativa.
    """
    weight_sum = sum(target_weights.values())
    if not np.isclose(weight_sum, 1.0, atol=0.01):
        raise ValueError(f"Målvikterna ska summera till 1, fick {weight_sum:.4f}.")
    if any(weight < 0 for weight in target_weights.values()):
        raise ValueError("Negativa målvikter stöds inte i rebalanseringen.")

    total = sum(current_values.values())
    if total <= 0:
        raise ValueError("Portföljens totala värde måste vara positivt.")
    tickers = sorted(set(current_values) | set(target_weights))
    rows = []
    for ticker in tickers:
        current = current_values.get(ticker, 0.0)
        target_weight = target_weights.get(ticker, 0.0)
        target_value = total * target_weight
        rows.append(
            {
                "ticker": ticker,
                "nuvarande_varde": current,
                "nuvarande_vikt": current / total,
                "malvikt": target_weight,
                "malvarde": target_value,
                "handla_for": target_value - current,
            }
        )
    return pd.DataFrame(rows)
