"""Valutakurser via Yahoo Finance-valutapar (t.ex. USDSEK=X).

Används för att räkna om innehav i olika valutor till portföljens
basvaluta. Saknas en kurs returneras None — beloppet redovisas då som
"data saknas" i UI och räknas inte in i totalsumman.
"""

from __future__ import annotations

from src.data_ingestion.base import DataSourceError
from src.data_ingestion.service import MarketDataService
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


def fx_pair_ticker(from_currency: str, to_currency: str) -> str:
    """Yahoo-ticker för ett valutapar, t.ex. ("USD", "SEK") -> "USDSEK=X"."""
    return f"{from_currency.upper()}{to_currency.upper()}=X"


def get_fx_rate(
    service: MarketDataService, from_currency: str, to_currency: str
) -> tuple[float, str] | None:
    """Senast kända växelkurs mellan två valutor.

    Args:
        service: Datatjänsten (kursen cachas som vilken ticker som helst).
        from_currency: Valutan beloppet är uttryckt i, t.ex. "USD".
        to_currency: Basvalutan att räkna om till, t.ex. "SEK".

    Returns:
        (kurs, kursdatum som ISO-sträng), eller None om kursen inte kunde
        hämtas — beloppet ska då redovisas som saknat, aldrig gissas.
    """
    if from_currency.upper() == to_currency.upper():
        return 1.0, "samma valuta"
    ticker = fx_pair_ticker(from_currency, to_currency)
    try:
        frame = service.get_price_history(ticker)
    except DataSourceError as exc:
        logger.error("Växelkurs %s kunde inte hämtas: %s", ticker, exc)
        return None
    rate = float(frame["close"].iloc[-1])
    if rate <= 0:
        logger.error("Växelkurs %s är ogiltig (%s).", ticker, rate)
        return None
    return rate, frame.index[-1].date().isoformat()
