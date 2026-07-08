"""Sida: Morgonkoll — hela bevakningslistan sammanfattad i en tabell.

Tanken: en enda vy som besvarar "hur ser mina aktier ut idag?" utan att
användaren behöver klicka runt. Varje kolumn är en indikatorobservation i
klartext — vad man gör med informationen är ens eget beslut.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from dashboard.views.common import load_prices, show_missing
from src.analysis.scorecard import Scorecard, build_scorecard, scorecards_table

_COLUMN_GUIDE = """
**Så läser du tabellen** (alla fält beskriver historisk data — inga prognoser):

- **Trend**: kursens läge mot 50- och 200-dagars glidande medelvärde.
  "Upptrend" betyder bara att kursen ligger över båda — inte att den fortsätter upp.
- **RSI 14**: momentum 0–100. Under 30 kallas översålt, över 70 överköpt;
  i starka trender kan RSI stanna länge i ytterlägena.
- **MACD-histogram**: skillnaden mellan MACD- och signallinjen. Positivt och
  stigande brukar läsas som tilltagande momentum uppåt — och omvänt.
- **Från 52v-högsta/-lägsta**: avstånd till senaste årets extremnivåer.
- **Volatilitet**: hur mycket kursen svängt senaste året, i årstakt.
  Högre volatilitet = större rörelser åt båda hållen.
"""


def render(config: dict[str, Any]) -> None:
    """Ritar morgonkollsidan."""
    st.title("Morgonkoll")
    st.caption(
        "Hela bevakningslistan i en tabell — sorterbar genom att klicka på "
        "kolumnrubrikerna. Observationer, inte rekommendationer."
    )
    watchlist: list[str] = config.get("watchlist", [])
    if not watchlist:
        st.info("Bevakningslistan är tom — lägg till tickers under Inställningar.")
        return

    cards: list[Scorecard] = []
    failed: list[str] = []
    progress = st.progress(0.0, text="Hämtar och beräknar ...")
    for i, ticker in enumerate(watchlist):
        prices = load_prices(ticker)
        if prices is None:
            failed.append(ticker)
        else:
            try:
                cards.append(build_scorecard(ticker, prices))
            except ValueError:
                failed.append(ticker)
        progress.progress((i + 1) / len(watchlist), text=f"{ticker} klar")
    progress.empty()

    if failed:
        for ticker in failed:
            show_missing("kursdata", ticker)
    if not cards:
        st.error("Ingen ticker kunde sammanställas.")
        return

    st.dataframe(scorecards_table(cards), hide_index=True, width="stretch")
    with st.expander("Vad betyder kolumnerna?"):
        st.markdown(_COLUMN_GUIDE)
