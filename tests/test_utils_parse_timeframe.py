"""
Tests for utils/parse_timeframe.py - Timeframe parsing functionality.
"""

import pytest

from pwatch.utils.parse_timeframe import parse_timeframe


class TestParseTimeframe:
    """Test cases for parse_timeframe function."""

    def test_parse_timeframe_minutes(self):
        """Test parsing minutes timeframe."""
        assert parse_timeframe("5m") == 5
        assert parse_timeframe("15m") == 15
        assert parse_timeframe("60m") == 60
        assert parse_timeframe("1m") == 1
        assert parse_timeframe("120m") == 120

    def test_parse_timeframe_hours(self):
        """Test parsing hours timeframe."""
        assert parse_timeframe("1h") == 60
        assert parse_timeframe("2h") == 120
        assert parse_timeframe("24h") == 1440
        assert parse_timeframe("0.5h") == 30  # Half hour

    def test_parse_timeframe_days(self):
        """Test parsing days timeframe."""
        assert parse_timeframe("1d") == 1440
        assert parse_timeframe("2d") == 2880
        assert parse_timeframe("7d") == 10080
        assert parse_timeframe("0.5d") == 720  # Half day

    def test_parse_timeframe_invalid_format(self):
        """Test parsing invalid timeframe format."""
        with pytest.raises(ValueError, match="Invalid timeframe format"):
            parse_timeframe("5x")

        with pytest.raises(ValueError, match="Invalid timeframe format"):
            parse_timeframe("5")

        with pytest.raises(ValueError, match="Invalid timeframe format"):
            parse_timeframe("m5")

        with pytest.raises(ValueError, match="Invalid timeframe format"):
            parse_timeframe("")

    def test_parse_timeframe_non_numeric(self):
        """Test parsing timeframe with non-numeric values."""
        with pytest.raises(ValueError):
            parse_timeframe("xm")

        with pytest.raises(ValueError):
            parse_timeframe("abc")

        with pytest.raises(ValueError):
            parse_timeframe("1.2.3h")

    def test_parse_timeframe_zero_values(self):
        """Test parsing zero timeframe values."""
        assert parse_timeframe("0m") == 0
        assert parse_timeframe("0h") == 0
        assert parse_timeframe("0d") == 0

    def test_parse_timeframe_negative_values(self):
        """Test parsing negative timeframe values."""
        with pytest.raises(ValueError):
            parse_timeframe("-5m")

        with pytest.raises(ValueError):
            parse_timeframe("-1h")

        with pytest.raises(ValueError):
            parse_timeframe("-2d")

    def test_parse_timeframe_decimal_values(self):
        """Test parsing decimal timeframe values."""
        assert parse_timeframe("0.5m") == 0  # Should truncate to int
        assert parse_timeframe("1.5m") == 1
        assert parse_timeframe("2.7h") == 162  # 2.7 * 60 = 162
        assert parse_timeframe("0.25d") == 360  # 0.25 * 1440 = 360

    def test_parse_timeframe_large_values(self):
        """Test parsing large timeframe values."""
        assert parse_timeframe("1000m") == 1000
        assert parse_timeframe("100h") == 6000
        assert parse_timeframe("30d") == 43200

    def test_parse_timeframe_whitespace(self):
        """Test parsing timeframe with whitespace."""
        with pytest.raises(ValueError):
            parse_timeframe("5 m")

        with pytest.raises(ValueError):
            parse_timeframe("5m ")

        with pytest.raises(ValueError):
            parse_timeframe(" 5m")

    def test_parse_timeframe_case_sensitivity(self):
        """Test parsing timeframe with different cases."""
        with pytest.raises(ValueError):
            parse_timeframe("5M")  # Uppercase M

        with pytest.raises(ValueError):
            parse_timeframe("5H")  # Uppercase H

        with pytest.raises(ValueError):
            parse_timeframe("5D")  # Uppercase D

    def test_parse_timeframe_edge_cases(self):
        """Test edge cases for timeframe parsing."""
        # Single character
        with pytest.raises(ValueError):
            parse_timeframe("m")

        # Just numbers
        with pytest.raises(ValueError):
            parse_timeframe("5")

        # Multiple letters
        with pytest.raises(ValueError):
            parse_timeframe("5mm")

        # Mixed case
        with pytest.raises(ValueError):
            parse_timeframe("5mH")

    def test_parse_timeframe_conversions(self):
        """Test that time conversions are correct."""
        # 1 hour = 60 minutes
        assert parse_timeframe("1h") == 60

        # 1 day = 1440 minutes (24 * 60)
        assert parse_timeframe("1d") == 1440

        # 2 days = 2880 minutes
        assert parse_timeframe("2d") == 2880

        # 30 minutes = 30 minutes
        assert parse_timeframe("30m") == 30

    def test_parse_timeframe_float_precision(self):
        """Test parsing with float precision."""
        # Test that floating point values are properly truncated
        assert parse_timeframe("1.9m") == 1
        assert parse_timeframe("2.1h") == 126  # 2.1 * 60 = 126
        assert parse_timeframe("1.1d") == 1584  # 1.1 * 1440 = 1584

    def test_parse_timeframe_very_small_decimals(self):
        """Test parsing very small decimal values."""
        assert parse_timeframe("0.1m") == 0
        assert parse_timeframe("0.01h") == 0
        assert parse_timeframe("0.001d") == 0

    def test_parse_timeframe_string_numbers(self):
        """Test parsing with string numbers."""
        with pytest.raises(ValueError):
            parse_timeframe("five m")

        with pytest.raises(ValueError):
            parse_timeframe("one h")

        with pytest.raises(ValueError):
            parse_timeframe("two d")
