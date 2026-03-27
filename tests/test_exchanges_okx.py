from unittest.mock import AsyncMock, patch

import pytest
from websockets.exceptions import ConnectionClosedError
from websockets.frames import Close

from pwatch.exchanges.okx import OkxExchange


def test_extract_price_prefers_last_field():
    item = {"last": "123.45", "instId": "BTC-USDT-SWAP"}

    assert OkxExchange._extract_price(item) == 123.45


def test_extract_price_falls_back_to_last_price_field():
    item = {"lastPrice": "234.56", "instId": "BTC-USDT-SWAP"}

    assert OkxExchange._extract_price(item) == 234.56


@pytest.mark.asyncio
async def test_ws_connect_uses_explicit_keepalive_settings():
    with patch("pwatch.exchanges.base.ccxt.exchanges", ["okx"]), patch(
        "pwatch.exchanges.base.ccxt.okx"
    ), patch("pwatch.exchanges.okx.logging"), patch(
        "pwatch.exchanges.okx.websockets.connect"
    ) as mock_connect:
        mock_websocket = AsyncMock()
        mock_websocket.recv.side_effect = [
            '{"event":"subscribe","connId":"abc"}',
            ConnectionClosedError(None, None),
        ]
        mock_connect.return_value.__aenter__.return_value = mock_websocket

        exchange = OkxExchange()
        exchange.running = True

        await exchange._ws_connect(["BTC/USDT:USDT"])

        _, kwargs = mock_connect.call_args
        assert kwargs["ping_interval"] == 20
        assert kwargs["ping_timeout"] == 20
        assert kwargs["close_timeout"] == 10


@pytest.mark.asyncio
async def test_ws_connect_does_not_log_establish_failure_after_later_disconnect():
    with patch("pwatch.exchanges.base.ccxt.exchanges", ["okx"]), patch(
        "pwatch.exchanges.base.ccxt.okx"
    ), patch("pwatch.exchanges.okx.logging") as mock_logging, patch(
        "pwatch.exchanges.okx.websockets.connect"
    ) as mock_connect:
        mock_websocket = AsyncMock()
        mock_websocket.recv.side_effect = [
            '{"event":"subscribe","connId":"abc"}',
            ConnectionClosedError(Close(1006, "abnormal closure"), None),
        ]
        mock_connect.return_value.__aenter__.return_value = mock_websocket

        exchange = OkxExchange()
        exchange.running = True

        await exchange._ws_connect(["BTC/USDT:USDT"])

        error_messages = [call.args[0] for call in mock_logging.error.call_args_list]
        assert not any("Unable to establish WebSocket connection after 3 attempts" in msg for msg in error_messages)
