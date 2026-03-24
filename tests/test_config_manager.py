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

def test_default_config_includes_conservative_auto_mode_profile(tmp_path):
    manager = ConfigManager(config_path=Path(tmp_path) / "missing-config.yaml")
    config = manager.get_config()

    assert config["autoModeProfile"] == "conservative"
    assert config["autoModeLimit"] == 40
    assert config["autoModeMinQuoteVolume24h"] == 80_000_000
    assert config["autoModeMinOpenInterestUsd"] == 25_000_000
    assert config["autoModeMinListingAgeDays"] == 45
    assert config["autoModeMaxRecentVolatilityPct"] == 6.0


def test_update_config_applies_balanced_profile_defaults_when_values_missing(tmp_path, sample_config, monkeypatch):
    monkeypatch.setattr(
        "pwatch.core.config_manager.load_usdt_contracts",
        lambda exchange: ["BTC/USDT:USDT"],
    )
    manager = _create_manager(tmp_path, sample_config)

    candidate = copy.deepcopy(sample_config)
    candidate["notificationSymbols"] = "auto"
    candidate["autoModeProfile"] = "balanced"
    candidate.pop("autoModeLimit", None)
    candidate.pop("autoModeMinQuoteVolume24h", None)
    candidate.pop("autoModeMinOpenInterestUsd", None)
    candidate.pop("autoModeMinListingAgeDays", None)
    candidate.pop("autoModeMaxRecentVolatilityPct", None)

    result = manager.update_config(candidate)

    assert result.success
    assert result.config["autoModeProfile"] == "balanced"
    assert result.config["autoModeLimit"] == 50
    assert result.config["autoModeMinQuoteVolume24h"] == 50_000_000
    assert result.config["autoModeMinOpenInterestUsd"] == 15_000_000
    assert result.config["autoModeMinListingAgeDays"] == 30
    assert result.config["autoModeMaxRecentVolatilityPct"] == 8.0
