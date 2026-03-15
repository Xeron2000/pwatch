"""
Test cases for cache management system.
"""

import time
from collections import OrderedDict

from pwatch.utils.cache_manager import CacheManager, CacheStrategy, PriceCacheManager


class TestCacheManager:
    """Test cache management functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.cache = CacheManager(max_size=100, default_ttl=300)

    def test_init(self):
        """Test CacheManager initialization."""
        assert self.cache.max_size == 100
        assert self.cache.default_ttl == 300
        assert self.cache.strategy == CacheStrategy.LRU
        assert len(self.cache.cache) == 0

    def test_set_and_get_string_key(self):
        """Test setting and getting values with string keys."""
        self.cache.set("test_key", "test_value")
        result = self.cache.get("test_key")

        assert result == "test_value"
        assert len(self.cache.cache) == 1

    def test_set_and_get_tuple_key(self):
        """Test setting and getting values with tuple keys."""
        key = ("BTC", "USDT", "1m")
        self.cache.set(key, 50000.0)
        result = self.cache.get(key)

        assert result == 50000.0
        assert len(self.cache.cache) == 1

    def test_set_and_get_dict_key(self):
        """Test setting and getting values with dict keys."""
        key = {"symbol": "BTC/USDT", "timeframe": "1m"}
        self.cache.set(key, {"price": 50000.0, "volume": 1000.0})
        result = self.cache.get(key)

        assert result == {"price": 50000.0, "volume": 1000.0}
        assert len(self.cache.cache) == 1

    def test_get_nonexistent_key(self):
        """Test getting value for nonexistent key."""
        result = self.cache.get("nonexistent_key")
        assert result is None

        # Test with default value
        result = self.cache.get("nonexistent_key", "default_value")
        assert result == "default_value"

    def test_set_with_ttl(self):
        """Test setting value with TTL."""
        self.cache.set("temp_key", "temp_value", ttl=0.1)

        # Value should exist immediately
        result = self.cache.get("temp_key")
        assert result == "temp_value"

        # Wait for TTL to expire
        time.sleep(0.2)

        # Value should be gone
        result = self.cache.get("temp_key")
        assert result is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = CacheManager(max_size=3, default_ttl=300)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it most recently used
        cache.get("key1")

        # Add new item, should evict key2 (least recently used)
        cache.set("key4", "value4")

        # Check eviction
        assert cache.get("key1") == "value1"  # Should exist
        assert cache.get("key2") is None  # Should be evicted
        assert cache.get("key3") == "value3"  # Should exist
        assert cache.get("key4") == "value4"  # Should exist

    def test_delete(self):
        """Test deleting items from cache."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        # Delete key1
        result = self.cache.delete("key1")
        assert result is True

        # Verify deletion
        assert self.cache.get("key1") is None
        assert self.cache.get("key2") == "value2"

        # Delete nonexistent key
        result = self.cache.delete("nonexistent_key")
        assert result is False

    def test_clear(self):
        """Test clearing cache."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        # Clear cache
        self.cache.clear()

        # Verify cache is empty
        assert len(self.cache.cache) == 0
        assert self.cache.get("key1") is None
        assert self.cache.get("key2") is None

    def test_contains(self):
        """Test checking if key exists in cache."""
        self.cache.set("key1", "value1")

        # Check existing key
        assert "key1" in self.cache

        # Check nonexistent key
        assert "key2" not in self.cache

    def test_size(self):
        """Test getting cache size."""
        assert self.cache.size() == 0

        self.cache.set("key1", "value1")
        assert self.cache.size() == 1

        self.cache.set("key2", "value2")
        assert self.cache.size() == 2

    def test_keys(self):
        """Test getting all keys in cache."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        keys = self.cache.keys()
        assert set(keys) == {"key1", "key2"}

    def test_values(self):
        """Test getting all values in cache."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        values = self.cache.values()
        assert set(values) == {"value1", "value2"}

    def test_items(self):
        """Test getting all items in cache."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        items = self.cache.items()
        assert dict(items) == {"key1": "value1", "key2": "value2"}

    def test_get_stats(self):
        """Test getting cache statistics."""
        # Initially empty
        stats = self.cache.get_stats()
        assert stats["size"] == 0
        assert stats["max_size"] == 100
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 0
        assert stats["eviction_count"] == 0

        # Add some items
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        # Get some hits and misses
        self.cache.get("key1")  # hit
        self.cache.get("key2")  # hit
        self.cache.get("key3")  # miss

        stats = self.cache.get_stats()
        assert stats["size"] == 2
        assert stats["hit_count"] == 2
        assert stats["miss_count"] == 1

    def test_cleanup_expired(self):
        """Test cleaning up expired items."""
        self.cache.set("key1", "value1", ttl=0.1)
        self.cache.set("key2", "value2", ttl=0.2)
        self.cache.set("key3", "value3")  # No TTL

        # Wait for first item to expire
        time.sleep(0.15)

        # Cleanup expired items
        removed_count = self.cache.cleanup_expired()

        assert removed_count == 1
        assert self.cache.get("key1") is None
        assert self.cache.get("key2") == "value2"
        assert self.cache.get("key3") == "value3"

    def test_different_strategies(self):
        """Test different cache strategies."""
        # Test FIFO strategy
        fifo_cache = CacheManager(max_size=3, strategy=CacheStrategy.FIFO)
        fifo_cache.set("key1", "value1")
        fifo_cache.set("key2", "value2")
        fifo_cache.set("key3", "value3")

        # Access key1 to make it recently used (should not affect FIFO)
        fifo_cache.get("key1")

        # Add new item, should evict key1 (first in)
        fifo_cache.set("key4", "value4")

        assert fifo_cache.get("key1") is None  # Should be evicted
        assert fifo_cache.get("key2") == "value2"  # Should exist
        assert fifo_cache.get("key3") == "value3"  # Should exist
        assert fifo_cache.get("key4") == "value4"  # Should exist


