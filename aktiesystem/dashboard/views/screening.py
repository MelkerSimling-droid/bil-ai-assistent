"""Sida: Screening — filtrera bevakningslistan på fundamentala kriterier."""

from __future__ import annotations

from typing import Any

import streamlit as st

from dashboard.views.common import load_fundamentals_dict
from src.data_ingestion.base import FundamentalData
from src.fundamentals.screening import SCREENABLE_FIELDS, Criterion, screen

_FIELD_LABELS = {
    "market_cap": "Marknadsvärde",
    "pe_ratio": "P/E (rullande)",
    "forward_pe": "P/E (forward)",
    "pb_ratio": "P/B",
    "ev_ebitda": "EV/EBITDA",
    "profit_margin": "Vinstmarginal (decimal)",
    "debt_to_equity": "Skuld/eget kapital",
    "dividend_yield": "Direktavkastning (decimal)",
}


def _criteria_editor() -> list[Criterion]:
    """Låter användaren bygga upp till tre kriterier."""
    criteria: list[Criterion] = []
    st.markdown("**Kriterier** (alla måste uppfyllas):")
    for i in range(3):
        col1, col2, col3, col4 = st.columns([1, 3, 1, 2])
        active = col1.checkbox(
            "på", value=(i == 0), key=f"crit_on_{i}", label_visibility="collapsed"
        )
        field = col2.selectbox(
            "Nyckeltal",
            SCREENABLE_FIELDS,
            index=min(i + 1, len(SCREENABLE_FIELDS) - 1),
            format_func=lambda f: _FIELD_LABELS.get(f, f),
            key=f"crit_field_{i}",
        )
        operator = col3.selectbox("Op", ["<", "<=", ">", ">="], key=f"crit_op_{i}")
        value = col4.number_input("Gränsvärde", value=15.0, key=f"crit_val_{i}")
        if active:
            criteria.append(Criterion(field, operator, float(value)))
    return criteria


def render(config: dict[str, Any]) -> None:
    """Ritar screeningsidan."""
    st.title("Screening")
    st.caption(
        "Filtrerar bevakningslistan på fundamentala nyckeltal. Bolag där data "
        "saknas redovisas separat — de räknas varken som träff eller avslag. "
        "En träff är en observation, inte en köprekommendation."
    )
    watchlist: list[str] = config.get("watchlist", [])
    if not watchlist:
        st.info("Bevakningslistan är tom — lägg till tickers under Inställningar.")
        return

    criteria = _criteria_editor()
    if not criteria:
        st.info("Aktivera minst ett kriterium.")
        return
    if not st.button("Kör screening", type="primary"):
        return

    companies: list[FundamentalData] = []
    failed: list[str] = []
    progress = st.progress(0.0)
    for i, ticker in enumerate(watchlist):
        raw = load_fundamentals_dict(ticker)
        if raw is None:
            failed.append(ticker)
        else:
            companies.append(FundamentalData(**raw))
        progress.progress((i + 1) / len(watchlist))
    progress.empty()

    if failed:
        st.warning(f"Data kunde inte hämtas för: {', '.join(failed)} — de ingår inte i resultatet.")
    if not companies:
        st.error("Ingen fundamenta kunde hämtas — screening kan inte genomföras.")
        return

    result = screen(companies, criteria)
    col1, col2, col3 = st.columns(3)
    col1.metric("Träffar", len(result.matches))
    col2.metric("Uppfyller ej", len(result.rejected))
    col3.metric("Saknar data", len(result.missing_data))
    st.dataframe(result.table, hide_index=True, use_container_width=True)
    if result.missing_data:
        st.caption(
            "Bolag under 'data saknas' har inte poängsatts: att ett nyckeltal saknas "
            "hos källan betyder inte att bolaget uppfyller eller bryter kriteriet."
        )
