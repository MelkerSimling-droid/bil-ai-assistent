"""Sida: Aktieanalys — teknisk analys, fundamenta, DCF, sentiment, position sizing."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard.views.common import (
    get_service,
    load_fundamentals_dict,
    load_intraday,
    load_prices,
    show_missing,
)
from src.data_ingestion.base import DataSourceError, FundamentalData
from src.fundamentals.dcf import DCFAssumptions, dcf_valuation, sensitivity_table
from src.fundamentals.metrics import metrics_table, net_debt
from src.indicators.technical import compute_all, vwap
from src.risk.risk import position_size_fixed_risk
from src.sentiment.news_sentiment import DISCLAIMER as SENTIMENT_DISCLAIMER
from src.sentiment.news_sentiment import aggregate_sentiment, score_headlines


def _price_chart(ticker: str, indicators) -> go.Figure:
    """Kurs + SMA/Bollinger överst, RSI i mitten, MACD nederst."""
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03,
        subplot_titles=(ticker, "RSI 14", "MACD"),
    )
    fig.add_trace(go.Scatter(x=indicators.index, y=indicators["close"], name="Kurs"), 1, 1)
    for col, name in [("sma_50", "SMA 50"), ("sma_200", "SMA 200")]:
        if indicators[col].notna().any():
            fig.add_trace(go.Scatter(x=indicators.index, y=indicators[col], name=name), 1, 1)
    fig.add_trace(
        go.Scatter(
            x=indicators.index,
            y=indicators["bb_upper"],
            name="Bollinger övre",
            line={"dash": "dot", "width": 1},
        ),
        1,
        1,
    )
    fig.add_trace(
        go.Scatter(
            x=indicators.index,
            y=indicators["bb_lower"],
            name="Bollinger nedre",
            line={"dash": "dot", "width": 1},
        ),
        1,
        1,
    )
    fig.add_trace(go.Scatter(x=indicators.index, y=indicators["rsi_14"], name="RSI"), 2, 1)
    fig.add_hline(y=70, line_dash="dash", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", row=2, col=1)
    fig.add_trace(go.Scatter(x=indicators.index, y=indicators["macd"], name="MACD"), 3, 1)
    fig.add_trace(go.Scatter(x=indicators.index, y=indicators["signal"], name="Signal"), 3, 1)
    fig.update_layout(height=700, legend={"orientation": "h"})
    return fig


def _render_technical(ticker: str) -> None:
    prices = load_prices(ticker)
    if prices is None:
        show_missing("kursdata", ticker)
        return
    try:
        indicators = compute_all(prices)
    except ValueError as exc:
        st.error(f"Kunde inte beräkna indikatorer: {exc}")
        return
    st.plotly_chart(_price_chart(ticker, indicators), use_container_width=True)
    last = indicators.iloc[-1]
    st.caption(
        f"Senaste stängning {last['close']:.2f} ({indicators.index[-1].date()}). "
        f"RSI 14 är {last['rsi_14']:.0f} — under 30 brukar kallas översålt, över 70 "
        "överköpt (beskrivning av indikatorn, ingen rekommendation)."
    )
    _render_position_sizing(
        float(last["close"]), float(last["atr_14"]) if last["atr_14"] == last["atr_14"] else None
    )


def _render_position_sizing(price: float, atr_value: float | None) -> None:
    with st.expander("Position sizing-kalkylator (fast risk per affär)"):
        st.caption(
            "Räknar ut hur många aktier som kan köpas så att förlusten vid stop loss "
            "motsvarar vald andel av portföljen. Gap och slippage kan ge större förlust."
        )
        col1, col2, col3 = st.columns(3)
        portfolio = col1.number_input(
            "Portföljvärde", min_value=1000.0, value=100_000.0, step=1000.0
        )
        risk_pct = (
            col2.number_input("Risk per affär (%)", min_value=0.1, max_value=20.0, value=1.0) / 100
        )
        default_stop = round(price - 2 * atr_value, 2) if atr_value else round(price * 0.95, 2)
        stop = col3.number_input("Stop loss-kurs", min_value=0.01, value=max(default_stop, 0.01))
        if atr_value:
            st.caption(f"Förifylld stop = kurs − 2×ATR(14) = {default_stop:.2f}.")
        try:
            result = position_size_fixed_risk(portfolio, risk_pct, price, stop)
            st.write(
                f"**{result.shares} aktier** (positionsvärde {result.position_value:,.0f}, "
                f"risk {result.risk_amount:,.0f} om stoppen träffas exakt)."
            )
        except ValueError as exc:
            st.warning(str(exc))


def _render_intraday(ticker: str) -> None:
    """Intradagsvy: kurs + VWAP + volym för dagshandel."""
    st.caption(
        "Intradagsdata från Yahoo: 1h-barer ca 2 år bakåt, 15m-barer ca 60 dagar. "
        "Data är fördröjd (inte realtid) och cachas i upp till 1 timme. VWAP "
        "(volymvägt snittpris, återställs varje handelsdag) är intradagshandelns "
        "vanligaste referensnivå — en beskrivning av dagens handel, inget råd."
    )
    interval = st.radio("Barlängd", ["1h", "15m"], horizontal=True)
    frame = load_intraday(ticker, interval)
    if frame is None or len(frame) < 2:
        show_missing(f"intradagsdata ({interval})", ticker)
        return
    days = sorted({index.date() for index in frame.index}, reverse=True)
    shown_days = st.slider("Antal handelsdagar att visa", 1, min(len(days), 20), min(5, len(days)))
    selected = frame[frame.index.normalize().isin([pd.Timestamp(d) for d in days[:shown_days]])]
    vwap_series = vwap(selected["high"], selected["low"], selected["close"], selected["volume"])

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.05
    )
    fig.add_trace(go.Scatter(x=selected.index, y=selected["close"], name="Kurs"), 1, 1)
    fig.add_trace(
        go.Scatter(x=selected.index, y=vwap_series, name="VWAP", line={"dash": "dot"}), 1, 1
    )
    fig.add_trace(go.Bar(x=selected.index, y=selected["volume"], name="Volym"), 2, 1)
    fig.update_layout(height=550, legend={"orientation": "h"})
    fig.update_xaxes(rangebreaks=[{"pattern": "hour", "bounds": [18, 9]}])
    st.plotly_chart(fig, use_container_width=True)

    last = selected.iloc[-1]
    last_vwap = (
        float(vwap_series.iloc[-1]) if vwap_series.iloc[-1] == vwap_series.iloc[-1] else None
    )
    if last_vwap:
        relation = "över" if float(last["close"]) > last_vwap else "under"
        st.caption(
            f"Senaste bar ({selected.index[-1]:%Y-%m-%d %H:%M}): kurs {last['close']:.2f}, "
            f"{relation} dagens VWAP {last_vwap:.2f}."
        )


def _render_fundamentals(ticker: str) -> None:
    raw = load_fundamentals_dict(ticker)
    if raw is None:
        show_missing("fundamenta", ticker)
        return
    data = FundamentalData(**raw)
    st.caption(f"Källa: {data.source}, hämtat {data.fetched_at[:16]} (cachas lokalt).")
    st.dataframe(metrics_table(data), hide_index=True)
    _render_dcf(data)


def _render_dcf(data: FundamentalData) -> None:
    st.subheader("DCF-värdering")
    st.warning(
        "Resultatet är EXTREMT känsligt för antagandena nedan. Små ändringar i "
        "tillväxt eller diskonteringsränta ger stora skillnader i beräknat värde. "
        "Se känslighetstabellen och betrakta detta som ett resonemangsverktyg."
    )
    if data.free_cash_flow is None or data.free_cash_flow <= 0:
        st.info(
            "Data saknas eller är negativ: bolagets fria kassaflöde tillåter ingen "
            "meningsfull DCF-beräkning här."
        )
        return
    col1, col2, col3 = st.columns(3)
    growth = col1.slider("Årlig FCF-tillväxt (%)", -5.0, 25.0, 5.0, 0.5) / 100
    discount = col2.slider("Diskonteringsränta (%)", 4.0, 20.0, 9.0, 0.5) / 100
    terminal = col3.slider("Terminal tillväxt (%)", 0.0, 4.0, 2.0, 0.25) / 100
    try:
        assumptions = DCFAssumptions(growth, discount, terminal)
        debt = net_debt(data) or 0.0
        result = dcf_valuation(data.free_cash_flow, assumptions, debt, data.shares_outstanding)
    except ValueError as exc:
        st.warning(str(exc))
        return
    if net_debt(data) is None:
        st.caption("Obs: nettoskuld kunde inte beräknas (data saknas) och sattes till 0.")
    if result.value_per_share is not None:
        st.metric(
            "Beräknat värde per aktie", f"{result.value_per_share:,.2f} {data.currency or ''}"
        )
    else:
        st.metric("Beräknat equity-värde", f"{result.equity_value:,.0f}")
        st.caption("Antal aktier saknas hos källan — värde per aktie kan inte beräknas.")
    st.markdown("**Känslighetstabell** (värde per aktie vid andra antaganden):")
    st.dataframe(
        sensitivity_table(data.free_cash_flow, assumptions, debt, data.shares_outstanding).round(2)
    )


def _render_sentiment(ticker: str, config: dict[str, Any]) -> None:
    st.subheader("Nyhetssentiment")
    st.warning(SENTIMENT_DISCLAIMER)
    try:
        news = get_service().get_news(ticker, limit=int(config["sentiment"]["max_headlines"]))
    except DataSourceError:
        show_missing("nyheter", ticker)
        return
    if not news:
        st.info(f"Inga nyhetsrubriker hittades för {ticker}.")
        return
    scored = score_headlines(news)
    aggregated = aggregate_sentiment(scored)
    st.dataframe(aggregated, hide_index=True)
    with st.expander(f"Alla {len(scored)} rubriker"):
        for headline in scored:
            st.markdown(
                f"- **[{headline.label}]** {headline.title} "
                f"({headline.publisher or 'okänd källa'}, poäng {headline.compound:+.2f})"
            )


def render(config: dict[str, Any]) -> None:
    """Ritar aktieanalyssidan."""
    st.title("Aktieanalys")
    watchlist: list[str] = config.get("watchlist", [])
    col1, col2 = st.columns([2, 3])
    choice = col1.selectbox("Välj från bevakningslistan", ["(egen ticker)"] + watchlist)
    custom = col2.text_input("... eller ange ticker (Yahoo-format, t.ex. VOLV-B.ST)")
    ticker = (
        custom.strip().upper() if custom.strip() else (choice if choice != "(egen ticker)" else "")
    )
    if not ticker:
        st.info("Välj eller ange en ticker för att börja.")
        return

    tab_ta, tab_intra, tab_fund, tab_news = st.tabs(
        ["Teknisk analys", "Intradag", "Fundamenta & DCF", "Sentiment"]
    )
    with tab_ta:
        _render_technical(ticker)
    with tab_intra:
        _render_intraday(ticker)
    with tab_fund:
        _render_fundamentals(ticker)
    with tab_news:
        _render_sentiment(ticker, config)
