import asyncio
import json
import logging
import time

import websockets

from .base import BaseExchange


class BybitExchange(BaseExchange):
    def __init__(self):
        super().__init__("bybit")
        self.exchange.options["defaultType"] = "swap"

    async def _ws_connect(self, symbols):
        """Establish WebSocket connection and subscribe to market data"""
        logging.info(
            f"Attempting to establish WebSocket connection for {self.exchange_name}, subscribing symbols: {symbols}"
        )

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries and self.running:
            try:
                # Bybit uses different endpoints for spot and derivatives
                # This implementation will focus on the unified public endpoint
                uri = "wss://stream.bybit.com/v5/public/linear"
                logging.debug(f"Bybit WebSocket URI: {uri}")

                subscribe_msg = {"op": "subscribe", "args": []}

                for symbol in symbols:
                    base_symbol = symbol.split(":")[0]
                    formatted_symbol = base_symbol.replace("/", "")
                    subscribe_msg["args"].append(f"tickers.{formatted_symbol}")

                logging.debug(f"Subscription message: {subscribe_msg}")

                async with websockets.connect(uri) as websocket:
                    self.ws = websocket
                    self.ws_connected = True
                    logging.info("Bybit WebSocket connection established")

                    # Send subscription request
                    await websocket.send(json.dumps(subscribe_msg))
                    logging.info("Subscription request sent to Bybit")

                    # Continuously receive data
                    while self.running:
                        try:
                            response = await websocket.recv()
                            data = json.loads(response)

                            # Handle ping/pong
                            if "op" in data and data.get("op") == "ping":
                                pong_msg = {"op": "pong", "req_id": data.get("req_id")}
                                await websocket.send(json.dumps(pong_msg))
                                logging.debug("Heartbeat response sent")
                                continue

                            if "topic" in data and "tickers" in data["topic"]:
                                symbol = data["data"]["symbol"]
                                price = float(data["data"]["lastPrice"])
                                original_symbol = next(
                                    (s for s in symbols if s.split(":")[0].replace("/", "").upper() == symbol.upper()),
                                    symbol,
                                )
                                canonical_symbol = (
                                    original_symbol if ":" in original_symbol else f"{original_symbol}:USDT"
                                )
                                self.last_prices[canonical_symbol] = price

                                # Log received price data every 10 minutes
                                if time.time() % 600 < 1:
                                    logging.info(
                                        "Bybit price update - %s: %s",
                                        canonical_symbol,
                                        price,
                                    )

                                # Store historical data using base class method
                                self._store_historical_price(canonical_symbol, price)

                        except Exception as e:
                            logging.error(f"Bybit WebSocket data processing error: {e}")
                            break

                    self.ws_connected = False
                    logging.warning("Bybit WebSocket connection closed")

                # If connection successful, break retry loop
                break

            except Exception as e:
                logging.error(f"Error establishing WebSocket connection (attempt {retry_count + 1}/{max_retries}): {e}")
                retry_count += 1
                await asyncio.sleep(5)  # Wait 5 seconds before retrying

        if not self.ws_connected:
            logging.error(f"Unable to establish WebSocket connection after {max_retries} attempts")
