"""
Test cases for configuration validation system.
"""

import os
import tempfile

from pwatch.utils.config_validator import ValidationResult, config_validator


class TestConfigValidator:
    """Test configuration validation functionality."""

    def test_valid_configuration(self):
        """Test validation of a valid configuration."""
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "symbolsFilePath": "config/symbols.txt",
            "notificationChannels": ["telegram"],
            "notificationSymbols": ["BTC/USDT:USDT"],
            "telegram": {"token": "123456789:ABCdef123456", "chatId": "123456789"},
            "notificationTimezone": "Asia/Shanghai",
            "logLevel": "INFO",
        }

        result = config_validator.validate_config(config)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        config = {}

        result = config_validator.validate_config(config)
        assert not result.is_valid
        assert len(result.errors) > 0

        error_messages = [str(error) for error in result.errors]
        assert any("exchange" in msg.lower() for msg in error_messages)
        assert any("timeframe" in msg.lower() for msg in error_messages)
        assert any("threshold" in msg.lower() for msg in error_messages)
        assert any(
            "notification" in msg.lower() and "symbol" in msg.lower()
            for msg in error_messages
        )

    def test_invalid_exchange(self):
        """Test validation fails with invalid exchange."""
        config = {
            "exchange": "invalid_exchange",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "symbolsFilePath": "config/symbols.txt",
            "notificationChannels": ["telegram"],
            "notificationSymbols": ["BTC/USDT:USDT"],
        }

        result = config_validator.validate_config(config)
        assert not result.is_valid
        assert any("exchange" in str(error).lower() for error in result.errors)

    def test_invalid_timeframe(self):
        """Test validation fails with invalid timeframe."""
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "invalid_timeframe",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "symbolsFilePath": "config/symbols.txt",
            "notificationChannels": ["telegram"],
            "notificationSymbols": ["BTC/USDT:USDT"],
        }

        result = config_validator.validate_config(config)
        assert not result.is_valid
        assert any("timeframe" in str(error).lower() for error in result.errors)

    def test_invalid_check_interval(self):
        """Test validation fails when checkInterval format is invalid."""
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "invalid",
            "defaultThreshold": 1.0,
            "symbolsFilePath": "config/symbols.txt",
            "notificationChannels": ["telegram"],
            "notificationSymbols": ["BTC/USDT:USDT"],
        }

        result = config_validator.validate_config(config)
        assert not result.is_valid
        assert any("checkinterval" in str(error).lower() for error in result.errors)

    def test_invalid_threshold_range(self):
        """Test validation fails with threshold out of range."""
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 150.0,
            "symbolsFilePath": "config/symbols.txt",
            "notificationChannels": ["telegram"],
            "notificationSymbols": ["BTC/USDT:USDT"],
        }

        result = config_validator.validate_config(config)
        assert not result.is_valid
        assert any("threshold" in str(error).lower() for error in result.errors)

    def test_empty_notification_symbols(self):
        """Test validation fails when notification symbols list is empty."""
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "symbolsFilePath": "config/symbols.txt",
            "notificationChannels": ["telegram"],
            "notificationSymbols": [],
        }

        result = config_validator.validate_config(config)
        assert not result.is_valid
        assert any(
            "notification" in str(error).lower() and "symbol" in str(error).lower()
            for error in result.errors
        )

    def test_invalid_telegram_token(self):
        """Test validation fails with invalid Telegram token."""
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "symbolsFilePath": "config/symbols.txt",
            "notificationChannels": ["telegram"],
            "telegram": {"token": "invalid_token", "chatId": "123456789"},
            "notificationSymbols": ["BTC/USDT:USDT"],
        }

        result = config_validator.validate_config(config)
        assert not result.is_valid
        assert any(
            "telegram" in str(error).lower() and "token" in str(error).lower()
            for error in result.errors
        )

    def test_valid_file_path(self):
        """Test validation of valid file path."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            _ = f.write("test content")
            temp_path = f.name

        try:
            config = {
                "exchange": "binance",
                "exchanges": ["binance", "okx"],
                "defaultTimeframe": "5m",
                "checkInterval": "1m",
                "defaultThreshold": 1.0,
                "symbolsFilePath": temp_path,
                "notificationChannels": ["telegram"],
                "telegram": {"token": "123456789:ABCdef123456", "chatId": "123456789"},
                "notificationSymbols": ["BTC/USDT:USDT"],
            }

            result = config_validator.validate_config(config)
            assert result.is_valid
        finally:
            os.unlink(temp_path)

    def test_invalid_file_path(self):
        """Test validation fails with invalid file path."""
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "symbolsFilePath": "/nonexistent/path/symbols.txt",
            "notificationChannels": ["telegram"],
            "telegram": {"token": "123456789:ABCdef123456", "chatId": "123456789"},
            "notificationSymbols": ["BTC/USDT:USDT"],
        }

        result = config_validator.validate_config(config)
        assert not result.is_valid
        assert any("file" in str(error).lower() for error in result.errors)

    def test_get_config_schema(self):
        """Test getting configuration schema."""
        schema = config_validator.get_config_schema()

        assert isinstance(schema, dict)
        assert "exchange" in schema
        assert "defaultTimeframe" in schema
        assert "checkInterval" in schema
        assert "telegram" in schema
        assert "chartImageWidth" not in schema

        exchange_schema = schema["exchange"]
        assert "required" in exchange_schema
        assert "type" in exchange_schema
        assert "description" in exchange_schema

    def test_validation_result_add_methods(self):
        """Test ValidationResult add methods."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])

        result.add_error("Test error")
        result.add_warning("Test warning")
        result.add_info("Test info")

        assert not result.is_valid
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert len(result.info) == 1
        assert result.errors[0] == "Test error"
        assert result.warnings[0] == "Test warning"
        assert result.info[0] == "Test info"

    def test_partial_valid_configuration_without_chart_fields(self):
        """Config without optional chart fields remains valid and warning-free."""
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "symbolsFilePath": "config/symbols.txt",
            "notificationChannels": [],
            "notificationSymbols": ["BTC/USDT:USDT"],
        }

        result = config_validator.validate_config(config)
        assert result.is_valid
        assert result.warnings == []

    def test_valid_auto_mode_quality_filter_configuration(self):
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationSymbols": "auto",
            "autoModeLimit": 50,
            "autoModeMinQuoteVolume24h": 50000000,
            "autoModeMinOpenInterestUsd": 10000000,
            "autoModeMinListingAgeDays": 30,
            "autoModeMaxRecentVolatilityPct": 10.0,
            "telegram": {"token": "123456789:ABCdef123456", "chatId": "123456789"},
        }

        result = config_validator.validate_config(config)
        assert result.is_valid

    def test_invalid_auto_mode_quality_filter_configuration(self):
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationSymbols": "auto",
            "autoModeLimit": 0,
            "autoModeMinQuoteVolume24h": -1,
            "autoModeMinOpenInterestUsd": -1,
            "autoModeMinListingAgeDays": -1,
            "autoModeMaxRecentVolatilityPct": 0,
            "telegram": {"token": "123456789:ABCdef123456", "chatId": "123456789"},
        }

        result = config_validator.validate_config(config)
        assert not result.is_valid
        assert any("automode" in str(error).lower() for error in result.errors)

    def test_valid_auto_mode_profile_configuration(self):
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationSymbols": "auto",
            "autoModeProfile": "aggressive",
            "telegram": {"token": "123456789:ABCdef123456", "chatId": "123456789"},
        }

        result = config_validator.validate_config(config)
        assert result.is_valid


    def test_missing_telegram_chat_id_is_invalid_when_telegram_enabled(self):
        config = {
            "exchange": "binance",
            "exchanges": ["binance", "okx"],
            "defaultTimeframe": "5m",
            "checkInterval": "1m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationSymbols": ["BTC/USDT:USDT"],
            "telegram": {"token": "123456789:ABCdef123456", "chatId": ""},
        }

        result = config_validator.validate_config(config)

        assert not result.is_valid
        assert any("chat id" in str(error).lower() for error in result.errors)

    def test_webhook_secret_removed_from_schema(self):
        schema = config_validator.get_config_schema()

        assert "webhookSecret" not in schema.get("telegram", {})