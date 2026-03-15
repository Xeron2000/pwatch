"""Utility helpers for reading and writing pwatch configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from pwatch.paths import get_config_path


def write_config(config: Dict[str, Any], path: Path | None = None) -> None:
    """Persist the configuration dictionary to disk as YAML."""
    if path is None:
        path = get_config_path()
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            config,
            fh,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            indent=2,
        )
