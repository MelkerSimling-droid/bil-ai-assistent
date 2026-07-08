"""Sparar backtestkörningar till disk för reproducerbarhet.

Spec-princip: alla resultat i dashboarden ska kunna spåras i efterhand.
Varje körning sparas som en JSON-fil med tidsstämpel, strategi, parametrar,
nyckeltal, varningar och hela equity-kurvan.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from src.backtesting.costs import CostModel
from src.backtesting.engine import BacktestResult
from src.utils.config import PROJECT_ROOT
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)

DEFAULT_RUNS_DIR = PROJECT_ROOT / "data" / "processed" / "backtests"


def run_to_dict(
    result: BacktestResult,
    tickers: list[str],
    start_capital: float,
    cost_model: CostModel,
) -> dict:
    """Serialiserar en körning till en JSON-vänlig dict.

    Args:
        result: Backtestresultatet.
        tickers: Vilka tickers som ingick.
        start_capital: Startkapitalet som användes.
        cost_model: Courtage-/slippagemodellen som användes.

    Returns:
        Dict med allt som krävs för att granska körningen i efterhand.
        NaN/inf i nyckeltalen ersätts med None (giltig JSON).
    """

    def json_safe(value: float) -> float | None:
        return value if value == value and abs(value) != float("inf") else None

    return {
        "sparad": datetime.now(UTC).isoformat(),
        "strategi": result.strategy_name,
        "tickers": sorted(tickers),
        "startkapital": start_capital,
        "kostnadsmodell": asdict(cost_model),
        "period": {
            "start": result.equity_curve.index[0].date().isoformat(),
            "slut": result.equity_curve.index[-1].date().isoformat(),
            "handelsdagar": len(result.equity_curve),
        },
        "nyckeltal": {key: json_safe(value) for key, value in result.metrics.items()},
        "varningar": result.warnings,
        "antal_affarer_i_logg": len(result.trades),
        "equity_kurva": {
            index.date().isoformat(): round(float(value), 2)
            for index, value in result.equity_curve.items()
        },
    }


def save_backtest_run(
    result: BacktestResult,
    tickers: list[str],
    start_capital: float,
    cost_model: CostModel,
    directory: Path | None = None,
) -> Path:
    """Sparar en körning som JSON och returnerar filens sökväg.

    Filnamnet innehåller tidsstämpel och strateginamn, t.ex.
    ``2026-07-08T09-30-00_sma-korsning-50-200.json``.

    Raises:
        OSError: Om filen inte kan skrivas (rapporteras uppåt, döljs aldrig).
    """
    runs_dir = directory or DEFAULT_RUNS_DIR
    runs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")
    slug = "".join(c if c.isalnum() else "-" for c in result.strategy_name.lower()).strip("-")
    path = runs_dir / f"{timestamp}_{slug}.json"
    payload = run_to_dict(result, tickers, start_capital, cost_model)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    logger.info("Backtestkörning sparad: %s", path)
    return path
