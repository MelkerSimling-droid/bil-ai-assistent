"""Grundläggande sentimentanalys av nyhetsrubriker med VADER.

VIKTIGA BEGRÄNSNINGAR (visas även i UI):
* VADER är ett engelskt lexikon byggt för sociala medier — svenska
  rubriker får opålitliga poäng och finansspråk tolkas ofta fel
  ("beats expectations" fångas, "sänkt riktkurs" gör det inte).
* Rubriksentiment är en GROV approximation och ingen pålitlig prediktor
  för kursutveckling. Använd som kontext, inte beslutsunderlag.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.data_ingestion.base import NewsItem

DISCLAIMER = (
    "Sentimentpoängen bygger på VADER, ett engelskspråkigt lexikon för sociala "
    "medier. Poängen är en grov approximation — inte en pålitlig prediktor för "
    "kursutveckling — och fungerar dåligt på icke-engelska rubriker."
)

#: Gränser för klassificering av compound-poängen (VADER:s standardkonvention).
_POSITIVE_THRESHOLD = 0.05
_NEGATIVE_THRESHOLD = -0.05


@dataclass
class ScoredHeadline:
    """En nyhetsrubrik med sentimentpoäng."""

    ticker: str
    title: str
    published_at: str | None
    publisher: str | None
    url: str | None
    compound: float  # -1 (mest negativ) till +1 (mest positiv)
    label: str  # "positiv" / "neutral" / "negativ"


def _label(compound: float) -> str:
    """Klassificerar en compound-poäng enligt VADER-konventionen."""
    if compound >= _POSITIVE_THRESHOLD:
        return "positiv"
    if compound <= _NEGATIVE_THRESHOLD:
        return "negativ"
    return "neutral"


def score_headlines(items: list[NewsItem]) -> list[ScoredHeadline]:
    """Sätter sentimentpoäng på en lista nyhetsrubriker.

    Args:
        items: Nyheter från datainhämtningsmodulen.

    Returns:
        En ScoredHeadline per rubrik (tomma rubriker hoppas över).
    """
    analyzer = SentimentIntensityAnalyzer()
    scored = []
    for item in items:
        if not item.title.strip():
            continue
        compound = float(analyzer.polarity_scores(item.title)["compound"])
        scored.append(
            ScoredHeadline(
                ticker=item.ticker,
                title=item.title,
                published_at=item.published_at,
                publisher=item.publisher,
                url=item.url,
                compound=compound,
                label=_label(compound),
            )
        )
    return scored


def aggregate_sentiment(scored: list[ScoredHeadline]) -> pd.DataFrame:
    """Aggregerar sentiment per ticker och dag.

    Args:
        scored: Poängsatta rubriker.

    Returns:
        DataFrame med kolumnerna ticker, datum (eller "okänt datum" när
        publiceringstid saknas), antal rubriker och medelpoäng. Tom frame
        om inga rubriker finns — aldrig påhittade rader.
    """
    if not scored:
        return pd.DataFrame(columns=["ticker", "datum", "antal_rubriker", "medelpoang"])
    frame = pd.DataFrame(
        {
            "ticker": [s.ticker for s in scored],
            "datum": [s.published_at[:10] if s.published_at else "okänt datum" for s in scored],
            "compound": [s.compound for s in scored],
        }
    )
    grouped = (
        frame.groupby(["ticker", "datum"])["compound"]
        .agg(antal_rubriker="count", medelpoang="mean")
        .reset_index()
    )
    return grouped.sort_values(["ticker", "datum"], ascending=[True, False]).reset_index(drop=True)
