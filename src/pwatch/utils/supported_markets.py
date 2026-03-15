"""
Utilities for loading, filtering, and refreshing supported market symbols.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import ccxt

from pwatch.paths import get_markets_path

DERIVATIVE_TYPES = {"swap", "future", "futures", "perpetual", "option"}

SUPPORTED_MARKETS_PATH = get_markets_path()

_QUOTE_PATTERN = re.compile(r"[:/]")


# Default market data as fallback for first run
DEFAULT_MARKETS: Dict[str, List[str]] = {
    "okx": [
        "BTC/USDT:USDT",
        "ETH/USDT:USDT",
        "BNB/USDT:USDT",
        "SOL/USDT:USDT",
        "DOGE/USDT:USDT",
        "XRP/USDT:USDT",
        "ADA/USDT:USDT",
        "AVAX/USDT:USDT",
        "DOT/USDT:USDT",
        "LINK/USDT:USDT",
    ],
    "bybit": [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "DOGE/USDT",
        "XRP/USDT",
        "ADA/USDT",
        "AVAX/USDT",
        "DOT/USDT",
        "LINK/USDT",
        "MATIC/USDT",
    ],
    "binance": [
        "BTC/USDT",
        "ETH/USDT",
        "SOL/USDT",
        "DOGE/USDT",
        "XRP/USDT",
        "ADA/USDT",
        "AVAX/USDT",
        "DOT/USDT",
        "LINK/USDT",
        "MATIC/USDT",
    ],
}


def _ensure_parent_dir(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        logging.error("Failed to ensure directory for %s: %s", path, exc)


def _read_supported_markets() -> Dict[str, List[str]]:
    if not SUPPORTED_MARKETS_PATH.exists():
        logging.warning(
            "Supported markets file not found at %s. Will attempt to refresh automatically.",
            SUPPORTED_MARKETS_PATH,
        )
        return {}

    try:
        with SUPPORTED_MARKETS_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        logging.error("Failed to parse supported markets file: %s", exc)
        return {}
    except Exception as exc:
        logging.error("Unable to read supported markets: %s", exc)
        return {}

    if not isinstance(data, dict):
        logging.warning("Supported markets file must contain a mapping. Got %s", type(data))
        return {}

    normalized: Dict[str, List[str]] = {}
    for exchange, symbols in data.items():
        if isinstance(symbols, list):
            normalized[str(exchange)] = [str(symbol) for symbol in symbols if isinstance(symbol, str)]
        else:
            logging.debug(
                "Skipping supported market entry for %s because it is not a list: %s",
                exchange,
                type(symbols),
            )
    return normalized


def _write_supported_markets(data: Dict[str, Sequence[str]]) -> None:
    _ensure_parent_dir(SUPPORTED_MARKETS_PATH)
    try:
        serializable = {exchange: list(symbols) for exchange, symbols in data.items()}
        with SUPPORTED_MARKETS_PATH.open("w", encoding="utf-8") as fh:
            json.dump(serializable, fh, indent=4, ensure_ascii=False)
        logging.info(
            "Persisted supported markets to %s (%s exchanges).",
            SUPPORTED_MARKETS_PATH,
            len(serializable),
        )
    except Exception as exc:
        logging.error("Failed to write supported markets file: %s", exc)


def list_cached_exchanges() -> List[str]:
    """Return the exchanges present in the cached supported markets file."""
    markets = _read_supported_markets()
    # Preserve insertion order while deduplicating
    seen = set()
    ordered: List[str] = []
    for exchange in markets.keys():
        if exchange not in seen:
            seen.add(exchange)
            ordered.append(exchange)
    return ordered


def _is_usdt_contract(symbol: str) -> bool:
    parts = _QUOTE_PATTERN.split(symbol.upper())
    if not parts:
        return False
    return parts[-1] == "USDT"


def filter_usdt_symbols(symbols: Iterable[str]) -> List[str]:
    """Return USDT-quoted symbols from an iterable."""
    seen = set()
    filtered: List[str] = []
    for symbol in symbols:
        if not isinstance(symbol, str):
            continue
        trimmed = symbol.strip()
        if not trimmed:
            continue
        if not _is_usdt_contract(trimmed):
            continue
        if trimmed not in seen:
            seen.add(trimmed)
            filtered.append(trimmed)
    return filtered


def _is_derivatives_market(market: dict) -> bool:
    """Return True when the ccxt market payload represents a derivatives contract."""
    if not isinstance(market, dict):
        return False

    if market.get("contract"):
        return True

    market_type = str(market.get("type") or "").lower()
    if market_type in DERIVATIVE_TYPES:
        return True

    return False


def _fetch_exchange_symbols(exchange_name: str) -> List[str]:
    try:
        exchange_class = getattr(ccxt, exchange_name, None)
        if exchange_class is None:
            logging.error("Exchange %s is not supported by ccxt.", exchange_name)
            return []
        exchange = exchange_class({"options": {"defaultType": "swap"}})
        markets = exchange.fetch_markets()
        derivative_symbols = [
            market["symbol"] for market in markets if "symbol" in market and _is_derivatives_market(market)
        ]
        filtered = filter_usdt_symbols(derivative_symbols)
        logging.info(
            "Fetched %s markets for %s (retained %s derivative USDT contracts)",
            len(markets),
            exchange_name,
            len(filtered),
        )
        return sorted(filtered)
    except (ccxt.ExchangeError, ccxt.NetworkError) as exc:
        logging.error("Failed to fetch markets for %s: %s", exchange_name, exc)
        return []
    except Exception as exc:
        logging.error("Unexpected error fetching markets for %s: %s", exchange_name, exc)
        return []


def refresh_supported_markets(exchange_names: Iterable[str]) -> Dict[str, List[str]]:
    """Fetch and persist supported markets for the given exchanges."""
    existing = _read_supported_markets()
    updated: Dict[str, List[str]] = dict(existing)
    refreshed: Dict[str, List[str]] = {}

    for exchange in exchange_names:
        exchange = (exchange or "").strip()
        if not exchange:
            continue
        symbols = _fetch_exchange_symbols(exchange)
        if symbols:
            updated[exchange] = symbols
            refreshed[exchange] = symbols
        else:
            logging.warning("No USDT symbols available for %s after refresh attempt.", exchange)

    if refreshed:
        _write_supported_markets(updated)
    else:
        logging.warning("No exchanges produced market data; supported markets file left unchanged.")

    return refreshed


def refresh_exchange_markets(exchange: str) -> List[str]:
    """Fetch and persist supported markets for a single exchange."""
    refreshed = refresh_supported_markets([exchange])
    return refreshed.get(exchange, [])


def load_usdt_contracts(exchange: str) -> List[str]:
    """
    Load supported USDT-quoted contracts for the specified exchange.
    Requires markets to be pre-populated via tools/update_markets.py.
    """
    if not exchange:
        return []

    markets = _read_supported_markets()

    # Use default markets as fallback if no cached data
    if not markets or exchange not in markets:
        if exchange in DEFAULT_MARKETS:
            logging.warning(
                "No cached USDT contracts for %s. Using default markets.",
                exchange,
            )
            return DEFAULT_MARKETS[exchange]
        else:
            logging.warning(
                "No cached USDT contracts for %s and no default available. "
                "Try a different exchange or run tools/update_markets.py manually.",
                exchange,
            )
            return []

    symbols = markets.get(exchange, [])
    filtered = filter_usdt_symbols(symbols)
    if filtered:
        return sorted(filtered)

    logging.warning(
        "No cached USDT contracts for %s. Run tools/update_markets.py to refresh the dataset.",
        exchange,
    )
    return []
