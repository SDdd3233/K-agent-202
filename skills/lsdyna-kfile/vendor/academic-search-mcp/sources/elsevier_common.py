"""Shared helpers for pybliometrics-backed Elsevier sources."""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from pybliometrics import init as pybliometrics_init
from pybliometrics.utils.constants import CONFIG_FILE

from utils.errors import DataSourceError


_init_lock = Lock()
_initialised = False


def ensure_pybliometrics_config(source: str) -> None:
    """Initialise pybliometrics from its configured file.

    pybliometrics creates a config interactively when the file is absent.  MCP
    servers cannot prompt, so missing or invalid config is reported explicitly.
    """
    config_path = Path(CONFIG_FILE)
    if not config_path.exists():
        raise DataSourceError(
            source,
            f"pybliometrics config not found at {config_path}",
        )

    global _initialised
    with _init_lock:
        if _initialised:
            return
        try:
            pybliometrics_init(config_path=config_path)
        except (FileNotFoundError, ValueError) as exc:
            raise DataSourceError(
                source,
                f"pybliometrics config is invalid at {config_path}: {exc}",
                original_error=exc,
            ) from exc
        _initialised = True


def year_from_date(value: str | None) -> int | None:
    """Extract a publication year from an ISO-like date string."""
    if not value or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None
