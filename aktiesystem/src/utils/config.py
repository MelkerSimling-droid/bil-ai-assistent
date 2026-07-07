"""Central konfigurationshantering.

Läser config/config.yaml och miljövariabler från .env.
API-nycklar hämtas ENDAST via miljövariabler — aldrig från YAML-filen.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Projektroten = två nivåer upp från denna fil (src/utils/config.py).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


class ConfigError(Exception):
    """Fel vid inläsning eller validering av konfiguration."""


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Läser in YAML-konfigurationen och .env-filen.

    Args:
        config_path: Sökväg till config.yaml. Standard: config/config.yaml
            i projektroten.

    Returns:
        Konfigurationen som en nästlad dict.

    Raises:
        ConfigError: Om filen saknas, inte kan parsas eller saknar
            obligatoriska nycklar.
    """
    path = config_path or DEFAULT_CONFIG_PATH
    # Ladda .env från projektroten och config/ — befintliga env-variabler vinner.
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(PROJECT_ROOT / "config" / ".env")

    if not path.exists():
        raise ConfigError(f"Konfigurationsfil saknas: {path}")
    try:
        with open(path, encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Kunde inte parsa {path}: {exc}") from exc

    if not isinstance(config, dict):
        raise ConfigError(f"{path} innehåller ingen giltig konfiguration.")

    required_sections = ["watchlist", "data", "risk", "backtest"]
    missing = [key for key in required_sections if key not in config]
    if missing:
        raise ConfigError(f"Saknade sektioner i {path}: {', '.join(missing)}")
    return config


def get_api_key(name: str) -> str | None:
    """Hämtar en API-nyckel från miljövariabler.

    Args:
        name: Miljövariabelns namn, t.ex. "ALPHA_VANTAGE_API_KEY".

    Returns:
        Nyckelns värde, eller None om den inte är satt. Platshållarvärden
        från .env.example behandlas som att nyckeln saknas.
    """
    value = os.environ.get(name)
    if value is None or value.strip() in ("", "din_nyckel_har"):
        return None
    return value


def resolve_path(relative: str) -> Path:
    """Gör en projektrelativ sökväg absolut utifrån projektroten.

    Args:
        relative: Sökväg relativt projektroten, t.ex. "data/raw/x.sqlite".

    Returns:
        Absolut sökväg. Kataloger som saknas skapas INTE här.
    """
    path = Path(relative)
    return path if path.is_absolute() else PROJECT_ROOT / path
