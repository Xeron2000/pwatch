"""
Tests for utils/load_config.py - Configuration loading functionality.
"""

from unittest.mock import mock_open, patch

import pytest
import yaml

from pwatch.paths import get_config_path, get_symbols_path
from pwatch.utils.load_config import load_config

EXPECTED_SYMBOLS_PATH = str(get_symbols_path())


class TestLoadConfig:
    """Test cases for load_config function."""

    def test_load_config_success(self):
        """Test successful configuration loading."""
        config_data = {
            "exchange": "binance",
            "defaultTimeframe": "5m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationTimezone": "Asia/Shanghai",
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))), patch(
            "pwatch.utils.load_config.logging"
        ) as mock_logging:
            result = load_config("test_config.yaml")

            expected = {
                **config_data,
                "symbolsFilePath": EXPECTED_SYMBOLS_PATH,
                "checkInterval": config_data["defaultTimeframe"],
            }

            assert result == expected
            mock_logging.error.assert_not_called()

    def test_load_config_missing_required_key(self):
        """Test configuration loading with missing required key."""
        config_data = {
            "exchange": "binance",
            # Missing defaultTimeframe, defaultThreshold,
            # notificationChannels, notificationTimezone
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))), patch(
            "pwatch.utils.load_config.logging"
        ):
            with pytest.raises(
                ValueError, match="Missing required config key: defaultTimeframe"
            ):
                load_config("test_config.yaml")

    def test_load_config_missing_timezone(self):
        """Test configuration loading with missing timezone (should use default)."""
        config_data = {
            "exchange": "binance",
            "defaultTimeframe": "5m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationTimezone": "",  # Empty timezone
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))), patch(
            "pwatch.utils.load_config.logging"
        ):
            result = load_config("test_config.yaml")

            assert result["notificationTimezone"] == "Asia/Shanghai"
            assert result["checkInterval"] == config_data["defaultTimeframe"]

    def test_load_config_file_not_found(self):
        """Test configuration loading when file is not found."""
        with patch(
            "builtins.open", side_effect=FileNotFoundError("File not found")
        ), patch("pwatch.utils.load_config.logging") as mock_logging:
            with pytest.raises(Exception):
                load_config("nonexistent_config.yaml")

            mock_logging.error.assert_called()

    def test_load_config_invalid_yaml(self):
        """Test configuration loading with invalid YAML."""
        invalid_yaml = "invalid: yaml: content: [unclosed"

        with patch("builtins.open", mock_open(read_data=invalid_yaml)), patch(
            "pwatch.utils.load_config.logging"
        ) as mock_logging:
            with pytest.raises(Exception):
                load_config("invalid_config.yaml")

            mock_logging.error.assert_called()

    def test_load_config_empty_file(self):
        """Test configuration loading with empty file."""
        with patch("builtins.open", mock_open(read_data="")), patch(
            "pwatch.utils.load_config.logging"
        ):
            with pytest.raises(
                ValueError, match="Missing required config key: exchange"
            ):
                load_config("empty_config.yaml")

    def test_load_config_extra_keys(self):
        """Test configuration loading with extra keys (should be preserved)."""
        config_data = {
            "exchange": "binance",
            "defaultTimeframe": "5m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationTimezone": "Asia/Shanghai",
            "extraKey": "extraValue",
            "anotherExtra": {"nested": "value"},
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))), patch(
            "pwatch.utils.load_config.logging"
        ):
            result = load_config("test_config.yaml")

            expected = {
                **config_data,
                "symbolsFilePath": EXPECTED_SYMBOLS_PATH,
                "checkInterval": config_data["defaultTimeframe"],
            }
            assert result == expected
            assert "extraKey" in result
            assert "anotherExtra" in result

    def test_load_config_different_data_types(self):
        """Test configuration loading with different data types."""
        config_data = {
            "exchange": "binance",
            "defaultTimeframe": "15m",
            "defaultThreshold": 2.5,
            "notificationChannels": ["telegram"],
            "notificationTimezone": "UTC",
            "enableFeature": True,
            "maxRetries": 3,
            "timeout": 30.5,
            "nestedConfig": {"key1": "value1", "key2": ["item1", "item2"]},
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))), patch(
            "pwatch.utils.load_config.logging"
        ):
            result = load_config("test_config.yaml")

            expected = {
                **config_data,
                "symbolsFilePath": EXPECTED_SYMBOLS_PATH,
                "checkInterval": config_data["defaultTimeframe"],
            }
            assert result == expected
            assert isinstance(result["notificationChannels"], list)
            assert isinstance(result["enableFeature"], bool)
            assert isinstance(result["maxRetries"], int)
            assert isinstance(result["timeout"], float)
            assert isinstance(result["nestedConfig"], dict)

    def test_load_config_default_path(self):
        """Test configuration loading with default path."""
        config_data = {
            "exchange": "binance",
            "defaultTimeframe": "5m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationTimezone": "Asia/Shanghai",
        }

        mock_file = mock_open(read_data=yaml.dump(config_data))
        with patch("builtins.open", mock_file), patch("pwatch.utils.load_config.logging"):
            result = load_config()  # No path specified

            expected = {
                **config_data,
                "symbolsFilePath": EXPECTED_SYMBOLS_PATH,
                "checkInterval": config_data["defaultTimeframe"],
            }

            assert result == expected
            mock_file.assert_called_once_with(str(get_config_path()), "r")

    def test_load_config_custom_check_interval(self):
        """Test configuration loading when a custom check interval is provided."""
        config_data = {
            "exchange": "binance",
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationTimezone": "Asia/Shanghai",
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))), patch(
            "pwatch.utils.load_config.logging"
        ):
            result = load_config("test_config.yaml")

            assert result["checkInterval"] == "1m"
            assert result["symbolsFilePath"] == EXPECTED_SYMBOLS_PATH

    def test_load_config_timezone_none(self):
        """Test configuration loading with timezone as None."""
        config_data = {
            "exchange": "binance",
            "defaultTimeframe": "5m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationTimezone": None,
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))), patch(
            "pwatch.utils.load_config.logging"
        ):
            result = load_config("test_config.yaml")

            assert result["notificationTimezone"] == "Asia/Shanghai"
            assert result["symbolsFilePath"] == EXPECTED_SYMBOLS_PATH
            assert result["checkInterval"] == config_data["defaultTimeframe"]

    def test_load_config_special_characters(self):
        """Test configuration loading with special characters in values."""
        config_data = {
            "exchange": "binance",
            "defaultTimeframe": "5m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationTimezone": "Asia/Shanghai",
            "message": "Price 🚀 UP! BTC: $50,000.00",
            "path": "/path/with/special/chars/测试.yaml",
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))), patch(
            "pwatch.utils.load_config.logging"
        ):
            result = load_config("test_config.yaml")

            expected = {
                **config_data,
                "symbolsFilePath": EXPECTED_SYMBOLS_PATH,
                "checkInterval": config_data["defaultTimeframe"],
            }

            assert result == expected
            assert "🚀" in result["message"]
            assert "测试" in result["path"]

    def test_load_config_numeric_string_threshold(self):
        """Test configuration loading with numeric string threshold."""
        config_data = {
            "exchange": "binance",
            "defaultTimeframe": "5m",
            "defaultThreshold": "2.5",  # String instead of float
            "notificationChannels": ["telegram"],
            "notificationTimezone": "Asia/Shanghai",
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))), patch(
            "pwatch.utils.load_config.logging"
        ):
            result = load_config("test_config.yaml")

            assert result["symbolsFilePath"] == EXPECTED_SYMBOLS_PATH
            assert result["defaultThreshold"] == "2.5"  # Should preserve as string
            assert result["checkInterval"] == config_data["defaultTimeframe"]

    def test_load_config_boolean_threshold(self):
        """Test configuration loading with boolean threshold (edge case)."""
        config_data = {
            "exchange": "binance",
            "defaultTimeframe": "5m",
            "defaultThreshold": True,  # Boolean instead of number
            "notificationChannels": ["telegram"],
            "notificationTimezone": "Asia/Shanghai",
        }

        with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))), patch(
            "pwatch.utils.load_config.logging"
        ):
            result = load_config("test_config.yaml")

            assert result["symbolsFilePath"] == EXPECTED_SYMBOLS_PATH
            assert result["defaultThreshold"] is True  # Should preserve as boolean
            assert result["checkInterval"] == config_data["defaultTimeframe"]
