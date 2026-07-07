"""Transaktionskostnader: courtage och slippage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    """Konfigurerbar mäklarmodell.

    Attributes:
        courtage_fixed: Fast avgift per affär.
        courtage_percent: Procentuell avgift på affärsvärdet (0.00069 = 0.069 %).
        courtage_min: Minimicourtage per affär.
        slippage_percent: Prisförsämring per affär (0.0005 = 0.05 %),
            alltid till handlarens nackdel.
    """

    courtage_fixed: float = 0.0
    courtage_percent: float = 0.00069
    courtage_min: float = 1.0
    slippage_percent: float = 0.0005

    def __post_init__(self) -> None:
        for name in ("courtage_fixed", "courtage_percent", "courtage_min", "slippage_percent"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} kan inte vara negativ.")

    def courtage(self, trade_value: float) -> float:
        """Courtage för en affär: max(minimum, fast + procent × värde)."""
        if trade_value < 0:
            raise ValueError("Affärsvärdet kan inte vara negativt.")
        if trade_value == 0:
            return 0.0
        return max(self.courtage_min, self.courtage_fixed + self.courtage_percent * trade_value)

    def buy_price(self, market_price: float) -> float:
        """Effektiv köpkurs inklusive slippage (högre än marknadspris)."""
        return market_price * (1.0 + self.slippage_percent)

    def sell_price(self, market_price: float) -> float:
        """Effektiv säljkurs inklusive slippage (lägre än marknadspris)."""
        return market_price * (1.0 - self.slippage_percent)
