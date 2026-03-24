from __future__ import annotations

import time

from pwatch.utils.top_volume_symbols import fetch_top_volume_symbols


class FakeExchange:
    def __init__(self):
        now_ms = int(time.time() * 1000)
        old_ms = now_ms - 90 * 24 * 60 * 60 * 1000
        new_ms = now_ms - 2 * 24 * 60 * 60 * 1000
        self.id = "okx"
        self.markets = {
            "PEPE/USDT:USDT": {"active": True, "quote": "USDT", "settle": "USDT", "type": "swap", "created": old_ms},
            "BTC/USDT:USDT": {"active": True, "quote": "USDT", "settle": "USDT", "type": "swap", "created": old_ms},
            "ETH/USDT:USDT": {"active": True, "quote": "USDT", "settle": "USDT", "type": "swap", "created": old_ms},
            "NEW/USDT:USDT": {"active": True, "quote": "USDT", "settle": "USDT", "type": "swap", "created": new_ms},
            "WILD/USDT:USDT": {"active": True, "quote": "USDT", "settle": "USDT", "type": "swap", "created": old_ms},
            "NODATA/USDT:USDT": {"active": True, "quote": "USDT", "settle": "USDT", "type": "swap", "created": old_ms},
        }
        self._tickers = {
            "PEPE/USDT:USDT": {"quoteVolume": 150_000_000, "last": 1.0, "symbol": "PEPE/USDT:USDT"},
            "BTC/USDT:USDT": {"quoteVolume": 120_000_000, "last": 100.0, "symbol": "BTC/USDT:USDT"},
            "ETH/USDT:USDT": {"quoteVolume": 100_000_000, "last": 100.0, "symbol": "ETH/USDT:USDT"},
            "NEW/USDT:USDT": {"quoteVolume": 95_000_000, "last": 100.0, "symbol": "NEW/USDT:USDT"},
            "WILD/USDT:USDT": {"quoteVolume": 90_000_000, "last": 100.0, "symbol": "WILD/USDT:USDT"},
            "NODATA/USDT:USDT": {"quoteVolume": 85_000_000, "last": 100.0, "symbol": "NODATA/USDT:USDT"},
        }
        self._open_interests = {
            "PEPE/USDT:USDT": {"openInterestValue": 2_000_000},
            "BTC/USDT:USDT": {"openInterestValue": 50_000_000},
            "ETH/USDT:USDT": {"openInterestValue": 30_000_000},
            "NEW/USDT:USDT": {"openInterestValue": 40_000_000},
            "WILD/USDT:USDT": {"openInterestValue": 25_000_000},
        }
        self._ohlcv = {
            "PEPE/USDT:USDT": [[0, 0, 0, 0, 1.00, 0], [0, 0, 0, 0, 1.01, 0], [0, 0, 0, 0, 1.02, 0], [0, 0, 0, 0, 1.01, 0]],
            "BTC/USDT:USDT": [[0, 0, 0, 0, 100.0, 0], [0, 0, 0, 0, 101.0, 0], [0, 0, 0, 0, 100.5, 0], [0, 0, 0, 0, 101.2, 0]],
            "ETH/USDT:USDT": [[0, 0, 0, 0, 100.0, 0], [0, 0, 0, 0, 99.8, 0], [0, 0, 0, 0, 100.4, 0], [0, 0, 0, 0, 100.2, 0]],
            "NEW/USDT:USDT": [[0, 0, 0, 0, 100.0, 0], [0, 0, 0, 0, 100.5, 0], [0, 0, 0, 0, 100.2, 0], [0, 0, 0, 0, 100.8, 0]],
            "WILD/USDT:USDT": [[0, 0, 0, 0, 100.0, 0], [0, 0, 0, 0, 120.0, 0], [0, 0, 0, 0, 80.0, 0], [0, 0, 0, 0, 118.0, 0]],
        }

    def load_markets(self):
        return self.markets

    def fetch_tickers(self, *args, **kwargs):
        return self._tickers

    def fetch_open_interests(self, symbols=None, params=None):
        if symbols is None:
            return self._open_interests
        return {symbol: self._open_interests.get(symbol) for symbol in symbols if symbol in self._open_interests}

    def fetch_ohlcv(self, symbol, timeframe="5m", limit=4, params=None):
        return self._ohlcv.get(symbol, [])


def test_fetch_top_volume_symbols_applies_quality_filters(monkeypatch):
    fake_exchange = FakeExchange()
    monkeypatch.setattr("pwatch.utils.top_volume_symbols._create_exchange", lambda exchange_name: fake_exchange)
    monkeypatch.setattr("pwatch.utils.top_volume_symbols.clear_cache", lambda: None)

    result = fetch_top_volume_symbols(
        "okx",
        limit=2,
        filters={
            "minQuoteVolume24h": 80_000_000,
            "minOpenInterestUsd": 10_000_000,
            "minListingAgeDays": 30,
            "maxRecentVolatilityPct": 10.0,
        },
    )

    assert result == ["BTC/USDT:USDT", "ETH/USDT:USDT"]


def test_fetch_top_volume_symbols_excludes_missing_quality_data(monkeypatch):
    fake_exchange = FakeExchange()
    monkeypatch.setattr("pwatch.utils.top_volume_symbols._create_exchange", lambda exchange_name: fake_exchange)
    monkeypatch.setattr("pwatch.utils.top_volume_symbols.clear_cache", lambda: None)

    result = fetch_top_volume_symbols(
        "okx",
        limit=10,
        filters={
            "minQuoteVolume24h": 80_000_000,
            "minOpenInterestUsd": 10_000_000,
            "minListingAgeDays": 30,
            "maxRecentVolatilityPct": 10.0,
        },
    )

    assert "NODATA/USDT:USDT" not in result
    assert "NEW/USDT:USDT" not in result
    assert "WILD/USDT:USDT" not in result
    assert "PEPE/USDT:USDT" not in result
