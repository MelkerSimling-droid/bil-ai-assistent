"""Sida: Översikt — portföljvärde i basvalutan, dagens förändring och portföljrisk."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.views.common import load_fundamentals_dict, load_fx_rate, load_prices, show_missing
from src.risk.risk import correlation_matrix, historical_var, max_drawdown, portfolio_volatility


def _holding_currency(ticker: str) -> str | None:
    """Innehavets valuta enligt källans fundamenta, eller None om okänd."""
    fundamentals = load_fundamentals_dict(ticker)
    if fundamentals is None:
        return None
    return fundamentals.get("currency")


def _holdings_table(
    holdings: dict[str, float], base_currency: str
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], list[str]]:
    """Bygger innehavstabellen omräknad till basvalutan.

    Returns:
        (tabell, prisdata per ticker, tickers som exkluderats för att
        valuta eller växelkurs saknas — de gissas aldrig in i summan).
    """
    rows = []
    price_data: dict[str, pd.DataFrame] = {}
    excluded: list[str] = []
    for ticker, shares in holdings.items():
        prices = load_prices(ticker)
        if prices is None or len(prices) < 2:
            show_missing("kursdata", ticker)
            continue
        currency = _holding_currency(ticker)
        if currency is None:
            excluded.append(f"{ticker} (valuta okänd)")
            continue
        fx = load_fx_rate(currency, base_currency)
        if fx is None:
            excluded.append(f"{ticker} (växelkurs {currency}→{base_currency} saknas)")
            continue
        rate, _rate_date = fx
        price_data[ticker] = prices
        last, prev = float(prices["close"].iloc[-1]), float(prices["close"].iloc[-2])
        rows.append(
            {
                "Ticker": ticker,
                "Antal": shares,
                "Senaste kurs": round(last, 2),
                "Valuta": currency,
                "Växelkurs": round(rate, 4),
                "Värde": round(shares * last * rate, 0),
                "Dagens förändring": f"{(last / prev - 1):+.2%}",
                "Kursdatum": prices.index[-1].date().isoformat(),
            }
        )
    return pd.DataFrame(rows), price_data, excluded


def _render_risk_section(
    table: pd.DataFrame, price_data: dict[str, pd.DataFrame], config: dict[str, Any]
) -> None:
    """Portföljens riskmått med förklaringar i klartext."""
    st.subheader("Portföljrisk")
    st.caption("Beskrivande statistik över historisk data — säger inget säkert om framtiden.")
    closes = pd.DataFrame({t: f["close"] for t, f in price_data.items()}).dropna()
    if len(closes) < 60 or closes.shape[1] < 1:
        st.warning("För lite överlappande kurshistorik för att beräkna riskmått.")
        return
    returns = closes.pct_change().dropna()
    values = table.set_index("Ticker")["Värde"]
    weights = (values / values.sum()).reindex(closes.columns).to_numpy()
    portfolio_returns = (returns * weights).sum(axis=1)
    portfolio_value = float(values.sum())
    confidence = float(config["risk"].get("var_confidence", 0.95))

    col1, col2, col3 = st.columns(3)
    col1.metric("Volatilitet (årlig)", f"{portfolio_volatility(returns, weights):.1%}")
    col1.caption("Hur mycket portföljvärdet historiskt svängt på årsbasis.")
    equity = (1 + portfolio_returns).cumprod()
    col2.metric("Max drawdown (perioden)", f"{max_drawdown(equity):.1%}")
    col2.caption("Största historiska fallet från topp till botten med dagens vikter.")
    var = historical_var(portfolio_returns, confidence, portfolio_value)
    col3.metric(f"VaR ({confidence:.0%}, 1 dag)", f"{var:,.0f}")
    col3.caption(
        f"Historiskt sett förlorade portföljen mer än så här {1 - confidence:.0%} av dagarna. "
        "Avkastningarna är i lokal valuta — valutarörelser ingår inte i måtten."
    )

    if closes.shape[1] >= 2:
        st.markdown(
            "**Korrelationsmatris** — nära 1 betyder att innehaven rör sig ihop "
            "(sämre riskspridning)."
        )
        st.dataframe(correlation_matrix(returns).round(2))


def render(config: dict[str, Any]) -> None:
    """Ritar översiktssidan."""
    st.title("Översikt")
    holdings: dict[str, float] = config.get("holdings") or {}
    base_currency = str(config.get("base_currency", "SEK")).upper()
    if not holdings:
        st.info(
            "Inga innehav konfigurerade. Lägg till dem under `holdings:` i "
            "config/config.yaml för att se din portfölj här."
        )
        return

    table, price_data, excluded = _holdings_table(holdings, base_currency)
    if excluded:
        st.warning(
            "Följande innehav ingår INTE i summorna (data saknas, gissas aldrig): "
            + ", ".join(excluded)
        )
    if table.empty:
        st.error("Ingen kursdata kunde hämtas för något innehav.")
        return

    total = float(table["Värde"].sum())
    rate_by_ticker = table.set_index("Ticker")["Växelkurs"]
    day_change = sum(
        holdings[ticker]
        * (float(frame["close"].iloc[-1]) - float(frame["close"].iloc[-2]))
        * float(rate_by_ticker[ticker])
        for ticker, frame in price_data.items()
    )
    col1, col2 = st.columns(2)
    col1.metric(f"Portföljvärde ({base_currency})", f"{total:,.0f}")
    col2.metric(
        "Dagens förändring", f"{day_change:+,.0f}", f"{day_change / (total - day_change):+.2%}"
    )
    st.caption(
        f"Alla värden omräknade till {base_currency} med senaste växelkurs från Yahoo "
        "(kolumnen Växelkurs). Värdering till senast tillgängliga stängningskurs per "
        "innehav (kolumnen Kursdatum)."
    )
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.divider()
    _render_risk_section(table, price_data, config)
