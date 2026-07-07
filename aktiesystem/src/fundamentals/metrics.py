"""Presentation av fundamentala nyckeltal, med saknad data öppet markerad."""

from __future__ import annotations

import pandas as pd

from src.data_ingestion.base import FundamentalData

#: Etikett och formatsträng per nyckeltal (ordningen styr visningen).
_METRIC_LABELS: list[tuple[str, str, str]] = [
    ("market_cap", "Marknadsvärde", "{:,.0f}"),
    ("pe_ratio", "P/E (rullande)", "{:.1f}"),
    ("forward_pe", "P/E (forward)", "{:.1f}"),
    ("pb_ratio", "P/B", "{:.2f}"),
    ("ev_ebitda", "EV/EBITDA", "{:.1f}"),
    ("profit_margin", "Vinstmarginal", "{:.1%}"),
    ("debt_to_equity", "Skuld/eget kapital", "{:.1f}"),
    ("dividend_yield", "Direktavkastning", "{:.2%}"),
    ("free_cash_flow", "Fritt kassaflöde", "{:,.0f}"),
]

MISSING_LABEL = "data saknas"


def metrics_table(company: FundamentalData) -> pd.DataFrame:
    """Bygger en tvåkolumnstabell (nyckeltal, värde) för ett bolag.

    Saknade värden visas som "data saknas" — aldrig som 0 eller gissning.

    Args:
        company: Fundamenta hämtade via datainhämtningsmodulen.

    Returns:
        DataFrame med kolumnerna ``Nyckeltal`` och ``Värde``.
    """
    rows = []
    for field, label, fmt in _METRIC_LABELS:
        value = getattr(company, field)
        rows.append(
            {
                "Nyckeltal": label,
                "Värde": MISSING_LABEL if value is None else fmt.format(value),
            }
        )
    return pd.DataFrame(rows)


def net_debt(company: FundamentalData) -> float | None:
    """Nettoskuld = total skuld − kassa. None om något av värdena saknas."""
    if company.total_debt is None or company.total_cash is None:
        return None
    return company.total_debt - company.total_cash
