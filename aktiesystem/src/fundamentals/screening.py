"""Screening: filtrera bolag på fundamentala kriterier.

Bolag där ett kriteriums nyckeltal saknas EXKLUDERAS ur träffarna men
redovisas separat — att data saknas får aldrig tyst tolkas som godkänt.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import pandas as pd

from src.data_ingestion.base import FundamentalData

#: Nyckeltal som får användas i kriterier (fältnamn i FundamentalData).
SCREENABLE_FIELDS = (
    "market_cap",
    "pe_ratio",
    "forward_pe",
    "pb_ratio",
    "ev_ebitda",
    "profit_margin",
    "debt_to_equity",
    "dividend_yield",
)


@dataclass(frozen=True)
class Criterion:
    """Ett screeningkriterium: fält + operator + gränsvärde.

    Exempel: ``Criterion("pe_ratio", "<", 15)`` betyder P/E under 15.
    """

    field: str
    operator: str  # "<", "<=", ">", ">="
    value: float

    def __post_init__(self) -> None:
        if self.field not in SCREENABLE_FIELDS:
            raise ValueError(f"Okänt nyckeltal {self.field!r}. Tillåtna: {SCREENABLE_FIELDS}")
        if self.operator not in ("<", "<=", ">", ">="):
            raise ValueError(f"Ogiltig operator {self.operator!r}.")

    def matches(self, value: float | None) -> bool | None:
        """Utvärderar kriteriet. None in = None ut (data saknas)."""
        if value is None:
            return None
        if self.operator == "<":
            return value < self.value
        if self.operator == "<=":
            return value <= self.value
        if self.operator == ">":
            return value > self.value
        return value >= self.value


@dataclass
class ScreeningResult:
    """Resultat av en screening, med saknad data öppet redovisad."""

    matches: list[str]
    rejected: list[str]
    missing_data: dict[str, list[str]]  # ticker -> nyckeltal som saknades
    table: pd.DataFrame


def screen(companies: list[FundamentalData], criteria: list[Criterion]) -> ScreeningResult:
    """Filtrerar bolag mot en lista kriterier (alla måste uppfyllas).

    Args:
        companies: Fundamenta för bolagen som ska screenas.
        criteria: Kriterier som samtliga måste vara uppfyllda.

    Returns:
        ScreeningResult där bolag med saknade nyckeltal hamnar i
        ``missing_data`` i stället för i matches/rejected.
    """
    matches: list[str] = []
    rejected: list[str] = []
    missing: dict[str, list[str]] = {}
    rows: list[dict] = []

    for company in companies:
        row: dict = {"ticker": company.ticker, "namn": company.name}
        for field_info in fields(company):
            if field_info.name in SCREENABLE_FIELDS:
                row[field_info.name] = getattr(company, field_info.name)
        missing_fields = [
            crit.field for crit in criteria if crit.matches(getattr(company, crit.field)) is None
        ]
        if missing_fields:
            missing[company.ticker] = sorted(set(missing_fields))
            row["status"] = "data saknas: " + ", ".join(missing[company.ticker])
        elif all(crit.matches(getattr(company, crit.field)) for crit in criteria):
            matches.append(company.ticker)
            row["status"] = "träff"
        else:
            rejected.append(company.ticker)
            row["status"] = "uppfyller ej"
        rows.append(row)

    return ScreeningResult(
        matches=matches,
        rejected=rejected,
        missing_data=missing,
        table=pd.DataFrame(rows),
    )
