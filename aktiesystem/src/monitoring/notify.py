"""Notifieringskanaler för bevakningslarm.

MacNotifier visar macOS-notiser via osascript (inga beroenden, ingen
nyckel). Fler kanaler (e-post, Telegram) kan läggas till genom att
implementera samma ``send``-signatur.
"""

from __future__ import annotations

import subprocess
from typing import Protocol

from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


class Notifier(Protocol):
    """Gemensamt interface för notifieringskanaler."""

    def send(self, title: str, message: str) -> bool:
        """Skickar en notis. Returnerar True vid lyckat försök."""
        ...


class MacNotifier:
    """macOS-notiser via osascript (Notistjänsten i systemet)."""

    def send(self, title: str, message: str) -> bool:
        """Visar en macOS-notis. Fel loggas och returnerar False — tyst
        misslyckande utan logg förekommer inte."""
        script = (
            f'display notification "{_escape(message)}" '
            f'with title "Aktiesystem" subtitle "{_escape(title)}"'
        )
        try:
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=10
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.error("macOS-notis kunde inte skickas: %s", exc)
            return False
        if result.returncode != 0:
            logger.error("osascript-fel: %s", result.stderr.strip())
            return False
        return True


class LogNotifier:
    """Skriver larm till loggen — används alltid, som spårbar historik."""

    def send(self, title: str, message: str) -> bool:
        """Loggar larmet på INFO-nivå."""
        logger.info("LARM | %s | %s", title, message)
        return True


def _escape(text: str) -> str:
    """Escapar citattecken och radbrytningar för AppleScript-strängar."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
