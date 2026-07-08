"""Lokal SQLite-cache för marknadsdata.

Syfte: undvika onödiga API-anrop (rate limits) och ge reproducerbarhet —
varje hämtning loggas med tidsstämpel, källa och parametrar i sync_log.
Dataåtkomsten är samlad här så att SQLite senare kan bytas mot Postgres
utan att övriga moduler påverkas.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from src.data_ingestion.base import FundamentalData
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,
    open   REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY (ticker, date)
);
CREATE TABLE IF NOT EXISTS intraday_prices (
    ticker   TEXT NOT NULL,
    interval TEXT NOT NULL,
    ts       TEXT NOT NULL,
    open   REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY (ticker, interval, ts)
);
CREATE TABLE IF NOT EXISTS fundamentals (
    ticker     TEXT PRIMARY KEY,
    fetched_at TEXT NOT NULL,
    source     TEXT NOT NULL,
    payload    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sync_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker     TEXT NOT NULL,
    data_type  TEXT NOT NULL,
    source     TEXT NOT NULL,
    params     TEXT,
    fetched_at TEXT NOT NULL,
    row_count  INTEGER
);
"""


class MarketDataCache:
    """SQLite-baserad cache för kurser och fundamenta."""

    def __init__(self, db_path: Path) -> None:
        """Öppnar (eller skapar) cachedatabasen.

        Args:
            db_path: Sökväg till SQLite-filen. Katalogen skapas vid behov.
        """
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        """Öppnar en anslutning med radfabrik."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def store_prices(self, ticker: str, frame: pd.DataFrame, source: str, params: str) -> None:
        """Sparar OHLCV-data och loggar hämtningen i sync_log.

        Args:
            ticker: Tickern datan gäller.
            frame: DataFrame med DatetimeIndex och open/high/low/close/volume.
            source: Datakällans namn (för spårbarhet).
            params: Parametrar som användes vid hämtningen, t.ex. period.
        """
        rows = [
            (
                ticker,
                index.strftime("%Y-%m-%d"),
                None if pd.isna(row["open"]) else float(row["open"]),
                None if pd.isna(row["high"]) else float(row["high"]),
                None if pd.isna(row["low"]) else float(row["low"]),
                None if pd.isna(row["close"]) else float(row["close"]),
                None if pd.isna(row["volume"]) else float(row["volume"]),
            )
            for index, row in frame.iterrows()
        ]
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.executemany("INSERT OR REPLACE INTO prices VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
            conn.execute(
                "INSERT INTO sync_log (ticker, data_type, source, params, fetched_at, row_count)"
                " VALUES (?, 'prices', ?, ?, ?, ?)",
                (ticker, source, params, now, len(rows)),
            )
        logger.info("Cachade %d kursrader för %s (källa: %s).", len(rows), ticker, source)

    def load_prices(self, ticker: str) -> pd.DataFrame | None:
        """Läser cachad kurshistorik.

        Returns:
            DataFrame sorterad på datum, eller None om tickern saknas i cachen.
        """
        with self._connect() as conn:
            frame = pd.read_sql_query(
                "SELECT date, open, high, low, close, volume FROM prices"
                " WHERE ticker = ? ORDER BY date",
                conn,
                params=(ticker,),
                parse_dates=["date"],
                index_col="date",
            )
        return None if frame.empty else frame

    def store_intraday(
        self, ticker: str, interval: str, frame: pd.DataFrame, source: str, params: str
    ) -> None:
        """Sparar intradags-OHLCV (tidsstämplar med klockslag) + sync-logg.

        Args:
            ticker: Tickern datan gäller.
            interval: Barlängd, t.ex. "1h" eller "15m".
            frame: DataFrame med DatetimeIndex och open/high/low/close/volume.
            source: Datakällans namn.
            params: Hämtningsparametrar (period/interval) för spårbarhet.
        """
        rows = [
            (
                ticker,
                interval,
                index.strftime("%Y-%m-%d %H:%M:%S"),
                None if pd.isna(row["open"]) else float(row["open"]),
                None if pd.isna(row["high"]) else float(row["high"]),
                None if pd.isna(row["low"]) else float(row["low"]),
                None if pd.isna(row["close"]) else float(row["close"]),
                None if pd.isna(row["volume"]) else float(row["volume"]),
            )
            for index, row in frame.iterrows()
        ]
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO intraday_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
            )
            conn.execute(
                "INSERT INTO sync_log (ticker, data_type, source, params, fetched_at, row_count)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (ticker, f"prices_{interval}", source, params, now, len(rows)),
            )
        logger.info(
            "Cachade %d intradagsrader (%s) för %s (källa: %s).",
            len(rows),
            interval,
            ticker,
            source,
        )

    def load_intraday(self, ticker: str, interval: str) -> pd.DataFrame | None:
        """Läser cachad intradagshistorik för ett intervall, eller None."""
        with self._connect() as conn:
            frame = pd.read_sql_query(
                "SELECT ts AS date, open, high, low, close, volume FROM intraday_prices"
                " WHERE ticker = ? AND interval = ? ORDER BY ts",
                conn,
                params=(ticker, interval),
                parse_dates=["date"],
                index_col="date",
            )
        return None if frame.empty else frame

    def store_fundamentals(self, data: FundamentalData) -> None:
        """Sparar fundamenta som JSON och loggar hämtningen."""
        payload = json.dumps(asdict(data), ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO fundamentals VALUES (?, ?, ?, ?)",
                (data.ticker, data.fetched_at, data.source, payload),
            )
            conn.execute(
                "INSERT INTO sync_log (ticker, data_type, source, params, fetched_at, row_count)"
                " VALUES (?, 'fundamentals', ?, NULL, ?, 1)",
                (data.ticker, data.source, data.fetched_at),
            )

    def load_fundamentals(self, ticker: str) -> FundamentalData | None:
        """Läser cachade fundamenta, eller None om de saknas."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM fundamentals WHERE ticker = ?", (ticker,)
            ).fetchone()
        if row is None:
            return None
        return FundamentalData(**json.loads(row["payload"]))

    def last_synced_at(self, ticker: str, data_type: str) -> datetime | None:
        """Returnerar tidpunkten för senaste lyckade hämtning, eller None."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(fetched_at) AS ts FROM sync_log" " WHERE ticker = ? AND data_type = ?",
                (ticker, data_type),
            ).fetchone()
        if row is None or row["ts"] is None:
            return None
        return datetime.fromisoformat(row["ts"])

    def is_fresh(self, ticker: str, data_type: str, max_age_hours: float) -> bool:
        """Avgör om cachen är färsk nog att slippa nytt API-anrop."""
        synced = self.last_synced_at(ticker, data_type)
        if synced is None:
            return False
        return datetime.now(UTC) - synced < timedelta(hours=max_age_hours)
