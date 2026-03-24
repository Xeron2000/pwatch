"""Fetch top volume symbols from pwatch.exchanges."""

import logging
import time
from typing import Any, Optional

import ccxt

# Cache for top volume symbols (4 hours TTL)
_volume_cache: dict = {}
_CACHE_TTL_SECONDS = 4 * 60 * 60  # 4 hours


def fetch_top_volume_symbols(
    exchange_name: str,
    limit: int = 20,
    filters: Optional[dict[str, Any]] = None,
 ) -> list[str]:
    """Fetch top N symbols by 24h trading volume after applying quality filters."""
    normalized_filters = _normalize_filters(filters or {})
    cache_key = f"{exchange_name}_{limit}_{tuple(sorted(normalized_filters.items()))}"
    now = time.time()

    if cache_key in _volume_cache:
        cached_data, cached_time = _volume_cache[cache_key]
        if now - cached_time < _CACHE_TTL_SECONDS:
            logging.debug("Using cached top volume symbols for %s", exchange_name)
            return cached_data

    logging.info("Fetching top %s volume symbols from %s", limit, exchange_name)

    try:
        exchange = _create_exchange(exchange_name)
        symbols = _fetch_symbols_by_volume(exchange, limit, normalized_filters)

        if symbols:
            _volume_cache[cache_key] = (symbols, now)
            logging.info("Fetched %s top volume symbols from %s", len(symbols), exchange_name)

        return symbols

    except Exception as e:
        logging.error(f"Failed to fetch top volume symbols from {exchange_name}: {e}")
        if cache_key in _volume_cache:
            logging.warning("Using expired cache as fallback")
            return _volume_cache[cache_key][0]
        return []


def _normalize_filters(filters: dict[str, Any]) -> dict[str, Any]:
    return {
        "minQuoteVolume24h": float(filters.get("minQuoteVolume24h", 0) or 0),
        "minOpenInterestUsd": float(filters.get("minOpenInterestUsd", 0) or 0),
        "minListingAgeDays": int(filters.get("minListingAgeDays", 0) or 0),
        "maxRecentVolatilityPct": float(filters.get("maxRecentVolatilityPct", 0) or 0),
    }


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

    if exchange_name == "binance":
        options["defaultType"] = "swap"
        options["options"] = {"defaultType": "swap"}

    exchange = exchange_classes[exchange_name](options)
    return exchange


def _fetch_symbols_by_volume(exchange: ccxt.Exchange, limit: int, filters: dict[str, Any]) -> list[str]:
    """Fetch, filter, and sort symbols by 24h volume."""
    exchange.load_markets()

    exchange_id = exchange.id.lower()
    usdt_futures = [
        symbol
        for symbol, market in exchange.markets.items()
        if _is_usdt_perpetual(market, exchange_id)
    ]

    if not usdt_futures:
        logging.warning("No USDT perpetual futures found")
        return []

    tickers = _fetch_tickers_for_exchange(exchange, usdt_futures)
    candidate_symbols = []
    volume_by_symbol: dict[str, float] = {}
    for symbol in usdt_futures:
        ticker = tickers.get(symbol)
        if not ticker:
            continue
        volume = _calculate_usdt_volume(ticker)
        if volume <= 0 or volume < filters["minQuoteVolume24h"]:
            continue
        candidate_symbols.append(symbol)
        volume_by_symbol[symbol] = volume

    if not candidate_symbols:
        return []

    if filters["minOpenInterestUsd"] > 0:
        oi_map = _fetch_open_interest_map(exchange, candidate_symbols)
        candidate_symbols = [
            symbol
            for symbol in candidate_symbols
            if _extract_open_interest_usd(oi_map.get(symbol), tickers.get(symbol)) >= filters["minOpenInterestUsd"]
        ]

    if filters["minListingAgeDays"] > 0:
        candidate_symbols = [
            symbol
            for symbol in candidate_symbols
            if _listing_age_days(exchange.markets.get(symbol, {})) >= filters["minListingAgeDays"]
        ]

    if filters["maxRecentVolatilityPct"] > 0:
        candidate_symbols = [
            symbol
            for symbol in candidate_symbols
            if _recent_volatility_pct(exchange, symbol) <= filters["maxRecentVolatilityPct"]
        ]

    candidate_symbols.sort(key=lambda symbol: volume_by_symbol[symbol], reverse=True)
    return candidate_symbols[:limit]


