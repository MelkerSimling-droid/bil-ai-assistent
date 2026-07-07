"""Loggning: konsol + roterande loggfiler i logs/-mappen."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.utils.config import PROJECT_ROOT

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_configured = False


def setup_logging(level: str = "INFO", directory: Path | None = None) -> None:
    """Initierar loggning för hela applikationen. Idempotent.

    Args:
        level: Loggnivå som sträng, t.ex. "INFO" eller "DEBUG".
        directory: Katalog för loggfiler. Standard: logs/ i projektroten.
    """
    global _configured
    if _configured:
        return

    log_dir = directory or (PROJECT_ROOT / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(_LOG_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        log_dir / "aktiesystem.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Dämpa pratiga tredjepartsbibliotek.
    for noisy in ("urllib3", "yfinance", "peewee"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Returnerar en namngiven logger; initierar loggning vid behov.

    Args:
        name: Loggerns namn, normalt ``__name__``.

    Returns:
        En konfigurerad :class:`logging.Logger`.
    """
    setup_logging()
    return logging.getLogger(name)
