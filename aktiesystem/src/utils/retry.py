"""Retry med exponentiell backoff för nätverksanrop."""

from __future__ import annotations

import time
from collections.abc import Callable

from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


def with_retries[T](
    operation: Callable[[], T],
    description: str,
    max_retries: int = 4,
    backoff_base_seconds: float = 2.0,
) -> T:
    """Kör en operation med retries och exponentiell backoff.

    Väntetiden mellan försök är ``backoff_base_seconds * 2**försök``,
    dvs. 2 s, 4 s, 8 s ... med standardvärden.

    Args:
        operation: Funktion utan argument som utför anropet.
        description: Beskrivning för loggmeddelanden, t.ex. "OHLCV AAPL".
        max_retries: Max antal försök totalt (inklusive det första).
        backoff_base_seconds: Basväntetid i sekunder.

    Returns:
        Operationens resultat.

    Raises:
        Exception: Det sista felet, om alla försök misslyckas.
    """
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001 — nätverksfel kan vara vad som helst
            last_error = exc
            wait = backoff_base_seconds * (2**attempt)
            logger.warning(
                "Försök %d/%d misslyckades för %s: %s", attempt + 1, max_retries, description, exc
            )
            if attempt < max_retries - 1:
                time.sleep(wait)
    assert last_error is not None
    raise last_error
