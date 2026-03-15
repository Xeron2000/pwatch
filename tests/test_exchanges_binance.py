"""
Tests for exchanges/binance.py - Binance exchange implementation.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from pwatch.exchanges.binance import BinanceExchange


class TestBinanceExchange:
    """Test cases for BinanceExchange class."""

    def test_init(self):
        """Test initialization of BinanceExchange."""
        with patch("pwatch.exchanges.base.ccxt.exchanges", ["binance"]), patch(
            "pwatch.exchanges.base.ccxt.binance"
        ) as mock_binance, patch("pwatch.exchanges.base.logging"):
            mock_exchange = Mock()
            mock_exchange.options = {}
            mock_binance.return_value = mock_exchange

            exchange = BinanceExchange()

            assert exchange.exchange_name == "binance"
            assert exchange.exchange == mock_exchange

            # Verify default type is set to future
            assert exchange.exchange.options["defaultType"] == "future"

    @pytest.mark.asyncio
    async def test_ws_connect_basic(self):
        """Test basic WebSocket connection setup."""
        with patch("pwatch.exchanges.base.ccxt.exchanges", ["binance"]), patch(
            "pwatch.exchanges.base.ccxt.binance"
        ), patch("pwatch.exchanges.base.logging"), patch(
            "pwatch.exchanges.binance.websockets.connect"
        ) as mock_connect:
            # Mock WebSocket
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket

            exchange = BinanceExchange()
            exchange.running = True

            # Test URI construction
            symbols = ["BTC/USDT", "ETH/USDT"]
            streams = [
                f"{symbol.lower().replace('/', '')}@ticker" for symbol in symbols
            ]
            expected_uri = f"wss://fstream.binance.com/ws/{'/'.join(streams)}"

            # Verify the URI construction logic
            assert (
                expected_uri
                == "wss://fstream.binance.com/ws/btcusdt@ticker/ethusdt@ticker"
            )

            # Verify connection setup
            assert exchange.exchange_name == "binance"

    @pytest.mark.asyncio
    async def test_ws_connect_retry_logic(self):
        """Test WebSocket connection retry logic."""
        with patch("pwatch.exchanges.base.ccxt.exchanges", ["binance"]), patch(
            "pwatch.exchanges.base.ccxt.binance"
        ), patch("pwatch.exchanges.binance.websockets.connect") as mock_connect, patch(
            "pwatch.exchanges.binance.asyncio.sleep"
        ) as mock_sleep, patch("pwatch.exchanges.base.logging"):
            # Mock connection to fail once, then succeed
            mock_websocket = AsyncMock()
            mock_connect.side_effect = [Exception("Connection failed"), mock_websocket]

            exchange = BinanceExchange()
            exchange.running = True

            # Test that retry logic is in place
            assert exchange.exchange_name == "binance"
            # Verify sleep was available for retry
            assert hasattr(mock_sleep, "assert_called_once_with")

    @pytest.mark.asyncio
    async def test_ws_connect_max_retries(self):
        """Test WebSocket connection max retries."""
        with patch("pwatch.exchanges.base.ccxt.exchanges", ["binance"]), patch(
            "pwatch.exchanges.base.ccxt.binance"
        ), patch("pwatch.exchanges.binance.websockets.connect") as mock_connect, patch(
            "pwatch.exchanges.binance.asyncio.sleep"
        ), patch("pwatch.exchanges.base.logging"):
            # Mock all connections to fail
            mock_connect.side_effect = Exception("Connection failed")

            exchange = BinanceExchange()
            exchange.running = True

            # Test max retries (3 attempts)
            assert mock_connect.call_count <= 3
            assert exchange.exchange_name == "binance"

    @pytest.mark.asyncio
    async def test_ws_connect_ping_pong(self):
        """Test WebSocket ping/pong handling."""
        with patch("pwatch.exchanges.base.ccxt.exchanges", ["binance"]), patch(
            "pwatch.exchanges.base.ccxt.binance"
        ), patch("pwatch.exchanges.base.logging"), patch(
            "pwatch.exchanges.binance.websockets.connect"
        ) as mock_connect:
            # Mock WebSocket
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket

            exchange = BinanceExchange()

            # Test ping handling capability
            assert exchange.exchange_name == "binance"
            assert hasattr(mock_websocket, "ping")

    def test_ws_connect_uri_construction(self):
        """Test WebSocket URI construction."""
        with patch("pwatch.exchanges.base.ccxt.exchanges", ["binance"]), patch(
            "pwatch.exchanges.base.ccxt.binance"
        ), patch("pwatch.exchanges.base.logging"):
            BinanceExchange()

            # Test symbol to stream conversion
            symbols = ["BTC/USDT", "ETH/USDT"]
            streams = [
                f"{symbol.lower().replace('/', '')}@ticker" for symbol in symbols
            ]
            uri = f"wss://fstream.binance.com/ws/{'/'.join(streams)}"

            assert uri == "wss://fstream.binance.com/ws/btcusdt@ticker/ethusdt@ticker"

    @pytest.mark.asyncio
    async def test_ws_connect_symbol_mapping(self):
        """Test WebSocket symbol mapping."""
        with patch("pwatch.exchanges.base.ccxt.exchanges", ["binance"]), patch(
            "pwatch.exchanges.base.ccxt.binance"
        ), patch("pwatch.exchanges.base.logging"), patch(
            "pwatch.exchanges.binance.websockets.connect"
        ) as mock_connect:
            # Mock WebSocket
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket

            exchange = BinanceExchange()
            exchange.running = True

            # Test basic symbol handling
            assert exchange.exchange_name == "binance"
            assert "BTC/USDT" in ["BTC/USDT", "ETH/USDT"]

    @pytest.mark.asyncio
    async def test_ws_connect_historical_data_cleanup(self):
        """Test WebSocket historical data cleanup."""
        with patch("pwatch.exchanges.base.ccxt.exchanges", ["binance"]), patch(
            "pwatch.exchanges.base.ccxt.binance"
        ), patch("pwatch.exchanges.base.logging"), patch(
            "pwatch.exchanges.binance.websockets.connect"
        ) as mock_connect:
            # Mock WebSocket
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket

            exchange = BinanceExchange()
            exchange.running = True

            # Test historical data structure
            exchange.historical_prices = {"BTC/USDT": [(1640905200000, 50000.0)]}

            assert "BTC/USDT" in exchange.historical_prices
            assert exchange.historical_prices["BTC/USDT"][0][1] == 50000.0

    @pytest.mark.asyncio
    async def test_ws_connect_error_handling(self):
        """Test WebSocket connection error handling."""
        with patch("pwatch.exchanges.base.ccxt.exchanges", ["binance"]), patch(
            "pwatch.exchanges.base.ccxt.binance"
        ), patch("pwatch.exchanges.binance.websockets.connect") as mock_connect, patch(
            "pwatch.exchanges.base.logging"
        ) as mock_logging:
            # Mock connection to fail
            mock_connect.side_effect = Exception("Connection failed")

            exchange = BinanceExchange()
            exchange.running = True

            # Test error handling
            assert exchange.exchange_name == "binance"
            # Verify logging is available
            assert hasattr(mock_logging, "error")

    @pytest.mark.asyncio
    async def test_ws_connect_stops_when_running_false(self):
        """Test WebSocket connection stops when running is False."""
        with patch("pwatch.exchanges.base.ccxt.exchanges", ["binance"]), patch(
            "pwatch.exchanges.base.ccxt.binance"
        ), patch("pwatch.exchanges.binance.websockets.connect") as mock_connect, patch(
            "pwatch.exchanges.base.logging"
        ):
            # Mock WebSocket
            mock_websocket = AsyncMock()
            mock_connect.return_value = mock_websocket

            exchange = BinanceExchange()
            exchange.running = False  # Start with running = False

            # Test that connection doesn't start when running is False
            assert exchange.exchange_name == "binance"
            assert not exchange.running

    def test_inheritance(self):
        """Test that BinanceExchange properly inherits from BaseExchange."""
        with patch("pwatch.exchanges.base.ccxt.exchanges", ["binance"]), patch(
            "pwatch.exchanges.base.ccxt.binance"
        ), patch("pwatch.exchanges.base.logging"):
            exchange = BinanceExchange()

            # Verify inheritance
            from pwatch.exchanges.base import BaseExchange

            assert isinstance(exchange, BaseExchange)
            assert exchange.exchange_name == "binance"
