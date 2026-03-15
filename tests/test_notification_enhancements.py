import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from pwatch.utils.cache_manager import NotificationCooldownManager
from pwatch.utils.monitor_top_movers import monitor_top_movers


class TestNotificationCooldownManager:
    def test_should_notify_basic(self):
        manager = NotificationCooldownManager(default_cooldown_seconds=1.0)
        assert manager.should_notify("BTC/USDT") is True

        manager.record_notification("BTC/USDT")
        assert manager.should_notify("BTC/USDT") is False

        time.sleep(1.1)
        assert manager.should_notify("BTC/USDT") is True

    def test_bypass_cooldown(self):
        manager = NotificationCooldownManager(default_cooldown_seconds=10.0)
        manager.record_notification("BTC/USDT")
        assert manager.should_notify("BTC/USDT") is False
        assert manager.should_notify("BTC/USDT", bypass_cooldown=True) is True

    def test_custom_cooldown(self):
        manager = NotificationCooldownManager(default_cooldown_seconds=10.0)
        manager.record_notification("BTC/USDT", cooldown_seconds=1.0)
        assert manager.should_notify("BTC/USDT") is False

        time.sleep(1.1)
        assert manager.should_notify("BTC/USDT") is True

class TestPriorityClassification:
    @pytest.mark.asyncio
    async def test_priority_classification(self):
        mock_exchange = MagicMock()
        mock_exchange.exchange_name = "TestExchange"
        mock_exchange.get_current_prices = AsyncMock()

        # Initial prices
        mock_exchange.get_price_minutes_ago.return_value = {
            "BTC/USDT": 100.0,
            "ETH/USDT": 100.0,
            "SOL/USDT": 100.0
        }
        # Updated prices
        # BTC: +6% (HIGH), ETH: +3% (MEDIUM), SOL: +1.5% (LOW)
        mock_exchange.get_current_prices.return_value = {
            "BTC/USDT": 106.0,
            "ETH/USDT": 103.0,
            "SOL/USDT": 101.5
        }

        config = {
            "priorityThresholds": {"high": 5.0, "medium": 2.0},
            "notificationTimezone": "UTC"
        }

        message, movers = await monitor_top_movers(
            minutes=1,
            symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            threshold=1.0,
            exchange=mock_exchange,
            config=config
        )

        assert len(movers) == 3
        assert movers[0] == ("BTC/USDT", 6.0, "HIGH")
        assert movers[1] == ("ETH/USDT", 3.0, "MEDIUM")
        assert movers[2] == ("SOL/USDT", 1.5, "LOW")

        assert "🚨 [HIGH]" in message
        assert "⚠️ [MEDIUM]" in message
        assert "ℹ️ [LOW]" in message

    @pytest.mark.asyncio
    async def test_cooldown_integration_in_monitor_top_movers(self):
        mock_exchange = MagicMock()
        mock_exchange.exchange_name = "TestExchange"
        mock_exchange.get_current_prices = AsyncMock()

        mock_exchange.get_price_minutes_ago.return_value = {"BTC/USDT": 100.0, "ETH/USDT": 100.0}
        mock_exchange.get_current_prices.return_value = {"BTC/USDT": 106.0, "ETH/USDT": 106.0}

        config = {
            "priorityThresholds": {"high": 5.0, "medium": 2.0},
            "highPriorityBypassCooldown": True,
            "notificationTimezone": "UTC"
        }

        cooldown_manager = NotificationCooldownManager(default_cooldown_seconds=60.0)
        cooldown_manager.record_notification("BTC/USDT")
        cooldown_manager.record_notification("ETH/USDT")

        # Both are in cooldown.
        # But BTC/USDT at 6% is HIGH, which should bypass if bypass is True.

        # Test 1: Both HIGH, both bypass
        message, movers = await monitor_top_movers(
            minutes=1,
            symbols=["BTC/USDT", "ETH/USDT"],
            threshold=1.0,
            exchange=mock_exchange,
            config=config,
            cooldown_manager=cooldown_manager
        )
        assert len(movers) == 2

        # Test 2: One HIGH (bypass), one MEDIUM (cooldown)
        mock_exchange.get_current_prices.return_value = {"BTC/USDT": 106.0, "ETH/USDT": 103.0}
        message, movers = await monitor_top_movers(
            minutes=1,
            symbols=["BTC/USDT", "ETH/USDT"],
            threshold=1.0,
            exchange=mock_exchange,
            config=config,
            cooldown_manager=cooldown_manager
        )
        assert len(movers) == 1
        assert movers[0][0] == "BTC/USDT"

        # Test 3: Disable bypass
        config["highPriorityBypassCooldown"] = False
        result = await monitor_top_movers(
            minutes=1,
            symbols=["BTC/USDT", "ETH/USDT"],
            threshold=1.0,
            exchange=mock_exchange,
            config=config,
            cooldown_manager=cooldown_manager
        )
        assert result is None
