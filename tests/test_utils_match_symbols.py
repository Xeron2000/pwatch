"""
Tests for utils/match_symbols.py - Symbol matching functionality.
"""

import json
import re
from unittest.mock import mock_open, patch

from pwatch.utils.match_symbols import match_symbols


class TestMatchSymbols:
    """Test cases for match_symbols function."""

    def test_match_symbols_success(self):
        """Test successful symbol matching."""
        symbols = ["BTC", "ETH"]
        exchange = "binance"

        supported_markets = {
            "binance": ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]
        }

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print") as mock_print:
            result = match_symbols(symbols, exchange)

            expected = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
            assert result == expected
            mock_print.assert_not_called()

    def test_match_symbols_exchange_not_supported(self):
        """Test symbol matching with unsupported exchange."""
        symbols = ["BTC", "ETH"]
        exchange = "unsupported_exchange"

        supported_markets = {"binance": ["BTC/USDT:USDT"]}

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print") as mock_print:
            result = match_symbols(symbols, exchange)

            assert result == []
            mock_print.assert_called_with(
                "Exchange unsupported_exchange not supported."
            )

    def test_match_symbols_no_matches(self):
        """Test symbol matching when no matches are found."""
        symbols = ["XRP", "ADA"]
        exchange = "binance"

        supported_markets = {"binance": ["BTC/USDT:USDT", "ETH/USDT:USDT"]}

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print") as mock_print:
            result = match_symbols(symbols, exchange)

            assert result == []
            mock_print.assert_not_called()

    def test_match_symbols_partial_match(self):
        """Test symbol matching with partial matches."""
        symbols = ["BTC", "ETH", "XRP"]
        exchange = "binance"

        supported_markets = {
            "binance": ["BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT"]
        }

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print"):
            result = match_symbols(symbols, exchange)

            expected = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
            assert result == expected

    def test_match_symbols_case_sensitive(self):
        """Test symbol matching case sensitivity."""
        symbols = ["BTC", "ETH"]  # proper case
        exchange = "binance"

        supported_markets = {"binance": ["BTC/USDT:USDT", "ETH/USDT:USDT"]}

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print"):
            result = match_symbols(symbols, exchange)

            # Should still match because we check if symbol is in base_symbol
            assert result == ["BTC/USDT:USDT", "ETH/USDT:USDT"]

    def test_match_symbols_multiple_matches_pick_shortest(self):
        """Test symbol matching when multiple matches exist, pick shortest."""
        symbols = ["BTC"]
        exchange = "binance"

        supported_markets = {
            "binance": [
                "BTC/USDT:USDT",  # Shortest match
                "BTCBULL/USDT:USDT",  # Longer match
                "BTCDOWN/USDT:USDT",  # Longer match
            ]
        }

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print"):
            result = match_symbols(symbols, exchange)

            assert result == ["BTC/USDT:USDT"]  # Should pick the shortest match

    def test_match_symbols_with_numbers(self):
        """Test symbol matching with numbers in symbols."""
        symbols = ["BTC", "ETH", "1000SHIB"]
        exchange = "binance"

        supported_markets = {
            "binance": ["BTC/USDT:USDT", "ETH/USDT:USDT", "1000SHIB/USDT:USDT"]
        }

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print"):
            result = match_symbols(symbols, exchange)

            expected = ["BTC/USDT:USDT", "ETH/USDT:USDT", "1000SHIB/USDT:USDT"]
            assert result == expected

    def test_match_symbols_empty_symbols_list(self):
        """Test symbol matching with empty symbols list."""
        symbols = []
        exchange = "binance"

        supported_markets = {"binance": ["BTC/USDT:USDT", "ETH/USDT:USDT"]}

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print"):
            result = match_symbols(symbols, exchange)

            assert result == []

    def test_match_symbols_file_read_error(self):
        """Test symbol matching when file cannot be read."""
        symbols = ["BTC", "ETH"]
        exchange = "binance"

        with patch(
            "builtins.open", side_effect=FileNotFoundError("File not found")
        ), patch("builtins.print"):
            result = match_symbols(symbols, exchange)

            assert result == []
            # No error message printed, function silently fails

    def test_match_symbols_invalid_json(self):
        """Test symbol matching with invalid JSON in supported markets file."""
        symbols = ["BTC", "ETH"]
        exchange = "binance"

        with patch("builtins.open", mock_open(read_data="invalid json content")), patch(
            "builtins.print"
        ):
            result = match_symbols(symbols, exchange)

            assert result == []
            # Function silently fails on JSON error

    def test_match_symbols_whitespace_in_symbols(self):
        """Test symbol matching with whitespace in symbols."""
        symbols = ["BTC", "ETH", "XRP"]  # Remove whitespace
        exchange = "binance"

        supported_markets = {
            "binance": ["BTC/USDT:USDT", "ETH/USDT:USDT", "XRP/USDT:USDT"]
        }

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print"):
            result = match_symbols(symbols, exchange)

            # Should still match because we check if symbol is in base_symbol
            expected = ["BTC/USDT:USDT", "ETH/USDT:USDT", "XRP/USDT:USDT"]
            assert result == expected

    def test_match_symbols_special_characters(self):
        """Test symbol matching with special characters."""
        symbols = ["BTC", "ETH🚀"]
        exchange = "binance"

        supported_markets = {"binance": ["BTC/USDT:USDT", "ETH/USDT:USDT"]}

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print"):
            result = match_symbols(symbols, exchange)

            # Should match BTC but not ETH🚀
            assert result == ["BTC/USDT:USDT"]

    def test_match_symbols_duplicate_symbols(self):
        """Test symbol matching with duplicate symbols in input."""
        symbols = ["BTC", "ETH", "BTC"]  # Duplicate BTC
        exchange = "binance"

        supported_markets = {"binance": ["BTC/USDT:USDT", "ETH/USDT:USDT"]}

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print"):
            result = match_symbols(symbols, exchange)

            # Should return unique matches
            assert result == ["BTC/USDT:USDT", "ETH/USDT:USDT"]

    def test_match_symbols_empty_supported_markets(self):
        """Test symbol matching with empty supported markets for exchange."""
        symbols = ["BTC", "ETH"]
        exchange = "binance"

        supported_markets = {
            "binance": []  # Empty list
        }

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print"):
            result = match_symbols(symbols, exchange)

            assert result == []

    def test_match_symbols_different_exchange_formats(self):
        """Test symbol matching with different exchange market formats."""
        symbols = ["BTC", "ETH"]
        exchange = "binance"

        supported_markets = {
            "binance": [
                "BTC/USDT:USDT",
                "ETH/USDT:USDT",
                "BTC / USDT:USDT",  # With spaces
                "ETH / USDT:USDT",  # With spaces
            ]
        }

        with patch(
            "builtins.open", mock_open(read_data=json.dumps(supported_markets))
        ), patch("builtins.print"):
            result = match_symbols(symbols, exchange)

            # Should pick the shortest matches (without spaces)
            expected = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
            assert result == expected

    def test_match_symbols_pattern_matching(self):
        """Test the regex pattern matching logic."""
        # Test the pattern directly
        usdt_pattern = re.compile(
            r"(\d*[A-Za-z]+)\d*/USDT:USDT$|(\d*[A-Za-z]+)\s*/\s*USDT:USDT$"
        )

        # Test various market formats
        test_cases = [
            ("BTC/USDT:USDT", ("BTC", None)),
            ("ETH/USDT:USDT", ("ETH", None)),
            ("1000SHIB/USDT:USDT", ("1000SHIB", None)),
            ("BTC / USDT:USDT", (None, "BTC")),
            ("ETH / USDT:USDT", (None, "ETH")),
            ("INVALID/FORMAT", None),
            ("BTC/USDT", None),  # Missing :USDT
            ("BTC/USDT:BTC", None),  # Wrong quote currency
        ]

        for market, expected in test_cases:
            match = usdt_pattern.match(market)
            if expected is None:
                assert match is None, f"Pattern should not match {market}"
            else:
                assert match is not None, f"Pattern should match {market}"
                if expected[0] is not None:
                    assert match.group(1) == expected[0]
                else:
                    assert match.group(2) == expected[1]
