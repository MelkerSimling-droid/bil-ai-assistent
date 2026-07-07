"""Sida: Backtesting — kör en strategi mot historisk data."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.views.common import load_prices, show_missing
from src.backtesting.costs import CostModel
from src.backtesting.engine import BacktestEngine, BacktestResult
from src.backtesting.strategies import (
    BollingerReversionStrategy,
    RsiMeanReversionStrategy,
    SmaCrossoverStrategy,
)
from src.backtesting.strategy import Strategy
from src.backtesting.validation import run_split_backtest

OVERFITTING_WARNING = (
    "**Overfittingrisk:** när du justerar parametrar tills historiken ser bra ut "
    "anpassar du strategin till brus i just den perioden. Ett bra backtestresultat "
    "efter många parameterförsök säger mycket lite om framtiden. Testa alltid på "
    "en annan tidsperiod/andra tickers än den du optimerade på."
)


def _build_strategy() -> Strategy | None:
    """Strategival + parameterinmatning. None tills valet är komplett."""
    kind = st.selectbox("Strategi", ["SMA-korsning", "RSI mean reversion", "Bollinger-reversion"])
    try:
        if kind == "SMA-korsning":
            col1, col2 = st.columns(2)
            fast = int(col1.number_input("Snabbt SMA", 2, 400, 50))
            slow = int(col2.number_input("Långsamt SMA", 3, 500, 200))
            return SmaCrossoverStrategy(fast, slow)
        if kind == "RSI mean reversion":
            col1, col2, col3 = st.columns(3)
            period = int(col1.number_input("RSI-period", 2, 50, 14))
            buy = float(col2.number_input("Köp under RSI", 5.0, 50.0, 30.0))
            exit_lvl = float(col3.number_input("Sälj över RSI", 30.0, 95.0, 55.0))
            return RsiMeanReversionStrategy(period, buy, exit_lvl)
        col1, col2 = st.columns(2)
        period = int(col1.number_input("Bollinger-period", 5, 100, 20))
        std = float(col2.number_input("Antal standardavvikelser", 0.5, 4.0, 2.0))
        return BollingerReversionStrategy(period, std)
    except ValueError as exc:
        st.warning(str(exc))
        return None


def _result_charts(result: BacktestResult) -> None:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=result.equity_curve.index, y=result.equity_curve, name="Strategi"))
    if result.benchmark_equity is not None:
        fig.add_trace(
            go.Scatter(
                x=result.benchmark_equity.index,
                y=result.benchmark_equity,
                name="Index (buy & hold)",
            )
        )
    fig.update_layout(title="Equity-kurva", height=400, legend={"orientation": "h"})
    st.plotly_chart(fig, use_container_width=True)

    dd = go.Figure(
        go.Scatter(
            x=result.drawdown_curve.index, y=result.drawdown_curve, fill="tozeroy", name="Drawdown"
        )
    )
    dd.update_layout(title="Drawdown", height=250, yaxis_tickformat=".0%")
    st.plotly_chart(dd, use_container_width=True)


def _metrics_row(metrics: dict[str, float]) -> None:
    def fmt(key: str, pct: bool = False) -> str:
        value = metrics.get(key)
        if value is None or value != value:
            return "–"
        return f"{value:.1%}" if pct else f"{value:.2f}"

    cols = st.columns(6)
    cols[0].metric("Total avkastning", fmt("total_avkastning", pct=True))
    cols[1].metric("CAGR", fmt("cagr", pct=True))
    cols[2].metric("Sharpe", fmt("sharpe"))
    cols[3].metric("Sortino", fmt("sortino"))
    cols[4].metric("Max drawdown", fmt("max_drawdown", pct=True))
    cols[5].metric("Win rate", fmt("win_rate", pct=True))
    if "benchmark_avkastning" in metrics:
        st.caption(
            f"Index (buy & hold) gav {metrics['benchmark_avkastning']:.1%} under samma period "
            f"— strategins överavkastning: {metrics['overavkastning_mot_index']:+.1%}. "
        )
    st.caption(
        "Sharpe/Sortino: riskjusterad avkastning (högre är bättre; Sortino straffar bara "
        "nedgångsdagar). Win rate: andel avslutade affärer med vinst. Alla siffror "
        "inkluderar courtage och slippage."
    )


def render(config: dict[str, Any]) -> None:
    """Ritar backtestsidan."""
    st.title("Backtesting")
    st.info(OVERFITTING_WARNING)

    watchlist: list[str] = config.get("watchlist", [])
    tickers = st.multiselect("Tickers", watchlist, default=watchlist[:2])
    strategy = _build_strategy()
    bt_cfg = config["backtest"]
    with st.expander("Kapital & kostnader (från config.yaml)"):
        start_capital = float(
            st.number_input("Startkapital", 1000.0, value=float(bt_cfg["start_capital"]))
        )
        cost_model = CostModel(
            courtage_fixed=float(bt_cfg["courtage_fixed"]),
            courtage_percent=float(bt_cfg["courtage_percent"]),
            courtage_min=float(bt_cfg["courtage_min"]),
            slippage_percent=float(bt_cfg["slippage_percent"]),
        )
        st.caption(
            f"Courtage: max({cost_model.courtage_min}, {cost_model.courtage_fixed} + "
            f"{cost_model.courtage_percent:.3%} × belopp), slippage {cost_model.slippage_percent:.3%}."
        )

    out_of_sample = st.checkbox(
        "Utvärdera robusthet out-of-sample (70/30-delning)",
        value=False,
        help=(
            "Kör strategin separat på de första 70 % av historiken (in-sample) och "
            "de sista 30 % (out-of-sample). Faller resultatet ihop i den senare "
            "perioden är parametrarna sannolikt anpassade till brus."
        ),
    )

    if not tickers or strategy is None or not st.button("Kör backtest", type="primary"):
        return

    prices: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        frame = load_prices(ticker)
        if frame is None:
            show_missing("kursdata", ticker)
            return
        prices[ticker] = frame

    benchmark_ticker = str(config.get("benchmark", ""))
    benchmark_close = None
    if benchmark_ticker:
        bench = load_prices(benchmark_ticker)
        if bench is not None:
            benchmark_close = bench["close"]
        else:
            st.warning(f"Benchmarkdata ({benchmark_ticker}) kunde inte hämtas — jämförelsen utgår.")

    risk_free = float(config["risk"].get("risk_free_rate", 0.02))
    if out_of_sample:
        _run_split(prices, strategy, start_capital, cost_model, benchmark_close, risk_free)
        return

    with st.spinner("Kör backtest (event-driven, dag för dag) ..."):
        try:
            result = BacktestEngine(
                prices,
                strategy,
                start_capital,
                cost_model,
                benchmark_close,
                risk_free_rate=risk_free,
            ).run()
        except (ValueError, RuntimeError) as exc:
            st.error(f"Backtestet kunde inte genomföras: {exc}")
            return

    st.subheader(f"Resultat: {result.strategy_name}")
    _render_result(result)


def _render_result(result: BacktestResult) -> None:
    """Varningar, nyckeltal, grafer och affärslogg för ett resultat."""
    for warning in result.warnings:
        st.warning(warning)
    _metrics_row(result.metrics)
    _result_charts(result)
    with st.expander(f"Affärslogg ({len(result.trades)} rader)"):
        if result.trades.empty:
            st.write("Inga affärer genomfördes.")
        else:
            st.dataframe(result.trades, hide_index=True, use_container_width=True)


def _run_split(
    prices: dict[str, pd.DataFrame],
    strategy: Strategy,
    start_capital: float,
    cost_model: CostModel,
    benchmark_close: pd.Series | None,
    risk_free: float,
) -> None:
    """Kör och redovisar det tudelade backtestet (in-/out-of-sample)."""
    with st.spinner("Kör backtest på båda perioderna ..."):
        try:
            split = run_split_backtest(
                prices, strategy, start_capital, cost_model, benchmark_close, risk_free
            )
        except (ValueError, RuntimeError) as exc:
            st.error(f"Out-of-sample-utvärderingen kunde inte genomföras: {exc}")
            return

    st.subheader(f"Robusthetsutvärdering: {strategy.name}")
    st.caption(
        f"Historiken delades {split.split_date.date()}: strategin kördes separat på "
        "perioden före (in-sample, 70 %) och efter (out-of-sample, 30 %), båda med "
        "samma startkapital. Jämför nyckeltalen — stora försämringar out-of-sample "
        "tyder på overfitting."
    )
    for warning in split.warnings:
        st.warning(warning)

    st.markdown(f"### In-sample (t.o.m. {split.split_date.date()})")
    _render_result(split.in_sample)
    st.markdown(f"### Out-of-sample (fr.o.m. {split.split_date.date()})")
    _render_result(split.out_of_sample)
