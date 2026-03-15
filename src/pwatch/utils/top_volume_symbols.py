"""Fetch top volume symbols from pwatch.exchanges."""

import logging
import time
from typing import Optional

import ccxt

# Cache for top volume symbols (4 hours TTL)
_volume_cache: dict = {}
_CACHE_TTL_SECONDS = 4 * 60 * 60  # 4 hours


def fetch_top_volume_symbols(exchange_name: str, limit: int = 20) -> list[str]:
    """
    Fetch top N symbols by 24h trading volume from exchange.

    Args:
        exchange_name: Exchange name (okx, bybit, binance)
        limit: Number of symbols to return

    Returns:
        List of symbols in format SYMBOL/USDT:USDT
    """
    cache_key = f"{exchange_name}_{limit}"
    now = time.time()

    # Check cache
    if cache_key in _volume_cache:
        cached_data, cached_time = _volume_cache[cache_key]
        if now - cached_time < _CACHE_TTL_SECONDS:
            logging.debug(f"Using cached top volume symbols for {exchange_name}")
            return cached_data

    logging.info(f"Fetching top {limit} volume symbols from {exchange_name}")

    try:
        exchange = _create_exchange(exchange_name)
        symbols = _fetch_symbols_by_volume(exchange, limit)

        if symbols:
            _volume_cache[cache_key] = (symbols, now)
            logging.info(f"Fetched {len(symbols)} top volume symbols from {exchange_name}")

        return symbols

    except Exception as e:
        logging.error(f"Failed to fetch top volume symbols from {exchange_name}: {e}")
        # Return cached data if available (even if expired)
        if cache_key in _volume_cache:
            logging.warning("Using expired cache as fallback")
            return _volume_cache[cache_key][0]
        return []


def _create_exchange(exchange_name: str) -> ccxt.Exchange:
    """Create ccxt exchange instance."""
    exchange_name = exchange_name.lower().strip()

    exchange_classes = {
        "okx": ccxt.okx,
        "binance": ccxt.binance,
        "bybit": ccxt.bybit,
    }

    if exchange_name not in exchange_classes:
        raise ValueError(f"Unsupported exchange: {exchange_name}")

    options = {"enableRateLimit": True}

    # Binance: use USDT-margined futures API
    if exchange_name == "binance":
        options["defaultType"] = "swap"
        options["options"] = {"defaultType": "swap"}

    exchange = exchange_classes[exchange_name](options)
    return exchange


def _fetch_symbols_by_volume(exchange: ccxt.Exchange, limit: int) -> list[str]:
    """Fetch and sort symbols by 24h volume."""
    exchange.load_markets()

    exchange_id = exchange.id.lower()

    # Get all USDT perpetual futures
    usdt_futures = []
    for symbol, market in exchange.markets.items():
        if not _is_usdt_perpetual(market, exchange_id):
            continue
        usdt_futures.append(symbol)

    if not usdt_futures:
        logging.warning("No USDT perpetual futures found")
        return []

    usdt_futures_set = set(usdt_futures)

    # Fetch tickers for volume data
    tickers = _fetch_tickers_for_exchange(exchange, usdt_futures)

    # Sort by USDT volume
    volume_data = []
    for symbol, ticker in tickers.items():
        # Only include USDT perpetuals
        if symbol not in usdt_futures_set:
            continue

        volume = _calculate_usdt_volume(ticker)
        if volume > 0:
            volume_data.append((symbol, volume))

    volume_data.sort(key=lambda x: x[1], reverse=True)

    # Return top N symbols
    top_symbols = [symbol for symbol, _ in volume_data[:limit]]
    return top_symbols


def _calculate_usdt_volume(ticker: dict) -> float:
    """Calculate 24h USDT volume from ticker data."""
    # Try quoteVolume first (already in USDT)
    quote_volume = ticker.get("quoteVolume")
    if quote_volume and quote_volume > 0:
        return float(quote_volume)

    last_price = ticker.get("last") or ticker.get("close") or 0
    if not last_price or last_price <= 0:
        return 0

    # For OKX: use volCcy24h (base currency volume) from info
    info = ticker.get("info", {})
    vol_ccy = info.get("volCcy24h")
    if vol_ccy:
        try:
            return float(vol_ccy) * float(last_price)
        except (ValueError, TypeError):
            pass

    # Fallback: baseVolume * price
    base_volume = ticker.get("baseVolume") or 0
    if base_volume > 0:
        return float(base_volume) * float(last_price)

    return 0


def _fetch_tickers_for_exchange(exchange: ccxt.Exchange, symbols: list[str]) -> dict:
    """Fetch tickers using exchange-appropriate method."""
    exchange_id = exchange.id.lower()

    # OKX/Bybit support instType param for efficient batch fetch
    if exchange_id in ("okx", "bybit"):
        try:
            return exchange.fetch_tickers(params={"instType": "SWAP"})
        except Exception as e:
            logging.warning(f"Failed to fetch tickers with instType param: {e}")

    # Binance/others: fetch all tickers (defaultType already set in exchange config)
    try:
        return exchange.fetch_tickers()
    except Exception as e:
        logging.warning(f"Failed to fetch all tickers: {e}")

    # Fallback: fetch individually
    try:
        return exchange.fetch_tickers(symbols)
    except Exception as e:
        logging.warning(f"Failed to fetch tickers by symbols: {e}")
        return _fetch_tickers_individually(exchange, symbols[:100])


def _is_usdt_perpetual(market: dict, exchange_id: str = "") -> bool:
    """Check if market is a USDT perpetual future."""
    if not market.get("active", False):
        return False
    if market.get("quote") != "USDT":
        return False
    if market.get("settle") != "USDT":
        return False

    market_type = market.get("type")
    # Binance: only swap (perpetual), exclude future (delivery)
    if exchange_id == "binance":
        return market_type == "swap"

    # OKX/Bybit: accept both swap and future
    return market_type in ("swap", "future")


def _fetch_tickers_individually(exchange: ccxt.Exchange, symbols: list[str]) -> dict:
    """Fetch tickers one by one as fallback."""
    tickers = {}
    for symbol in symbols:
        try:
            ticker = exchange.fetch_ticker(symbol)
            tickers[symbol] = ticker
        except Exception:
            continue
    return tickers


def get_cache_age(exchange_name: str, limit: int = 20) -> Optional[float]:
    """Get age of cached data in seconds, or None if not cached."""
    cache_key = f"{exchange_name}_{limit}"
    if cache_key in _volume_cache:
        _, cached_time = _volume_cache[cache_key]
        return time.time() - cached_time
    return None


def clear_cache():
    """Clear the volume symbols cache."""
    global _volume_cache
    _volume_cache = {}
    logging.info("Top volume symbols cache cleared")
