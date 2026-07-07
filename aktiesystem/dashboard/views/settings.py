"""Sida: Inställningar — bevakningslista, riskparametrar, datasynk, API-nycklar."""

from __future__ import annotations

from typing import Any

import streamlit as st
import yaml

from dashboard.views.common import get_service
from src.utils.config import DEFAULT_CONFIG_PATH, get_api_key


def _save_watchlist(config: dict[str, Any], watchlist: list[str]) -> None:
    """Skriver tillbaka bevakningslistan till config.yaml (övrigt orört)."""
    config["watchlist"] = watchlist
    with open(DEFAULT_CONFIG_PATH, "w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, allow_unicode=True, sort_keys=False)


def render(config: dict[str, Any]) -> None:
    """Ritar inställningssidan."""
    st.title("Inställningar")

    st.subheader("Bevakningslista")
    watchlist: list[str] = list(config.get("watchlist", []))
    edited = st.text_area(
        "En ticker per rad (Yahoo-format, svenska aktier har suffixet .ST)",
        value="\n".join(watchlist),
        height=180,
    )
    if st.button("Spara bevakningslistan"):
        new_list = [line.strip().upper() for line in edited.splitlines() if line.strip()]
        try:
            _save_watchlist(config, new_list)
            st.success(f"Sparade {len(new_list)} tickers till config.yaml.")
            st.cache_data.clear()
        except OSError as exc:
            st.error(f"Kunde inte skriva config.yaml: {exc}")

    st.subheader("Synka data")
    st.caption(
        "Hämtar kurser och fundamenta för hela bevakningslistan och uppdaterar den "
        "lokala cachen. Kan ta en stund vid många tickers (rate limits respekteras)."
    )
    if st.button("Synka nu"):
        with st.spinner("Synkar ..."):
            results = get_service().sync_watchlist(config.get("watchlist", []))
        for ticker, status in results.items():
            (st.success if status.startswith("ok") else st.error)(f"{ticker}: {status}")
        st.cache_data.clear()

    st.subheader("Riskparametrar")
    st.caption("Ändras i config/config.yaml — visas här för transparens.")
    st.json(config.get("risk", {}))
    st.json(config.get("backtest", {}))

    st.subheader("API-nycklar")
    st.caption(
        "Nycklar hanteras via .env-filen (se config/.env.example) och visas aldrig "
        "här. yfinance kräver ingen nyckel."
    )
    for key_name in ("ALPHA_VANTAGE_API_KEY", "FMP_API_KEY", "NEWS_API_KEY"):
        status = "konfigurerad" if get_api_key(key_name) else "ej satt (behövs inte för basdrift)"
        st.write(f"- `{key_name}`: {status}")
