"""
Tests for core/sentry.py - PriceSentry main controller.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from pwatch.core.sentry import PriceSentry
from pwatch.detectors.base import AnomalyEvent


class _StopLoop(Exception):
    """Test-only exception used to stop the infinite monitoring loop safely."""


class TestPriceSentry:
    """Test cases for PriceSentry main controller."""

    def test_init_basic(self, sample_config, mock_exchange, mock_notifier):
        """Test basic initialization of PriceSentry."""
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=5):
            sentry = PriceSentry()

            assert sentry.config == sample_config
            assert sentry.notifier == mock_notifier
            assert sentry.exchange == mock_exchange
            assert sentry.matched_symbols == ["BTC/USDT:USDT"]
            assert sentry.minutes == 5
            assert sentry.threshold == 2.0

    def test_init_with_no_matched_symbols(
        self, sample_config, mock_exchange, mock_notifier
    ):
        """Test initialization when no symbols are matched."""
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=[]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=5):
            with patch("pwatch.core.sentry.logging") as mock_logging:
                sentry = PriceSentry()

                assert sentry.matched_symbols == []
                mock_logging.warning.assert_called_with(
                    "No USDT contract symbols found for exchange %s. "
                    "Run tools/update_markets.py to refresh supported markets.",
                    "binance",
                )

    def test_init_with_custom_config(self, mock_exchange, mock_notifier):
        """Test initialization with custom configuration values."""
        custom_config = {
            "exchange": "okx",
            "defaultTimeframe": "15m",
            "checkInterval": "15m",
            "defaultThreshold": 2.5,
            "notificationChannels": ["telegram"],
            "notificationTimezone": "Asia/Shanghai",
            "notificationSymbols": ["ETH/USDT:USDT"],
            "telegram": {
                "token": "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk",
                "chatId": "123456789",
            },
        }

        with patch("pwatch.core.sentry.load_config", return_value=custom_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["ETH/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=15):
            sentry = PriceSentry()

            assert sentry.minutes == 15
            assert sentry.threshold == 2.5

    def test_notification_symbols_limit_monitored_set(
        self, sample_config, mock_exchange, mock_notifier
    ):
        """仅监控配置文件中选定的合约交易对。"""
        scoped_config = dict(sample_config)
        scoped_config["notificationSymbols"] = [
            "ETH/USDT:USDT",
            "DOGE/USDT:USDT",
        ]

        with patch("pwatch.core.sentry.load_config", return_value=scoped_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts",
            return_value=["BTC/USDT:USDT", "ETH/USDT:USDT"],
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=5), patch(
            "pwatch.core.sentry.logging"
        ) as mock_logging:
            sentry = PriceSentry()

            assert sentry.matched_symbols == ["ETH/USDT:USDT"]
            assert sentry.notification_symbols == ["ETH/USDT:USDT"]
            mock_logging.warning.assert_any_call(
                "Notification symbols ignored because they are not monitored: %s",
                "DOGE/USDT:USDT",
            )

    def test_auto_mode_does_not_warn_about_string_notification_symbols(
        self, sample_config, mock_exchange, mock_notifier
    ):
        config = dict(sample_config)
        config["notificationSymbols"] = "auto"
        config["autoModeLimit"] = 2

        with patch("pwatch.core.sentry.load_config", return_value=config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.fetch_top_volume_symbols",
            return_value=["BTC/USDT:USDT", "ETH/USDT:USDT"],
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=5), patch(
            "pwatch.core.sentry.logging"
        ) as mock_logging:
            sentry = PriceSentry()

        assert sentry.matched_symbols == ["BTC/USDT:USDT", "ETH/USDT:USDT"]
        assert not any(
            "Ignored notificationSymbols of type str" in str(call)
            for call in mock_logging.warning.call_args_list
        )

    def test_rebuild_notification_filter_ignores_auto_selector_without_warning(self):
        sentry = PriceSentry.__new__(PriceSentry)
        sentry.config = {"notificationSymbols": "auto"}
        sentry.matched_symbols = ["BTC/USDT:USDT"]

        with patch("pwatch.core.sentry.logging") as mock_logging:
            sentry._rebuild_notification_filter_locked()

        assert sentry.notification_symbols is None
        assert sentry._notification_symbol_set == set()
        assert not any(
            "Ignored notificationSymbols of type str" in str(call)
            for call in mock_logging.warning.call_args_list
        )




    def test_notification_symbols_invalid_fallback(
        self, sample_config, mock_exchange, mock_notifier
    ):
        """无有效交易对时抛出错误，阻止监控运行。"""
        scoped_config = dict(sample_config)
        scoped_config["notificationSymbols"] = [
            "DOGE/USDT:USDT",
            "LTC/USDT:USDT",
        ]

        with patch("pwatch.core.sentry.load_config", return_value=scoped_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=5), patch(
            "pwatch.core.sentry.logging"
        ) as mock_logging:
            sentry = PriceSentry()

        assert getattr(sentry, "matched_symbols", []) == []
        assert getattr(sentry, "notification_symbols", None) is None
        assert any(
            "No valid notification symbols remain" in str(entry)
            for entry in mock_logging.error.call_args_list
        )

    @pytest.mark.asyncio
    async def test_run_with_no_symbols(
        self, sample_config, mock_exchange, mock_notifier
    ):
        """Test run method when no symbols are matched."""
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=[]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=5):
            sentry = PriceSentry()
            result = await sentry.run()

            # Should return early when no symbols
            assert result is None

    @pytest.mark.asyncio
    async def test_run_normal_operation(
        self, sample_config, mock_exchange, mock_notifier
    ):
        """Test run method with normal operation."""
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=1), patch(
            "pwatch.core.sentry.monitor_top_movers"
        ) as mock_monitor, patch("pwatch.core.sentry.logging"):
            # Mock monitor_top_movers to return None (no price movements)
            mock_monitor.return_value = None

            sentry = PriceSentry()

            # Mock the websocket and time to simulate a short run
            mock_exchange.start_websocket = Mock()
            mock_exchange.close = Mock()
            mock_exchange.ws_connected = True

            # Simulate a short run by stopping the loop safely
            with patch("time.time", side_effect=[0, 0, 61]), patch(
                "asyncio.sleep", side_effect=[None, _StopLoop()]
            ):
                with pytest.raises(_StopLoop):
                    await sentry.run()

            # Verify that websocket was started and closed
            mock_exchange.start_websocket.assert_called_once()
            mock_exchange.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_price_movements(
        self, sample_config, mock_exchange, mock_notifier
    ):
        """Test run method when price movements are detected."""
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=1), patch(
            "pwatch.core.sentry.monitor_top_movers"
        ) as mock_monitor, patch("pwatch.core.sentry.logging"):
            # Mock monitor_top_movers to return unified fact events
            mock_monitor.return_value = [
                {
                    "symbol": "BTC/USDT:USDT",
                    "priority": "HIGH",
                    "change_pct": 5.0,
                    "direction": "up",
                    "minutes": 1,
                    "price_from": 100.0,
                    "price_to": 105.0,
                }
            ]

            sentry = PriceSentry()

            mock_notifier.send.return_value = {
                "success": True,
                "reason": "sent",
                "retryable": False,
            }

            # Mock the websocket and time to simulate a short run
            mock_exchange.start_websocket = Mock()
            mock_exchange.close = Mock()
            mock_exchange.ws_connected = True

            # Simulate a short run by stopping the loop safely
            with patch("time.time", side_effect=[0, 0, 61, 61]), patch(
                "asyncio.sleep", side_effect=[None, _StopLoop()]
            ):
                with pytest.raises(_StopLoop):
                    await sentry.run()

            sent_message = mock_notifier.send.call_args.args[0]
            assert "BTC/USDT:USDT" in sent_message
            assert "5.00%" in sent_message

    def test_custom_check_interval_decouples_schedule(
        self, sample_config, mock_exchange, mock_notifier
    ):
        """checkInterval 应独立控制调度频率。"""
        config = dict(sample_config)
        config["defaultTimeframe"] = "5m"
        config["checkInterval"] = "1m"

        with patch("pwatch.core.sentry.load_config", return_value=config), patch(
            "pwatch.core.sentry.get_exchange",
            return_value=mock_exchange,
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts",
            return_value=["BTC/USDT:USDT"],
        ):
            sentry = PriceSentry()

            assert sentry.minutes == 5
            assert getattr(sentry, "_check_interval", None) == 60

    def test_default_config_values(self, mock_exchange, mock_notifier):
        """Test that default config values are applied correctly."""
        minimal_config = {
            "exchange": "binance",
            "defaultTimeframe": "5m",
            "defaultThreshold": 1.0,
            "notificationChannels": ["telegram"],
            "notificationTimezone": "Asia/Shanghai",
            "notificationSymbols": ["BTC/USDT:USDT"],
            "telegram": {
                "token": "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk",
                "chatId": "123456789",
            },
        }

        with patch("pwatch.core.sentry.load_config", return_value=minimal_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ) as mock_load_symbols, patch("pwatch.core.sentry.parse_timeframe", return_value=5):
            sentry = PriceSentry()

            # Check default values
            mock_load_symbols.assert_called_once_with("binance")
            assert sentry.minutes == 5  # defaultTimeframe '5m' -> 5 minutes
            assert sentry.threshold == 1  # defaultThreshold
            assert getattr(sentry, "_check_interval", None) == 300

    @pytest.mark.asyncio
    async def test_websocket_reconnection(
        self, sample_config, mock_exchange, mock_notifier
    ):
        """Test websocket reconnection logic."""
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=1), patch(
            "pwatch.core.sentry.monitor_top_movers", return_value=None
        ), patch("pwatch.core.sentry.logging"):
            sentry = PriceSentry()

            # Mock websocket to be disconnected
            mock_exchange.start_websocket = Mock()
            mock_exchange.close = Mock()
            mock_exchange.ws_connected = False
            mock_exchange.check_ws_connection = Mock()

            # Simulate time passing and stop the loop safely
            with patch("time.time", side_effect=[0, 0, 61]), patch(
                "asyncio.sleep", side_effect=[None, _StopLoop()]
            ):
                with pytest.raises(_StopLoop):
                    await sentry.run()

            # Verify that reconnection was attempted
            mock_exchange.check_ws_connection.assert_called()


    @pytest.mark.asyncio
    async def test_run_records_final_cooldown_only_after_success(
        self, sample_config, mock_exchange, mock_notifier
    ):
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=1), patch(
            "pwatch.core.sentry.monitor_top_movers", new=AsyncMock(return_value=[
                {
                    "symbol": "BTC/USDT:USDT",
                    "priority": "HIGH",
                    "change_pct": 6.0,
                    "direction": "up",
                    "minutes": 1,
                    "price_from": 100.0,
                    "price_to": 106.0,
                }
            ])), patch(
            "pwatch.core.sentry.notification_cooldown"
        ) as mock_cooldown, patch("pwatch.core.sentry.logging"):
            mock_notifier.send.return_value = {
                "success": True,
                "reason": "sent",
                "retryable": False,
            }
            mock_exchange.start_websocket = Mock()
            mock_exchange.close = Mock()
            mock_exchange.ws_connected = True

            with patch("time.time", side_effect=[0, 0, 61]), patch(
                "asyncio.sleep", side_effect=[None, _StopLoop()]
            ):
                with pytest.raises(_StopLoop):
                    await PriceSentry().run()

            mock_cooldown.record_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_does_not_record_final_cooldown_on_send_failure(
        self, sample_config, mock_exchange, mock_notifier
    ):
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=1), patch(
            "pwatch.core.sentry.monitor_top_movers", new=AsyncMock(return_value=[
                {
                    "symbol": "BTC/USDT:USDT",
                    "priority": "HIGH",
                    "change_pct": 6.0,
                    "direction": "up",
                    "minutes": 1,
                    "price_from": 100.0,
                    "price_to": 106.0,
                }
            ])), patch(
            "pwatch.core.sentry.notification_cooldown"
        ) as mock_cooldown, patch("pwatch.core.sentry.logging"):
            mock_notifier.send.return_value = {
                "success": False,
                "reason": "timeout",
                "retryable": True,
            }
            mock_exchange.start_websocket = Mock()
            mock_exchange.close = Mock()
            mock_exchange.ws_connected = True

            with patch("time.time", side_effect=[0, 0, 61]), patch(
                "asyncio.sleep", side_effect=[None, _StopLoop()]
            ):
                with pytest.raises(_StopLoop):
                    await PriceSentry().run()

            mock_cooldown.record_notification.assert_not_called()


    @pytest.mark.asyncio
    async def test_process_anomaly_events_skips_volume_only_alerts(
        self, sample_config, mock_exchange, mock_notifier
    ):
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=5), patch(
            "pwatch.core.sentry.logging"
        ):
            sentry = PriceSentry()
            sentry._anomaly_events.put(
                AnomalyEvent(
                    symbol="BTC/USDT:USDT",
                    event_type="volume_spike",
                    severity="HIGH",
                    data={"ratio": 25.0, "window_minutes": 10},
                )
            )

            await sentry._process_anomaly_events()

            mock_notifier.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_anomaly_events_keeps_price_volume_confirmation(
        self, sample_config, mock_exchange, mock_notifier
    ):
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=5), patch(
            "pwatch.core.sentry.notification_cooldown"
        ) as mock_cooldown, patch("pwatch.core.sentry.logging"):
            sentry = PriceSentry()
            mock_cooldown.should_notify.return_value = True
            mock_notifier.send.return_value = {
                "success": True,
                "reason": "sent",
                "retryable": False,
            }
            sentry._anomaly_events.put(
                AnomalyEvent(
                    symbol="BTC/USDT:USDT",
                    event_type="price_velocity",
                    severity="HIGH",
                    data={
                        "change_pct": 1.8,
                        "window_seconds": 60,
                        "price_from": 100.0,
                        "price_to": 101.8,
                    },
                )
            )
            sentry._anomaly_events.put(
                AnomalyEvent(
                    symbol="BTC/USDT:USDT",
                    event_type="volume_spike",
                    severity="HIGH",
                    data={"ratio": 25.0, "window_minutes": 10},
                )
            )

            await sentry._process_anomaly_events()

            mock_cooldown.should_notify.assert_called_once_with("BTC/USDT:USDT")
            mock_notifier.send.assert_called_once()
            sent_message = mock_notifier.send.call_args.args[0]
            assert "Volume:" in sent_message
            assert "量能确认" in sent_message

    @pytest.mark.asyncio
    async def test_process_anomaly_events_respects_notification_cooldown(
        self, sample_config, mock_exchange, mock_notifier
    ):
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=5), patch(
            "pwatch.core.sentry.notification_cooldown"
        ) as mock_cooldown, patch("pwatch.core.sentry.logging"):
            sentry = PriceSentry()
            mock_cooldown.should_notify.return_value = False
            sentry._anomaly_events.put(
                AnomalyEvent(
                    symbol="BTC/USDT:USDT",
                    event_type="price_velocity",
                    severity="MEDIUM",
                    data={
                        "change_pct": 0.8,
                        "window_seconds": 30,
                        "price_from": 100.0,
                        "price_to": 100.8,
                    },
                )
            )

            await sentry._process_anomaly_events()

            mock_cooldown.should_notify.assert_called_once_with("BTC/USDT:USDT")
            mock_notifier.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_anomaly_events_records_cooldown_after_realtime_send(
        self, sample_config, mock_exchange, mock_notifier
    ):
        with patch("pwatch.core.sentry.load_config", return_value=sample_config), patch(
            "pwatch.core.sentry.get_exchange", return_value=mock_exchange
        ), patch("pwatch.core.sentry.Notifier", return_value=mock_notifier), patch(
            "pwatch.core.sentry.load_usdt_contracts", return_value=["BTC/USDT:USDT"]
        ), patch("pwatch.core.sentry.parse_timeframe", return_value=5), patch(
            "pwatch.core.sentry.notification_cooldown"
        ) as mock_cooldown, patch("pwatch.core.sentry.logging"):
            sentry = PriceSentry()
            mock_cooldown.should_notify.return_value = True
            mock_notifier.send.return_value = {
                "success": True,
                "reason": "sent",
                "retryable": False,
            }
            sentry._anomaly_events.put(
                AnomalyEvent(
                    symbol="BTC/USDT:USDT",
                    event_type="price_velocity",
                    severity="MEDIUM",
                    data={
                        "change_pct": 0.8,
                        "window_seconds": 30,
                        "price_from": 100.0,
                        "price_to": 100.8,
                    },
                )
            )

            await sentry._process_anomaly_events()

            mock_cooldown.should_notify.assert_called_once_with("BTC/USDT:USDT")
            mock_notifier.send.assert_called_once()
            mock_cooldown.record_notification.assert_called_once_with("BTC/USDT:USDT", 300)
