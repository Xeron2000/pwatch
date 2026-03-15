"""Tests for core.config_manager behaviour with notification symbol constraints."""

import copy
from pathlib import Path

import yaml

from pwatch.core.config_manager import ConfigManager


def _create_manager(tmp_path, base_config):
    config_path = Path(tmp_path) / "config.yaml"
    with config_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(base_config, fh)
    return ConfigManager(config_path=config_path)


def test_update_config_rejects_empty_notification_symbols(tmp_path, sample_config, monkeypatch):
    """Empty notification symbol lists must fail validation."""
    monkeypatch.setattr(
        "pwatch.core.config_manager.load_usdt_contracts",
        lambda exchange: ["BTC/USDT:USDT"],
    )
    manager = _create_manager(tmp_path, sample_config)

    candidate = copy.deepcopy(sample_config)
    candidate["notificationSymbols"] = []

    result = manager.update_config(candidate)

    assert not result.success
    assert any("notification" in error.lower() for error in result.errors)


def test_update_config_rejects_non_matching_symbols(tmp_path, sample_config, monkeypatch):
    """Reject updates when no selected symbols match supported contracts."""
    manager = _create_manager(tmp_path, sample_config)

    candidate = copy.deepcopy(sample_config)
    candidate["notificationSymbols"] = ["DOGE/USDT:USDT"]

    monkeypatch.setattr(
        "pwatch.core.config_manager.load_usdt_contracts",
        lambda exchange: ["BTC/USDT:USDT"],
    )

    result = manager.update_config(candidate)

    assert not result.success
    assert any("no valid notification symbols" in error.lower() for error in result.errors)
