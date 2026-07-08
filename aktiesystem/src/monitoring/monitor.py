"""Marknadsbevakning: utvärderar larmregler och skickar notiser.

Körs manuellt eller schemalagt (se README):

    .venv/bin/python -m src.monitoring.monitor

Varje larm är en indikatorobservation, ALDRIG en rekommendation.
Dubblettskydd: ett larm-id (ticker + regel + dag) notifieras bara en gång;
historiken sparas i SQLite och visas i dashboardens översikt.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_ingestion.base import DataSourceError
from src.data_ingestion.service import MarketDataService
from src.monitoring.notify import LogNotifier, MacNotifier, Notifier
from src.monitoring.rules import Alert, evaluate_price_rules, sentiment_alert
from src.sentiment.news_sentiment import score_headlines
from src.utils.config import load_config, resolve_path
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id   TEXT PRIMARY KEY,
    ticker     TEXT NOT NULL,
    rule       TEXT NOT NULL,
    title      TEXT NOT NULL,
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class AlertState:
    """SQLite-baserat dubblettskydd och larmhistorik."""

    def __init__(self, db_path: Path) -> None:
        """Öppnar (skapar vid behov) larmdatabasen."""
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_SCHEMA)

    def is_new(self, alert_id: str) -> bool:
        """Sant om larmet inte redan har notifierats."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT 1 FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
        return row is None

    def record(self, alert: Alert) -> None:
        """Sparar ett notifierat larm i historiken."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO alerts VALUES (?, ?, ?, ?, ?, ?)",
                (
                    alert.alert_id,
                    alert.ticker,
                    alert.rule,
                    alert.title,
                    alert.message,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def recent(self, limit: int = 50) -> pd.DataFrame:
        """De senaste larmen, nyast först (för dashboarden)."""
        with sqlite3.connect(self._db_path) as conn:
            return pd.read_sql_query(
                "SELECT created_at, ticker, rule, title, message FROM alerts"
                " ORDER BY created_at DESC LIMIT ?",
                conn,
                params=(limit,),
            )


def _evaluate_ticker(
    service: MarketDataService, ticker: str, rules: dict[str, Any], max_headlines: int
) -> list[Alert]:
    """Utvärderar alla regler för en ticker. Datafel loggas, gissas aldrig bort."""
    alerts: list[Alert] = []
    try:
        prices = service.get_price_history(ticker, force_refresh=True)
        alerts.extend(evaluate_price_rules(ticker, prices, rules))
    except DataSourceError as exc:
        logger.error(
            "Bevakning: kursdata saknas för %s (%s) — prisregler hoppas över.", ticker, exc
        )
        return alerts
    if rules.get("sentiment_threshold") is not None:
        try:
            headlines = score_headlines(service.get_news(ticker, limit=max_headlines))
            if headlines:
                mean = sum(h.compound for h in headlines) / len(headlines)
                date = prices.index[-1].date().isoformat()
                alerts.extend(sentiment_alert(ticker, mean, len(headlines), rules, date))
        except DataSourceError as exc:
            logger.warning("Bevakning: nyheter saknas för %s (%s).", ticker, exc)
    return alerts


def run_monitor(
    config: dict[str, Any] | None = None,
    notifiers: list[Notifier] | None = None,
    state: AlertState | None = None,
) -> list[Alert]:
    """Kör en bevakningsrunda över hela bevakningslistan.

    Args:
        config: Konfiguration (läses från config.yaml om None).
        notifiers: Notifieringskanaler (standard: macOS-notis + logg).
        state: Dubblettskydd/historik (standard: enligt config).

    Returns:
        De NYA larm som notifierades under denna runda.
    """
    cfg = config or load_config()
    monitoring = cfg.get("monitoring") or {}
    rules = monitoring.get("rules") or {}
    if not rules:
        logger.warning("Ingen monitoring.rules-sektion i config.yaml — inget att bevaka.")
        return []
    service = MarketDataService.from_config(cfg)
    state = state or AlertState(
        resolve_path(monitoring.get("state_db", "data/processed/alerts.sqlite"))
    )
    notifiers = notifiers if notifiers is not None else [MacNotifier(), LogNotifier()]
    max_headlines = int(cfg.get("sentiment", {}).get("max_headlines", 25))

    sent: list[Alert] = []
    for ticker in cfg.get("watchlist", []):
        for alert in _evaluate_ticker(service, ticker, rules, max_headlines):
            if not state.is_new(alert.alert_id):
                continue
            for notifier in notifiers:
                notifier.send(alert.title, alert.message)
            state.record(alert)
            sent.append(alert)
    logger.info("Bevakningsrunda klar: %d nya larm.", len(sent))
    return sent


def main() -> None:
    """CLI-startpunkt: kör en runda och skriv resultatet till stdout."""
    alerts = run_monitor()
    if not alerts:
        print("Inga nya larm.")
        return
    for alert in alerts:
        print(f"[{alert.ticker}] {alert.title}\n  {alert.message}")


if __name__ == "__main__":
    main()
