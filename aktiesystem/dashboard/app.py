"""Aktiesystemets dashboard (Streamlit).

Körs från projektroten med:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Gör src/ importerbar oavsett varifrån streamlit startas.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Importerna måste ligga efter sys.path-justeringen ovan (noqa: E402).
import streamlit as st  # noqa: E402

from dashboard.views import (  # noqa: E402
    analysis,
    backtest,
    morning,
    optimization,
    overview,
    screening,
    settings,
)
from src.utils.config import ConfigError, load_config  # noqa: E402
from src.utils.logging_setup import setup_logging  # noqa: E402

DISCLAIMER = (
    "**Viktigt:** Det här verktyget är byggt för utbildnings- och analyssyfte "
    "och utgör **inte finansiell rådgivning**. Det presenterar historisk data "
    "och beräknade indikatorer — det förutsäger inte framtiden. Historisk "
    "avkastning i backtester är ingen garanti för framtida resultat. Du "
    "ansvarar själv för alla investeringsbeslut."
)

_PAGES = {
    "Översikt": overview.render,
    "Morgonkoll": morning.render,
    "Aktieanalys": analysis.render,
    "Screening": screening.render,
    "Backtesting": backtest.render,
    "Portföljoptimering": optimization.render,
    "Inställningar": settings.render,
}


def main() -> None:
    """Startpunkt: laddar config, ritar navigation och vald sida."""
    st.set_page_config(page_title="Aktiesystem", page_icon="📈", layout="wide")
    setup_logging()
    try:
        config = load_config()
    except ConfigError as exc:
        st.error(f"Konfigurationsfel: {exc}")
        st.stop()
        return

    st.sidebar.title("Aktiesystem")
    page_name = st.sidebar.radio("Sida", list(_PAGES.keys()))
    st.sidebar.divider()
    st.sidebar.caption(DISCLAIMER)

    if page_name == "Översikt":
        st.info(DISCLAIMER)
    _PAGES[page_name](config)


if __name__ == "__main__":
    main()
