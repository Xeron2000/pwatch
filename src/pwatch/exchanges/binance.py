import asyncio
import json
import logging
import time

import websockets

from .base import BaseExchange


class BinanceExchange(BaseExchange):
    def __init__(self):
        super().__init__("binance")
        self.exchange.options["defaultType"] = "future"

    async def _ws_connect(self, symbols):
        """Establish WebSocket connection and subscribe to market data"""
        logging.info(
            f"Attempting to establish WebSocket connection for {self.exchange_name}, subscribing symbols: {symbols}"
        )

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries and self.running:
            try:
                # Binance uses a different URI structure
                # wss://stream.binance.com:9443/ws/btcusdt@ticker/ethusdt@ticker
                streams = []
                for symbol in symbols:
                    base_symbol = symbol.split(":")[0]
                    formatted = base_symbol.replace("/", "").lower()
                    streams.append(f"{formatted}@ticker")
                uri = f"wss://fstream.binance.com/ws/{'/'.join(streams)}"
                logging.debug(f"Binance WebSocket URI: {uri}")

                async with websockets.connect(uri) as websocket:
                    self.ws = websocket
                    self.ws_connected = True
                    logging.info("Binance WebSocket connection established")

                    # Binance does not require a subscription message for ticker streams

                    # Continuously receive data
                    while self.running:
                        try:
                            response = await websocket.recv()
                            data = json.loads(response)

                            # Handle ping messages (Binance sends pings)
                            if "e" in data and data["e"] == "ping":
                                pong_frame = await websocket.ping()
                                await websocket.send(pong_frame)
                                logging.debug("Ping received, pong sent")
                                continue

                            # Process ticker data
                            if "s" in data and "c" in data:
                                symbol = data["s"]
                                price = float(data["c"])
                                # Binance symbols are uppercase, but stream is lowercase
                                # We need to find the original symbol format
                                original_symbol = next(
                                    (s for s in symbols if s.split(":")[0].replace("/", "").upper() == symbol.upper()),
                                    symbol,
                                )
                                canonical_symbol = original_symbol
                                if ":" not in canonical_symbol:
                                    canonical_symbol = f"{original_symbol}:USDT"
                                self.last_prices[canonical_symbol] = price

                                # Log received price data every 10 minutes
                                if time.time() % 600 < 1:  # Approximately every 10 minutes
                                    logging.info(
                                        "Binance price update - %s: %s",
                                        canonical_symbol,
                                        price,
                                    )

                                # Store historical data using base class method
                                self._store_historical_price(canonical_symbol, price)
                        except Exception as e:
                            logging.error(f"Binance WebSocket data processing error: {e}")
                            break

                    self.ws_connected = False
                    logging.warning("Binance WebSocket connection closed")

                # If connection successful, break retry loop
                break

            except Exception as e:
                logging.error(f"Error establishing WebSocket connection (attempt {retry_count + 1}/{max_retries}): {e}")
                retry_count += 1
                await asyncio.sleep(5)  # Wait 5 seconds before retrying

        if not self.ws_connected:
            logging.error(f"Unable to establish WebSocket connection after {max_retries} attempts")
