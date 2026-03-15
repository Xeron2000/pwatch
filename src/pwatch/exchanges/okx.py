import asyncio
import json
import logging
import time

import websockets

from .base import BaseExchange


class OkxExchange(BaseExchange):
    def __init__(self):
        super().__init__("okx")
        self.exchange.options.update(
            {
                "defaultType": "swap",
                "defaultInstType": "SWAP",
                "defaultMarket": "swap",
                "instType": "SWAP",
            }
        )
        try:
            self.exchange.load_markets(reload=True, params={"instType": "SWAP"})
        except Exception as exc:
            logging.debug(f"Failed to preload OKX swap markets: {exc}")

    def _get_ohlcv_params(self, symbol):
        """Ensure only swap markets are requested for historical data."""
        params = {"instType": "SWAP"}
        try:
            base, remainder = symbol.split("/")
            quote = remainder.split(":")[0]
            params["instId"] = f"{base}-{quote}-SWAP"
        except ValueError:
            pass
        return params

    @staticmethod
    def _canonical_symbol(inst_id: str) -> str:
        parts = inst_id.split("-")
        if len(parts) >= 2:
            base, quote = parts[0], parts[1]
            return f"{base}/{quote}:USDT"
        return inst_id

    async def _ws_connect(self, symbols):
        """Establish WebSocket connection and subscribe to market data"""
        logging.info(
            f"Attempting to establish WebSocket connection for {self.exchange_name}, subscribing symbols: {symbols}"
        )

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries and self.running:
            try:
                uri = "wss://ws.okx.com:8443/ws/v5/public"
                logging.debug(f"OKX WebSocket URI: {uri}")

                # Prepare subscription message - modify format to meet OKX
                # requirements
                subscribe_msg = {"op": "subscribe", "args": []}

                # OKX requires specific format for trading pairs
                for symbol in symbols:
                    # Convert format, e.g., BTC/USDT:USDT to BTC-USDT-SWAP
                    # Futures trading pair
                    base_symbol = symbol.split("/")[0]
                    formatted_symbol = f"{base_symbol}-USDT-SWAP"

                    subscribe_msg["args"].append({"channel": "tickers", "instId": formatted_symbol})

                logging.debug(f"Subscription message: {subscribe_msg}")

                async with websockets.connect(uri) as websocket:
                    self.ws = websocket
                    self.ws_connected = True
                    logging.info("OKX WebSocket connection established")

                    # Send subscription request
                    await websocket.send(json.dumps(subscribe_msg))
                    logging.info("Subscription request sent to OKX")

                    # Wait for subscription confirmation
                    response = await websocket.recv()
                    logging.debug(f"Subscription response: {response}")

                    # Continuously receive data
                    while self.running:
                        try:
                            response = await websocket.recv()
                            data = json.loads(response)

                            # Handle heartbeat messages
                            if "event" in data and data["event"] == "ping":
                                pong_msg = {"event": "pong"}
                                await websocket.send(json.dumps(pong_msg))
                                logging.debug("Heartbeat response sent")
                                continue

                            # Process ticker data
                            if "data" in data:
                                for item in data["data"]:
                                    inst_id = item["instId"]
                                    symbol = self._canonical_symbol(inst_id)
                                    price = float(item["last"])
                                    self.last_prices[symbol] = price

                                    # Log received price data every 10 minutes
                                    if time.time() % 600 < 1:  # Approximately every 10 minutes
                                        logging.info(f"OKX price update - {symbol}: {price}")

                                    # Store historical data using base class method
                                    self._store_historical_price(symbol, price)
                        except Exception as e:
                            logging.error(f"OKX WebSocket data processing error: {e}")
                            break

                    self.ws_connected = False
                    logging.warning("OKX WebSocket connection closed")

                # If connection successful, break retry loop
                break

            except Exception as e:
                logging.error(f"Error establishing WebSocket connection (attempt {retry_count + 1}/{max_retries}): {e}")
                retry_count += 1
                await asyncio.sleep(5)  # Wait 5 seconds before retrying

        if not self.ws_connected:
            logging.error(f"Unable to establish WebSocket connection after {max_retries} attempts")
