"""Sida: Portföljoptimering — efficient frontier och rebalansering."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.views.common import load_prices, show_missing
from src.portfolio.optimization import OptimizationResult, efficient_frontier, rebalancing_plan


def _frontier_chart(result: OptimizationResult) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[p.volatility for p in result.frontier],
            y=[p.expected_return for p in result.frontier],
            mode="lines+markers",
            name="Efficient frontier",
            hovertemplate="Vol %{x:.1%}, avkastning %{y:.1%}<extra></extra>",
        )
    )
    for point, label in [
        (result.min_volatility, "Lägst volatilitet"),
        (result.max_sharpe, "Högst Sharpe"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=[point.volatility],
                y=[point.expected_return],
                mode="markers+text",
                text=[label],
                textposition="top center",
                marker={"size": 12},
                name=label,
            )
        )
    fig.update_layout(
        xaxis_title="Volatilitet (årlig)",
        yaxis_title="Förväntad avkastning (historisk, årlig)",
        xaxis_tickformat=".0%",
        yaxis_tickformat=".0%",
        height=500,
    )
    return fig


def render(config: dict[str, Any]) -> None:
    """Ritar optimeringssidan."""
    st.title("Portföljoptimering")
    st.caption(
        "Modern portföljteori på historiska avkastningar. 'Förväntad avkastning' = "
        "historiskt snitt — inte en prognos. Optimala vikter är mycket känsliga för "
        "skattningsfel; se hela kurvan som en karta över avvägningar, inte ett facit."
    )
    watchlist: list[str] = config.get("watchlist", [])
    tickers = st.multiselect("Tillgångar (minst 2)", watchlist, default=watchlist[:4])
    if len(tickers) < 2:
        st.info("Välj minst två tillgångar.")
        return
    if not st.button("Beräkna efficient frontier", type="primary"):
        return

    closes: dict[str, pd.Series] = {}
    for ticker in tickers:
        prices = load_prices(ticker)
        if prices is None:
            show_missing("kursdata", ticker)
            return
        closes[ticker] = prices["close"]
    returns = pd.DataFrame(closes).dropna().pct_change().dropna()

    try:
        result = efficient_frontier(
            returns,
            n_points=int(config["portfolio"].get("frontier_points", 40)),
            risk_free_rate=float(config["risk"].get("risk_free_rate", 0.02)),
            allow_short=bool(config["portfolio"].get("allow_short", False)),
        )
    except (ValueError, RuntimeError) as exc:
        st.error(f"Optimeringen kunde inte genomföras: {exc}")
        return

    st.caption(
        f"Baserat på {len(returns)} dagars överlappande historik för {len(tickers)} tillgångar."
    )
    st.plotly_chart(_frontier_chart(result), width="stretch")

    st.subheader("Referensportföljernas vikter")
    st.caption("Två punkter på kurvan — inte rekommendationer. Vikter under 0,5 % visas som 0.")
    weights_frame = pd.DataFrame(
        {
            "Lägst volatilitet": result.min_volatility.weights,
            "Högst Sharpe (historiskt)": result.max_sharpe.weights,
        }
    ).map(lambda w: f"{w:.1%}" if w >= 0.005 else "0")
    st.dataframe(weights_frame)

    st.subheader("Rebalansering mot målvikter")
    st.caption(
        "Ange nuvarande värde per innehav så beräknas köp-/säljbelopp för att nå "
        "max-Sharpe-portföljens vikter. Courtage ingår inte i beloppen."
    )
    current: dict[str, float] = {}
    cols = st.columns(min(len(tickers), 4))
    for i, ticker in enumerate(tickers):
        current[ticker] = float(
            cols[i % len(cols)].number_input(
                f"Värde {ticker}", min_value=0.0, value=10_000.0, key=f"reb_{ticker}"
            )
        )
    try:
        plan = rebalancing_plan(current, result.max_sharpe.weights)
        styled = plan.copy()
        for column in ["nuvarande_vikt", "malvikt"]:
            styled[column] = styled[column].map("{:.1%}".format)
        for column in ["nuvarande_varde", "malvarde", "handla_for"]:
            styled[column] = styled[column].map("{:,.0f}".format)
        st.dataframe(styled, hide_index=True, width="stretch")
        st.caption("Positivt belopp i 'handla_for' = köp, negativt = sälj.")
    except ValueError as exc:
        st.warning(str(exc))
