"""Enkel DCF-värdering (Discounted Cash Flow) med exponerade antaganden.

VIKTIGT: Resultatet är EXTREMT känsligt för antagandena (tillväxt,
diskonteringsränta, terminaltillväxt). Modellen är ett resonemangsverktyg,
inte ett facit — dashboarden visar alltid en känslighetstabell tillsammans
med resultatet.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DCFAssumptions:
    """Antaganden för DCF-modellen. Alla räntor/tillväxttal som decimaler.

    Attributes:
        growth_rate: Årlig FCF-tillväxt under prognosperioden (0.05 = 5 %).
        discount_rate: Diskonteringsränta/avkastningskrav, t.ex. 0.09.
        terminal_growth: Evig tillväxt efter prognosperioden, t.ex. 0.02.
        projection_years: Antal prognosår innan terminalvärdet.
    """

    growth_rate: float = 0.05
    discount_rate: float = 0.09
    terminal_growth: float = 0.02
    projection_years: int = 5

    def __post_init__(self) -> None:
        if self.discount_rate <= self.terminal_growth:
            raise ValueError(
                "Diskonteringsräntan måste vara större än terminaltillväxten, "
                f"annars blir terminalvärdet odefinierat ({self.discount_rate} <= {self.terminal_growth})."
            )
        if self.projection_years < 1:
            raise ValueError("projection_years måste vara >= 1.")


@dataclass
class DCFResult:
    """Resultat av en DCF-beräkning, med full spårbarhet av delstegen."""

    enterprise_value: float
    equity_value: float
    value_per_share: float | None
    projected_fcf: list[float]
    discounted_fcf: list[float]
    terminal_value: float
    discounted_terminal_value: float
    assumptions: DCFAssumptions


def dcf_valuation(
    free_cash_flow: float,
    assumptions: DCFAssumptions,
    net_debt: float = 0.0,
    shares_outstanding: float | None = None,
) -> DCFResult:
    """Beräknar bolagsvärde med en tvåstegs-DCF (prognos + Gordon-terminal).

    Args:
        free_cash_flow: Senast kända årliga fria kassaflödet (basår).
        assumptions: Tillväxt-, diskonterings- och terminalantaganden.
        net_debt: Nettoskuld (total skuld minus kassa); dras från
            enterprise value för att få equity value.
        shares_outstanding: Antal utestående aktier; om None beräknas
            inget värde per aktie (visas som "data saknas").

    Returns:
        DCFResult med samtliga delsteg för spårbarhet.

    Raises:
        ValueError: Om basårets FCF inte är positivt — modellen är inte
            meningsfull då, och vi hittar inte på ett värde.
    """
    if free_cash_flow <= 0:
        raise ValueError(
            "DCF kräver positivt fritt kassaflöde som basår. "
            f"Fick {free_cash_flow:.0f} — modellen är inte tillämplig."
        )
    a = assumptions
    projected = [
        free_cash_flow * (1 + a.growth_rate) ** year for year in range(1, a.projection_years + 1)
    ]
    discounted = [
        fcf / (1 + a.discount_rate) ** year for year, fcf in enumerate(projected, start=1)
    ]
    # Gordon growth-terminalvärde på sista prognosårets FCF.
    terminal = projected[-1] * (1 + a.terminal_growth) / (a.discount_rate - a.terminal_growth)
    discounted_terminal = terminal / (1 + a.discount_rate) ** a.projection_years

    enterprise_value = sum(discounted) + discounted_terminal
    equity_value = enterprise_value - net_debt
    per_share = (
        equity_value / shares_outstanding if shares_outstanding and shares_outstanding > 0 else None
    )
    return DCFResult(
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        value_per_share=per_share,
        projected_fcf=projected,
        discounted_fcf=discounted,
        terminal_value=terminal,
        discounted_terminal_value=discounted_terminal,
        assumptions=a,
    )


def sensitivity_table(
    free_cash_flow: float,
    base: DCFAssumptions,
    net_debt: float = 0.0,
    shares_outstanding: float | None = None,
    growth_range: tuple[float, ...] = (-0.02, 0.0, 0.02),
    discount_range: tuple[float, ...] = (-0.02, 0.0, 0.02),
) -> pd.DataFrame:
    """Bygger en känslighetstabell: värde per aktie (eller equity value)
    för kombinationer av tillväxt- och diskonteringsränta runt basfallet.

    Returns:
        DataFrame med diskonteringsräntor som rader och tillväxttal som
        kolumner. Celler där modellen inte är definierad blir NaN.
    """
    rows = {}
    for d_delta in discount_range:
        discount = base.discount_rate + d_delta
        row = {}
        for g_delta in growth_range:
            growth = base.growth_rate + g_delta
            try:
                result = dcf_valuation(
                    free_cash_flow,
                    DCFAssumptions(
                        growth_rate=growth,
                        discount_rate=discount,
                        terminal_growth=base.terminal_growth,
                        projection_years=base.projection_years,
                    ),
                    net_debt=net_debt,
                    shares_outstanding=shares_outstanding,
                )
                row[f"tillväxt {growth:.1%}"] = (
                    result.value_per_share
                    if result.value_per_share is not None
                    else result.equity_value
                )
            except ValueError:
                row[f"tillväxt {growth:.1%}"] = float("nan")
        rows[f"ränta {discount:.1%}"] = row
    return pd.DataFrame(rows).T
