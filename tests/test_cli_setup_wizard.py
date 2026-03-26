from unittest.mock import patch

import yaml

from pwatch.app.cli import ensure_config_exists, interactive_config


def test_interactive_config_english_copy_matches_current_auto_mode(capsys):
    inputs = iter([
        "1",  # language
        "okx",
        "5m",
        "1m",
        "1",
        "Asia/Shanghai",
        "",  # auto mode
        "123456789",  # chat id
        "n",  # advanced options
    ])

    with patch("builtins.input", side_effect=lambda prompt="": next(inputs)), patch(
        "getpass.getpass", return_value="123456:token"
    ):
        config = interactive_config()

    captured = capsys.readouterr().out

    assert config["notificationSymbols"] == "auto"
    assert "Welcome to pwatch setup" in captured
    assert "PriceSentry Configuration Wizard" not in captured
    assert "quality-filtered" in captured
    assert "top 20" not in captured


def test_ensure_config_exists_uses_bilingual_first_run_message(tmp_path, capsys):
    expected_config = {"exchange": "okx"}

    with patch("pwatch.app.cli.get_config_path", return_value=tmp_path / "config.yaml"), patch(
        "pwatch.app.cli.interactive_config", return_value=expected_config
    ):
        config_path = ensure_config_exists()

    captured = capsys.readouterr().out

    assert config_path.exists()
    assert yaml.safe_load(config_path.read_text(encoding="utf-8")) == expected_config
    assert "No config file found. Starting interactive setup" in captured
    assert "未找到配置文件，开始交互式配置" in captured
    assert "Config saved to" in captured


def test_interactive_config_no_longer_emits_chart_config_or_prompts(capsys):
    inputs = iter([
        "1",  # language
        "okx",
        "5m",
        "1m",
        "1",
        "Asia/Shanghai",
        "",  # auto mode
        "123456789",  # chat id
        "n",  # advanced options
    ])

    with patch("builtins.input", side_effect=lambda prompt="": next(inputs)), patch(
        "getpass.getpass", return_value="123456:token"
    ):
        config = interactive_config()

    captured = capsys.readouterr().out

    assert "chart_section" not in config
    assert "attachChart" not in config
    assert "chartTimeframe" not in config
    assert "chartLookbackMinutes" not in config
    assert "chartTheme" not in config
    assert "chartImageWidth" not in config
    assert "chartImageHeight" not in config
    assert "chartImageScale" not in config
    assert "Chart Settings" not in captured
    assert "Chart theme" not in captured
    assert "Chart lookback minutes" not in captured

def test_interactive_config_requires_non_empty_chat_id(monkeypatch):
    inputs = iter([
        "1",  # language
        "okx",
        "5m",
        "1m",
        "1",
        "Asia/Shanghai",
        "",  # auto mode
        "",  # first empty chat id should be rejected
        "123456789",  # second attempt succeeds
        "n",
    ])

    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "123456:token")

    config = interactive_config()

    assert config["telegram"]["chatId"] == "123456789"