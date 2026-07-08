"""Sida: Backtesting — kör en strategi mot historisk data."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.views.common import load_intraday, load_prices, show_missing
from src.backtesting.costs import CostModel
from src.backtesting.engine import BacktestEngine, BacktestResult
from src.backtesting.metrics import PERIODS_PER_YEAR
from src.backtesting.persistence import run_to_dict, save_backtest_run
from src.backtesting.strategies import (
    BollingerReversionStrategy,
    RsiMeanReversionStrategy,
    SmaCrossoverStrategy,
    TimeSeriesMomentumStrategy,
)
from src.backtesting.strategy import Strategy
from src.backtesting.validation import rolling_window_evaluation, run_split_backtest
from src.utils.config import PROJECT_ROOT

OVERFITTING_WARNING = (
    "**Overfittingrisk:** när du justerar parametrar tills historiken ser bra ut "
    "anpassar du strategin till brus i just den perioden. Ett bra backtestresultat "
    "efter många parameterförsök säger mycket lite om framtiden. Testa alltid på "
    "en annan tidsperiod/andra tickers än den du optimerade på."
)


def _build_strategy() -> Strategy | None:
    """Strategival + parameterinmatning. None tills valet är komplett."""
    kind = st.selectbox(
        "Strategi",
        ["SMA-korsning", "RSI mean reversion", "Bollinger-reversion", "Tidsseriemomentum"],
    )
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
        if kind == "Tidsseriemomentum":
            col1, col2 = st.columns(2)
            lookback = int(col1.number_input("Mätperiod (barer)", 10, 500, 252))
            skip = int(col2.number_input("Exkludera senaste (barer)", 0, 100, 21))
            return TimeSeriesMomentumStrategy(lookback, skip)
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
    st.plotly_chart(fig, width="stretch")

    dd = go.Figure(
        go.Scatter(
            x=result.drawdown_curve.index, y=result.drawdown_curve, fill="tozeroy", name="Drawdown"
        )
    )
    dd.update_layout(title="Drawdown", height=250, yaxis_tickformat=".0%")
    st.plotly_chart(dd, width="stretch")


def _metrics_row(metrics: dict[str, float]) -> None:
    def fmt(key: str, pct: bool = False) -> str:
        value = metrics.get(key)
        if value is None or value != value:
            return "–"
        return f"{value:.1%}" if pct else f"{value:.2f}"

    cols = st.columns(7)
    cols[0].metric("Total avkastning", fmt("total_avkastning", pct=True))
    cols[1].metric("CAGR", fmt("cagr", pct=True))
    cols[2].metric("Sharpe", fmt("sharpe"))
    cols[3].metric("Sortino", fmt("sortino"))
    cols[4].metric("Max drawdown", fmt("max_drawdown", pct=True))
    cols[5].metric("Win rate", fmt("win_rate", pct=True))
    cols[6].metric("Exponering", fmt("exponering", pct=True))
    if "benchmark_avkastning" in metrics:
        st.caption(
            f"Index (buy & hold) gav {metrics['benchmark_avkastning']:.1%} under samma period "
            f"— strategins överavkastning: {metrics['overavkastning_mot_index']:+.1%}. "
        )
    st.caption(
        "Sharpe/Sortino: riskjusterad avkastning (högre är bättre; Sortino straffar bara "
        "nedgångsdagar). Win rate: andel avslutade affärer med vinst. Exponering: andel "
        "handelsdagar med öppen position — jämför inte rakt av med ett alltid-investerat "
        "index om exponeringen är låg. Alla siffror inkluderar courtage och slippage."
    )


def render(config: dict[str, Any]) -> None:
    """Ritar backtestsidan."""
    st.title("Backtesting")
    st.info(OVERFITTING_WARNING)

    watchlist: list[str] = config.get("watchlist", [])
    tickers = st.multiselect("Tickers", watchlist, default=watchlist[:2])
    data_source = st.selectbox(
        "Datakälla",
        ["Dagsdata (upp till 10 år)", "Intradag 1h (ca 2 år)", "Intradag 15m (ca 60 dagar)"],
        help=(
            "Intradagsbarer testar strategin på timmes-/kvartsnivå (för dagshandel). "
            "Obs: kortare historik ger färre affärer och lägre statistiskt värde, och "
            "signalen på bar T exekveras på nästa bars öppning — precis som för dagsdata."
        ),
    )
    interval = {"Dagsdata": "1d", "Intradag 1h": "1h", "Intradag 15m": "15m"}[
        data_source.split(" (")[0]
    ]
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

    mode = st.selectbox(
        "Robusthetsutvärdering",
        [
            "Ingen (en körning på hela perioden)",
            "In-/out-of-sample (70/30)",
            "Rullande fönster (4 delperioder)",
        ],
        help=(
            "70/30: strategin körs separat på de första 70 % (in-sample) och de sista "
            "30 % (out-of-sample) av historiken. Rullande fönster: fyra lika långa "
            "delperioder körs var för sig — avslöjar strategier vars resultat kommer "
            "från en enda gynnsam period."
        ),
    )

    col_run, col_compare = st.columns([1, 2])
    run_single = col_run.button("Kör backtest", type="primary")
    run_comparison = col_compare.button(
        "Jämför alla strategier (standardparametrar)",
        help=(
            "Kör alla fyra strategierna med standardparametrar plus köp-och-behåll "
            "på samma data och kostnadsmodell — en snabb överblick över vilka "
            "angreppssätt som historiskt fungerat på just dessa tickers."
        ),
    )
    if not tickers or strategy is None or not (run_single or run_comparison):
        return

    prices: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        frame = load_prices(ticker) if interval == "1d" else load_intraday(ticker, interval)
        if frame is None:
            show_missing(f"kursdata ({interval})", ticker)
            return
        prices[ticker] = frame

    benchmark_ticker = str(config.get("benchmark", ""))
    benchmark_close = None
    if interval != "1d":
        st.caption(
            "Indexjämförelse görs inte för intradagsbacktester (indexdata på "
            "intradagsnivå är opålitlig hos källan)."
        )
    elif benchmark_ticker:
        bench = load_prices(benchmark_ticker)
        if bench is not None:
            benchmark_close = bench["close"]
        else:
            st.warning(f"Benchmarkdata ({benchmark_ticker}) kunde inte hämtas — jämförelsen utgår.")

    risk_free = float(config["risk"].get("risk_free_rate", 0.02))
    periods = PERIODS_PER_YEAR[interval]
    if run_comparison:
        _run_comparison(prices, start_capital, cost_model, benchmark_close, risk_free, periods)
        return
    if mode.startswith("In-/out"):
        _run_split(prices, strategy, start_capital, cost_model, benchmark_close, risk_free, periods)
        return
    if mode.startswith("Rullande"):
        _run_rolling(prices, strategy, start_capital, cost_model, risk_free, periods)
        return

    with st.spinner("Kör backtest (event-driven, bar för bar) ..."):
        try:
            result = BacktestEngine(
                prices,
                strategy,
                start_capital,
                cost_model,
                benchmark_close,
                risk_free_rate=risk_free,
                periods_per_year=periods,
            ).run()
        except (ValueError, RuntimeError) as exc:
            st.error(f"Backtestet kunde inte genomföras: {exc}")
            return

    st.subheader(f"Resultat: {result.strategy_name}")
    _render_result(result)
    _offer_saved_run(result, list(prices), start_capital, cost_model)


def _offer_saved_run(
    result: BacktestResult,
    tickers: list[str],
    start_capital: float,
    cost_model: CostModel,
) -> None:
    """Sparar körningen till disk och erbjuder nedladdning (reproducerbarhet)."""
    import json

    payload = run_to_dict(result, tickers, start_capital, cost_model)
    try:
        path = save_backtest_run(result, tickers, start_capital, cost_model)
        st.caption(f"Körningen sparades för spårbarhet: `{path.relative_to(PROJECT_ROOT)}`")
    except OSError as exc:
        st.warning(f"Körningen kunde inte sparas till disk: {exc}")
    st.download_button(
        "Ladda ner körningen (JSON)",
        data=json.dumps(payload, ensure_ascii=False, indent=2),
        file_name="backtest.json",
        mime="application/json",
    )


class _BuyAndHold(Strategy):
    """Referens: alltid investerad (lika vikt), samma kostnadsmodell."""

    name = "Köp & behåll (lika vikt)"

    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        return {ticker: 1 for ticker in history}


def _run_comparison(
    prices: dict[str, pd.DataFrame],
    start_capital: float,
    cost_model: CostModel,
    benchmark_close: pd.Series | None,
    risk_free: float,
    periods_per_year: float,
) -> None:
    """Kör alla strategier (standardparametrar) på samma data och jämför."""
    strategies: list[Strategy] = [
        _BuyAndHold(),
        SmaCrossoverStrategy(),
        RsiMeanReversionStrategy(),
        BollingerReversionStrategy(),
        TimeSeriesMomentumStrategy(),
    ]
    rows = []
    curves: dict[str, pd.Series] = {}
    progress = st.progress(0.0, "Kör strategier ...")
    for i, strategy in enumerate(strategies):
        try:
            result = BacktestEngine(
                prices,
                strategy,
                start_capital,
                cost_model,
                benchmark_close,
                risk_free_rate=risk_free,
                periods_per_year=periods_per_year,
            ).run()
        except (ValueError, RuntimeError) as exc:
            st.warning(f"{strategy.name}: kunde inte köras ({exc}).")
            continue
        m = result.metrics

        def fmt(key: str, pct: bool = True, metrics: dict[str, float] = m) -> str:
            value = metrics.get(key)
            if value is None or value != value:
                return "–"
            return f"{value:.1%}" if pct else f"{value:.2f}"

        rows.append(
            {
                "Strategi": strategy.name,
                "Avkastning": fmt("total_avkastning"),
                "CAGR": fmt("cagr"),
                "Sharpe": fmt("sharpe", pct=False),
                "Max drawdown": fmt("max_drawdown"),
                "Win rate": fmt("win_rate"),
                "Exponering": fmt("exponering"),
                "Affärer": int(m.get("antal_affarer", 0)),
            }
        )
        curves[strategy.name] = result.equity_curve
        progress.progress((i + 1) / len(strategies), f"Kört {strategy.name}")
    progress.empty()
    if not rows:
        st.error("Ingen strategi kunde köras på den valda datan.")
        return

    st.subheader("Strategijämförelse (standardparametrar)")
    st.caption(
        "Samma data, samma startkapital, samma kostnadsmodell. Köp & behåll är "
        "referensen att slå — en strategi som ligger under den har historiskt inte "
        "motiverat sitt krångel. Historiskt resultat är ingen prognos, och att den "
        "bästa strategin här vinner beror delvis på just denna period (se "
        "robusthetsutvärderingarna innan slutsatser dras)."
    )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    fig = go.Figure()
    for name, curve in curves.items():
        fig.add_trace(go.Scatter(x=curve.index, y=curve, name=name))
    fig.update_layout(title="Equity-kurvor", height=450, legend={"orientation": "h"})
    st.plotly_chart(fig, width="stretch")


def _run_rolling(
    prices: dict[str, pd.DataFrame],
    strategy: Strategy,
    start_capital: float,
    cost_model: CostModel,
    risk_free: float,
    periods_per_year: float,
) -> None:
    """Kör och redovisar rullande fönster-utvärderingen."""
    with st.spinner("Kör backtest på fyra delperioder ..."):
        try:
            windows, warnings = rolling_window_evaluation(
                prices,
                strategy,
                start_capital,
                cost_model,
                risk_free,
                n_windows=4,
                periods_per_year=periods_per_year,
            )
        except (ValueError, RuntimeError) as exc:
            st.error(f"Utvärderingen kunde inte genomföras: {exc}")
            return

    st.subheader(f"Rullande fönster: {strategy.name}")
    st.caption(
        "Historiken delades i fyra lika långa delperioder som körts var för sig med "
        "samma startkapital. En robust strategi presterar hyggligt i de flesta "
        "delperioder — inte bara i en."
    )
    for warning in warnings:
        st.warning(warning)

    def cell(metrics: dict[str, float], key: str, pct: bool = True) -> str:
        value = metrics.get(key)
        if value is None or value != value:
            return "–"
        return f"{value:.1%}" if pct else f"{value:.2f}"

    table = pd.DataFrame(
        [
            {
                "Period": f"{w.start.date()} – {w.end.date()}",
                "Avkastning": cell(w.result.metrics, "total_avkastning"),
                "Sharpe": cell(w.result.metrics, "sharpe", pct=False),
                "Max drawdown": cell(w.result.metrics, "max_drawdown"),
                "Exponering": cell(w.result.metrics, "exponering"),
                "Affärer": int(w.result.metrics.get("antal_affarer", 0)),
            }
            for w in windows
        ]
    )
    st.dataframe(table, hide_index=True, width="stretch")
    with st.expander("Equity-kurvor per delperiod"):
        for window in windows:
            st.markdown(f"**{window.start.date()} – {window.end.date()}**")
            st.line_chart(window.result.equity_curve)


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
            st.dataframe(result.trades, hide_index=True, width="stretch")


def _run_split(
    prices: dict[str, pd.DataFrame],
    strategy: Strategy,
    start_capital: float,
    cost_model: CostModel,
    benchmark_close: pd.Series | None,
    risk_free: float,
    periods_per_year: float,
) -> None:
    """Kör och redovisar det tudelade backtestet (in-/out-of-sample)."""
    with st.spinner("Kör backtest på båda perioderna ..."):
        try:
            split = run_split_backtest(
                prices,
                strategy,
                start_capital,
                cost_model,
                benchmark_close,
                risk_free,
                periods_per_year=periods_per_year,
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
