"""Riskhantering: position sizing, volatilitet, korrelation, drawdown, VaR.

Alla mått är beskrivande statistik över historisk data — de förutsäger
inte framtiden. Dashboarden förklarar varje mått i klartext.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class PositionSize:
    """Resultat av en position sizing-beräkning."""

    shares: int
    position_value: float
    risk_amount: float
    risk_per_share: float


def position_size_fixed_risk(
    portfolio_value: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float,
) -> PositionSize:
    """Position sizing med fast riskbelopp per affär.

    Antal aktier = (portföljvärde × risk per affär) / (entry − stop loss).
    Tanken: om stop lossen träffas förloras högst ``risk_per_trade`` av
    portföljen (exklusive slippage/gap — verkliga förluster kan bli större).

    Args:
        portfolio_value: Totalt portföljvärde.
        risk_per_trade: Andel av portföljen som riskeras (0.01 = 1 %).
        entry_price: Tänkt köpkurs.
        stop_loss_price: Kurs där positionen stängs (< entry_price).

    Returns:
        PositionSize med antal aktier (heltal, avrundat nedåt).

    Raises:
        ValueError: Vid ogiltiga priser eller riskandel.
    """
    if portfolio_value <= 0:
        raise ValueError("Portföljvärdet måste vara positivt.")
    if not 0 < risk_per_trade <= 0.2:
        raise ValueError("risk_per_trade ska vara mellan 0 och 0.2 (20 %).")
    if entry_price <= 0:
        raise ValueError("Entrypriset måste vara positivt.")
    if stop_loss_price >= entry_price:
        raise ValueError(
            "Stop loss måste ligga under entrypriset för en lång position "
            f"(entry {entry_price}, stop {stop_loss_price})."
        )
    risk_amount = portfolio_value * risk_per_trade
    risk_per_share = entry_price - stop_loss_price
    shares = int(risk_amount / risk_per_share)
    # Begränsa så positionen aldrig överstiger portföljvärdet (belåning stöds ej).
    max_affordable = int(portfolio_value / entry_price)
    shares = min(shares, max_affordable)
    return PositionSize(
        shares=shares,
        position_value=shares * entry_price,
        risk_amount=shares * risk_per_share,
        risk_per_share=risk_per_share,
    )


def daily_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Enkla dagliga avkastningar från stängningskurser.

    Args:
        prices: Serie eller frame (en kolumn per tillgång) med kurser.

    Returns:
        Avkastningar; första raden faller bort.
    """
    if len(prices) < 2:
        raise ValueError("Minst två kurspunkter krävs för avkastningar.")
    return prices.pct_change().dropna(how="all")


def portfolio_volatility(returns: pd.DataFrame, weights: np.ndarray) -> float:
    """Årlig portföljvolatilitet: sqrt(wᵀ Σ w) × sqrt(252).

    Args:
        returns: Dagliga avkastningar, en kolumn per tillgång.
        weights: Vikter i samma kolumnordning; ska summera till ~1.

    Returns:
        Annualiserad volatilitet som decimal (0.20 = 20 %).
    """
    if returns.shape[1] != len(weights):
        raise ValueError(
            f"Antal vikter ({len(weights)}) matchar inte antal tillgångar ({returns.shape[1]})."
        )
    if not np.isclose(float(np.sum(weights)), 1.0, atol=0.01):
        raise ValueError(f"Vikterna ska summera till 1, fick {np.sum(weights):.4f}.")
    covariance = returns.cov().to_numpy() * TRADING_DAYS_PER_YEAR
    return float(np.sqrt(weights @ covariance @ weights))


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Korrelationsmatris mellan tillgångarnas dagliga avkastningar."""
    if returns.shape[1] < 2:
        raise ValueError("Minst två tillgångar krävs för en korrelationsmatris.")
    return returns.corr()


def max_drawdown(equity: pd.Series) -> float:
    """Största procentuella fall från en tidigare topp.

    Args:
        equity: Portfölj- eller kursvärde över tid.

    Returns:
        Max drawdown som negativ decimal (−0.25 = −25 %).
    """
    if len(equity) < 2:
        raise ValueError("Minst två punkter krävs för drawdown.")
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return float(drawdown.min())


def drawdown_series(equity: pd.Series) -> pd.Series:
    """Drawdown vid varje tidpunkt (0 vid ny topp, negativt annars)."""
    return (equity / equity.cummax() - 1.0).rename("drawdown")


def historical_var(
    returns: pd.Series, confidence: float = 0.95, portfolio_value: float = 1.0
) -> float:
    """Value at Risk via historisk simulering (empirisk kvantil).

    "Med `confidence` sannolikhet förlorar portföljen inte mer än detta
    på en dag, OM framtiden liknar den historiska perioden" — vilket den
    inte alltid gör; det är metodens kända svaghet.

    Args:
        returns: Dagliga portföljavkastningar.
        confidence: Konfidensnivå, t.ex. 0.95.
        portfolio_value: Skalar VaR till belopp; 1.0 ger andel.

    Returns:
        VaR som positivt tal (förlustbelopp).
    """
    if not 0.5 < confidence < 1.0:
        raise ValueError("Konfidensnivån ska ligga mellan 0.5 och 1.0.")
    if len(returns) < 30:
        raise ValueError(f"Minst 30 observationer krävs för meningsfull VaR, fick {len(returns)}.")
    quantile = float(np.quantile(returns.dropna(), 1.0 - confidence))
    return max(0.0, -quantile) * portfolio_value
