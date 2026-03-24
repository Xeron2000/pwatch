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
        mock_exchange.get_price_minutes_ago = AsyncMock()

        mock_exchange.get_price_minutes_ago.return_value = {
            "BTC/USDT": 100.0,
            "ETH/USDT": 100.0,
            "SOL/USDT": 100.0,
        }
        mock_exchange.get_current_prices.return_value = {
            "BTC/USDT": 106.0,
            "ETH/USDT": 103.0,
            "SOL/USDT": 101.5,
        }

        config = {
            "priorityThresholds": {"high": 5.0, "medium": 2.0},
            "notificationTimezone": "UTC",
        }

        events = await monitor_top_movers(
            minutes=1,
            symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            threshold=1.0,
            exchange=mock_exchange,
            config=config,
        )

        assert len(events) == 3
        assert events[0]["symbol"] == "BTC/USDT"
        assert events[0]["priority"] == "HIGH"
        assert events[0]["direction"] == "up"
        assert events[1]["symbol"] == "ETH/USDT"
        assert events[1]["priority"] == "MEDIUM"
        assert events[2]["symbol"] == "SOL/USDT"
        assert events[2]["priority"] == "LOW"

    @pytest.mark.asyncio
    async def test_cooldown_integration_in_monitor_top_movers(self):
        mock_exchange = MagicMock()
        mock_exchange.exchange_name = "TestExchange"
        mock_exchange.get_current_prices = AsyncMock()
        mock_exchange.get_price_minutes_ago = AsyncMock()

        mock_exchange.get_price_minutes_ago.return_value = {"BTC/USDT": 100.0, "ETH/USDT": 100.0}
        mock_exchange.get_current_prices.return_value = {"BTC/USDT": 106.0, "ETH/USDT": 106.0}

        config = {
            "priorityThresholds": {"high": 5.0, "medium": 2.0},
            "highPriorityBypassCooldown": True,
            "notificationTimezone": "UTC",
        }

        cooldown_manager = NotificationCooldownManager(default_cooldown_seconds=60.0)
        cooldown_manager.record_notification("BTC/USDT")
        cooldown_manager.record_notification("ETH/USDT")

        events = await monitor_top_movers(
            minutes=1,
            symbols=["BTC/USDT", "ETH/USDT"],
            threshold=1.0,
            exchange=mock_exchange,
            config=config,
            cooldown_manager=cooldown_manager,
        )
        assert len(events) == 2

        mock_exchange.get_current_prices.return_value = {"BTC/USDT": 106.0, "ETH/USDT": 103.0}
        events = await monitor_top_movers(
            minutes=1,
            symbols=["BTC/USDT", "ETH/USDT"],
            threshold=1.0,
            exchange=mock_exchange,
            config=config,
            cooldown_manager=cooldown_manager,
        )
        assert len(events) == 1
        assert events[0]["symbol"] == "BTC/USDT"

        config["highPriorityBypassCooldown"] = False
        result = await monitor_top_movers(
            minutes=1,
            symbols=["BTC/USDT", "ETH/USDT"],
            threshold=1.0,
            exchange=mock_exchange,
            config=config,
            cooldown_manager=cooldown_manager,
        )
        assert result is None
