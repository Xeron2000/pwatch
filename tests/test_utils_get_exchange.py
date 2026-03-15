"""
Tests for utils/get_exchange.py - Exchange factory functionality.
"""

import pytest

from pwatch.utils.get_exchange import get_exchange


class TestGetExchange:
    """Test cases for get_exchange function."""

    def test_get_exchange_binance(self):
        """Test getting Binance exchange instance."""
        from pwatch.exchanges.binance import BinanceExchange

        result = get_exchange("binance")

        assert isinstance(result, BinanceExchange)

    def test_get_exchange_binance_uppercase(self):
        """Test getting Binance exchange with uppercase name."""
        from pwatch.exchanges.binance import BinanceExchange

        result = get_exchange("BINANCE")

        assert isinstance(result, BinanceExchange)

    def test_get_exchange_binance_mixed_case(self):
        """Test getting Binance exchange with mixed case name."""
        from pwatch.exchanges.binance import BinanceExchange

        result = get_exchange("Binance")

        assert isinstance(result, BinanceExchange)

    def test_get_exchange_okx(self):
        """Test getting OKX exchange instance."""
        from pwatch.exchanges.okx import OkxExchange

        result = get_exchange("okx")

        assert isinstance(result, OkxExchange)

    def test_get_exchange_okx_uppercase(self):
        """Test getting OKX exchange with uppercase name."""
        from pwatch.exchanges.okx import OkxExchange

        result = get_exchange("OKX")

        assert isinstance(result, OkxExchange)

    def test_get_exchange_bybit(self):
        """Test getting Bybit exchange instance."""
        from pwatch.exchanges.bybit import BybitExchange

        result = get_exchange("bybit")

        assert isinstance(result, BybitExchange)

    def test_get_exchange_bybit_uppercase(self):
        """Test getting Bybit exchange with uppercase name."""
        from pwatch.exchanges.bybit import BybitExchange

        result = get_exchange("BYBIT")

        assert isinstance(result, BybitExchange)

    def test_get_exchange_unsupported(self):
        """Test getting unsupported exchange."""
        with pytest.raises(ValueError, match="Exchange unsupported not supported."):
            get_exchange("unsupported")

    def test_get_exchange_empty_string(self):
        """Test getting exchange with empty string."""
        with pytest.raises(ValueError, match="Exchange   not supported."):
            get_exchange("")

    def test_get_exchange_none(self):
        """Test getting exchange with None."""
        with pytest.raises(ValueError, match="Exchange None not supported."):
            get_exchange(None)

    def test_get_exchange_whitespace(self):
        """Test getting exchange with whitespace."""
        with pytest.raises(ValueError, match="Exchange   not supported."):
            get_exchange("   ")

    def test_get_exchange_partial_match(self):
        """Test getting exchange with partial name match."""
        with pytest.raises(ValueError, match="Exchange bin not supported."):
            get_exchange("bin")

    def test_get_exchange_special_characters(self):
        """Test getting exchange with special characters."""
        with pytest.raises(ValueError, match="Exchange bin@nce not supported."):
            get_exchange("bin@nce")

    def test_get_exchange_numbers(self):
        """Test getting exchange with numbers."""
        with pytest.raises(ValueError, match="Exchange 123 not supported."):
            get_exchange("123")

    def test_get_exchange_case_insensitive_behavior(self):
        """Test that exchange names are case insensitive."""
        test_cases = [
            ("binance", "BinanceExchange"),
            ("BINANCE", "BinanceExchange"),
            ("Binance", "BinanceExchange"),
            ("okx", "OkxExchange"),
            ("OKX", "OkxExchange"),
            ("Okx", "OkxExchange"),
            ("bybit", "BybitExchange"),
            ("BYBIT", "BybitExchange"),
            ("Bybit", "BybitExchange"),
        ]

        for exchange_name, expected_class_name in test_cases:
            result = get_exchange(exchange_name)

            # Check that the result is an instance of the expected class
            if "Binance" in expected_class_name:
                from pwatch.exchanges.binance import BinanceExchange

                assert isinstance(result, BinanceExchange)
            elif "Okx" in expected_class_name:
                from pwatch.exchanges.okx import OkxExchange

                assert isinstance(result, OkxExchange)
            elif "Bybit" in expected_class_name:
                from pwatch.exchanges.bybit import BybitExchange

                assert isinstance(result, BybitExchange)

    def test_get_exchange_returns_new_instance(self):
        """Test that each call returns a new instance."""
        from pwatch.exchanges.binance import BinanceExchange

        result1 = get_exchange("binance")
        result2 = get_exchange("binance")

        assert isinstance(result1, BinanceExchange)
        assert isinstance(result2, BinanceExchange)
        assert result1 is not result2  # Different instances