def _calculate_usdt_volume(ticker: dict) -> float:
    """Calculate 24h USDT volume from ticker data."""
    quote_volume = ticker.get("quoteVolume")
    if quote_volume and quote_volume > 0:
        return float(quote_volume)

    last_price = ticker.get("last") or ticker.get("close") or 0
    if not last_price or last_price <= 0:
        return 0

    info = ticker.get("info", {})
    vol_ccy = info.get("volCcy24h")
    if vol_ccy:
        try:
            return float(vol_ccy) * float(last_price)
        except (ValueError, TypeError):
            pass

    base_volume = ticker.get("baseVolume") or 0
    if base_volume > 0:
        return float(base_volume) * float(last_price)

    return 0


def _fetch_tickers_for_exchange(exchange: ccxt.Exchange, symbols: list[str]) -> dict:
    """Fetch tickers using exchange-appropriate method."""
    exchange_id = exchange.id.lower()

    if exchange_id in ("okx", "bybit"):
        try:
            return exchange.fetch_tickers(params={"instType": "SWAP"})
        except Exception as e:
            logging.warning(f"Failed to fetch tickers with instType param: {e}")

    try:
        return exchange.fetch_tickers()
    except Exception as e:
        logging.warning(f"Failed to fetch all tickers: {e}")

    try:
        return exchange.fetch_tickers(symbols)
    except Exception as e:
        logging.warning(f"Failed to fetch tickers by symbols: {e}")
        return _fetch_tickers_individually(exchange, symbols[:100])


def _fetch_open_interest_map(exchange: ccxt.Exchange, symbols: list[str]) -> dict[str, Any]:
    try:
        if hasattr(exchange, "fetch_open_interests"):
            result = exchange.fetch_open_interests(symbols)
            if isinstance(result, dict):
                return result
    except Exception as exc:
        logging.warning("Failed to fetch open interests in batch: %s", exc)

    open_interests: dict[str, Any] = {}
    for symbol in symbols:
        try:
            if hasattr(exchange, "fetch_open_interest"):
                open_interests[symbol] = exchange.fetch_open_interest(symbol)
        except Exception:
            continue
    return open_interests


def _extract_open_interest_usd(open_interest: Any, ticker: Optional[dict]) -> float:
    if not open_interest:
        return 0
    for key in ("openInterestValue", "openInterestUsd", "openInterestAmountUsd", "openInterestQuote"):
        value = open_interest.get(key) if isinstance(open_interest, dict) else None
        if value:
            return float(value)
    amount = open_interest.get("openInterestAmount") if isinstance(open_interest, dict) else None
    last_price = (ticker or {}).get("last") or (ticker or {}).get("close") or 0
    if amount and last_price:
        return float(amount) * float(last_price)
    return 0


def _listing_age_days(market: dict) -> int:
    created = market.get("created")
    if not created:
        return 0
    return int((time.time() * 1000 - created) / (24 * 60 * 60 * 1000))


def _recent_volatility_pct(exchange: ccxt.Exchange, symbol: str) -> float:
    try:
        candles = exchange.fetch_ohlcv(symbol, timeframe="5m", limit=4)
    except Exception as exc:
        logging.warning("Failed to fetch OHLCV for %s: %s", symbol, exc)
        return float("inf")

    closes = [float(candle[4]) for candle in candles if len(candle) >= 5 and candle[4]]
    if len(closes) < 2:
        return float("inf")

    moves = []
    for prev, curr in zip(closes, closes[1:]):
        if prev <= 0:
            return float("inf")
        moves.append(abs((curr - prev) / prev) * 100)

    return max(moves) if moves else float("inf")


def _is_usdt_perpetual(market: dict, exchange_id: str = "") -> bool:
    """Check if market is a USDT perpetual future."""
    if not market.get("active", False):
        return False
    if market.get("quote") != "USDT":
        return False
    if market.get("settle") != "USDT":
        return False

    market_type = market.get("type")
    if exchange_id == "binance":
        return market_type == "swap"

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


def get_cache_age(exchange_name: str, limit: int = 20, filters: Optional[dict[str, Any]] = None) -> Optional[float]:
    """Get age of cached data in seconds, or None if not cached."""
    normalized_filters = _normalize_filters(filters or {})
    cache_key = f"{exchange_name}_{limit}_{tuple(sorted(normalized_filters.items()))}"
    if cache_key in _volume_cache:
        _, cached_time = _volume_cache[cache_key]
        return time.time() - cached_time
    return None


def clear_cache():
    """Clear the volume symbols cache."""
    global _volume_cache
    _volume_cache = {}
    logging.info("Top volume symbols cache cleared")