class TestPriceCacheManager:
    """Test price cache management functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.price_cache = PriceCacheManager(max_size=100, default_ttl=300)

    def test_init(self):
        """Test PriceCacheManager initialization."""
        assert self.price_cache.max_size == 100
        assert self.price_cache.default_ttl == 300
        assert isinstance(self.price_cache, CacheManager)
        assert isinstance(self.price_cache.cache, OrderedDict)

    def test_set_price(self):
        """Test setting price data."""
        self.price_cache.set_price("BTC/USDT", 50000.0)

        price = self.price_cache.get_price("BTC/USDT")
        assert price == 50000.0

    def test_get_price_default(self):
        """Test getting price with default value."""
        price = self.price_cache.get_price("BTC/USDT", default=0.0)
        assert price == 0.0

    def test_set_prices_batch(self):
        """Test setting multiple prices at once."""
        prices = {"BTC/USDT": 50000.0, "ETH/USDT": 3000.0, "BNB/USDT": 400.0}

        self.price_cache.set_prices(prices)

        assert self.price_cache.get_price("BTC/USDT") == 50000.0
        assert self.price_cache.get_price("ETH/USDT") == 3000.0
        assert self.price_cache.get_price("BNB/USDT") == 400.0

    def test_get_prices(self):
        """Test getting multiple prices."""
        prices = {"BTC/USDT": 50000.0, "ETH/USDT": 3000.0, "BNB/USDT": 400.0}

        self.price_cache.set_prices(prices)

        # Get all prices
        result = self.price_cache.get_prices(["BTC/USDT", "ETH/USDT", "BNB/USDT"])
        expected = {"BTC/USDT": 50000.0, "ETH/USDT": 3000.0, "BNB/USDT": 400.0}
        assert result == expected

        # Get subset of prices
        result = self.price_cache.get_prices(["BTC/USDT", "ETH/USDT"])
        expected = {"BTC/USDT": 50000.0, "ETH/USDT": 3000.0}
        assert result == expected

        # Get prices with some missing
        result = self.price_cache.get_prices(["BTC/USDT", "XRP/USDT"])
        expected = {"BTC/USDT": 50000.0, "XRP/USDT": None}
        assert result == expected

    def test_get_prices_with_defaults(self):
        """Test getting prices with default values."""
        prices = {"BTC/USDT": 50000.0, "ETH/USDT": 3000.0}

        self.price_cache.set_prices(prices)

        # Get prices with defaults
        result = self.price_cache.get_prices(
            ["BTC/USDT", "ETH/USDT", "XRP/USDT"], default=0.0
        )
        expected = {"BTC/USDT": 50000.0, "ETH/USDT": 3000.0, "XRP/USDT": 0.0}
        assert result == expected

    def test_delete_price(self):
        """Test deleting price data."""
        self.price_cache.set_price("BTC/USDT", 50000.0)

        # Delete price
        result = self.price_cache.delete_price("BTC/USDT")
        assert result is True

        # Verify deletion
        assert self.price_cache.get_price("BTC/USDT") is None

        # Delete nonexistent price
        result = self.price_cache.delete_price("XRP/USDT")
        assert result is False

    def test_clear_prices(self):
        """Test clearing all price data."""
        self.price_cache.set_price("BTC/USDT", 50000.0)
        self.price_cache.set_price("ETH/USDT", 3000.0)

        # Clear all prices
        self.price_cache.clear_prices()

        # Verify cache is empty
        assert self.price_cache.get_price("BTC/USDT") is None
        assert self.price_cache.get_price("ETH/USDT") is None

    def test_get_price_stats(self):
        """Test getting price cache statistics."""
        # Initially empty
        stats = self.price_cache.get_stats()
        assert stats["size"] == 0
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 0

        # Add some prices
        self.price_cache.set_price("BTC/USDT", 50000.0)
        self.price_cache.set_price("ETH/USDT", 3000.0)

        # Get some hits and misses
        self.price_cache.get_price("BTC/USDT")  # hit
        self.price_cache.get_price("ETH/USDT")  # hit
        self.price_cache.get_price("XRP/USDT")  # miss

        stats = self.price_cache.get_stats()
        assert stats["size"] == 2
        assert stats["hit_count"] == 2
        assert stats["miss_count"] == 1

    def test_cleanup_expired_prices(self):
        """Test cleaning up expired price data."""
        self.price_cache.set_price("BTC/USDT", 50000.0, ttl=0.1)
        self.price_cache.set_price("ETH/USDT", 3000.0, ttl=0.2)
        self.price_cache.set_price("BNB/USDT", 400.0)  # No TTL

        # Wait for first item to expire
        time.sleep(0.15)

        # Cleanup expired items
        removed_count = self.price_cache.cleanup_expired()

        assert removed_count == 1
        assert self.price_cache.get_price("BTC/USDT") is None
        assert self.price_cache.get_price("ETH/USDT") == 3000.0
        assert self.price_cache.get_price("BNB/USDT") == 400.0

    def test_price_cache_inherits_from_cache_manager(self):
        """Test that PriceCacheManager inherits from CacheManager."""
        assert isinstance(self.price_cache, CacheManager)

        # Test inherited methods work
        self.price_cache.set("test_key", "test_value")
        assert self.price_cache.get("test_key") == "test_value"

        assert "test_key" in self.price_cache
        assert self.price_cache.size() == 1
