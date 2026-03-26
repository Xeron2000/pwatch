"""Centralized path management for pwatch (XDG-compliant)."""

import os
from pathlib import Path


def get_config_dir() -> Path:
    """Return the pwatch configuration directory."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) / "pwatch" if xdg else Path.home() / ".config" / "pwatch"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_config_path() -> Path:
    """Return path to config.yaml."""
    return get_config_dir() / "config.yaml"


def get_markets_path() -> Path:
    """Return path to supported_markets.json."""
    return get_config_dir() / "supported_markets.json"


def get_symbols_path() -> Path:
    """Return path to symbols.txt."""
    return get_config_dir() / "symbols.txt"


def get_pid_path() -> Path:
    """Return path to pwatch.pid."""
    return get_config_dir() / "pwatch.pid"


def get_log_path() -> Path:
    """Return path to pwatch.log."""
    return get_config_dir() / "pwatch.log"