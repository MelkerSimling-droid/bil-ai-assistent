"""Delade hjälpfunktioner för dashboardens vyer."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.data_ingestion.base import DataSourceError
from src.data_ingestion.service import MarketDataService


@st.cache_resource
def get_service() -> MarketDataService:
    """En delad MarketDataService för hela appen (cache_resource = singleton)."""
    return MarketDataService.from_config()


@st.cache_data(ttl=3600, show_spinner="Hämtar kursdata ...")
def load_prices(ticker: str) -> pd.DataFrame | None:
    """Hämtar kurshistorik; None vid fel (UI visar då 'data saknas')."""
    try:
        return get_service().get_price_history(ticker)
    except DataSourceError:
        return None


@st.cache_data(ttl=3600, show_spinner="Hämtar fundamenta ...")
def load_fundamentals_dict(ticker: str) -> dict[str, Any] | None:
    """Fundamenta som dict (cachebar); None vid fel."""
    from dataclasses import asdict

    try:
        return asdict(get_service().get_fundamentals(ticker))
    except DataSourceError:
        return None


@st.cache_data(ttl=3600, show_spinner="Hämtar växelkurs ...")
def load_fx_rate(from_currency: str, to_currency: str) -> tuple[float, str] | None:
    """Senaste växelkurs (kurs, kursdatum); None om den inte kunde hämtas."""
    from src.data_ingestion.fx import get_fx_rate

    return get_fx_rate(get_service(), from_currency, to_currency)


def show_missing(what: str, ticker: str) -> None:
    """Standardiserat 'data saknas'-meddelande — vi visar aldrig gissningar."""
    st.warning(
        f"Data saknas: kunde inte hämta {what} för **{ticker}**. "
        "Kontrollera tickern och nätverket — systemet visar aldrig gissade värden. "
        "Se logs/aktiesystem.log för detaljer."
    )
