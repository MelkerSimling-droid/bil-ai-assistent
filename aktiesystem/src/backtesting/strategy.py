"""Strategi-interface för backtestmotorn.

En strategi får historik till och med "nu" och returnerar målsignaler.
Den lägger inga ordrar själv och vet inget om kassa eller courtage —
det sköter motorn. Därmed kan nya strategier läggas till utan att
motorn ändras.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """Abstrakt basklass för handelsstrategier.

    Implementationer ska vara deterministiska funktioner av historiken:
    samma indata -> samma signaler (krav för reproducerbarhet).
    """

    #: Namn som visas i UI och resultat.
    name: str = "abstrakt strategi"

    #: Max antal barer historik strategin behöver se. None = hela historiken.
    #: Att sätta detta gör backtester på lång intradagshistorik dramatiskt
    #: snabbare (motorn slipper skicka växande dataslices). Sätt det till
    #: minst indikatorns period + tillräcklig uppvärmning; för indikatorer
    #: med exponentiell utjämning (RSI/EMA) ger ~20× perioden numeriskt
    #: försumbar avvikelse mot full historik.
    max_lookback: int | None = None

    @abstractmethod
    def generate_signals(self, history: dict[str, pd.DataFrame]) -> dict[str, int]:
        """Beräknar målsignaler givet historik till och med idag.

        Args:
            history: Per ticker: OHLCV-frame där SISTA raden är "idag".
                Motorn garanterar att ingen framtida data ingår.

        Returns:
            Dict ticker -> 1 (äga) eller 0 (inte äga). Tickers som
            utelämnas tolkas som 0. Om historiken är för kort för
            strategins indikatorer ska 0 returneras (inte ett fel).
        """
