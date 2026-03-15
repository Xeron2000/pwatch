"""Tests for anomaly detection modules."""

import time

import pytest

from pwatch.core.sentry import PriceSentry
from pwatch.detectors.base import AnomalyEvent, BaseDetector
from pwatch.detectors.price_velocity import PriceVelocityDetector
from pwatch.detectors.volume_spike import VolumeSpikeDetector


# ---------------------------------------------------------------------------
# BaseDetector
# ---------------------------------------------------------------------------


class TestBaseDetector:
    def test_emit_calls_callbacks(self):
        d = BaseDetector({})
        events = []
        d.on_event(events.append)
        ev = AnomalyEvent(symbol="BTC/USDT:USDT", event_type="test", severity="LOW", data={})
        d._emit(ev)
        assert len(events) == 1
        assert events[0] is ev

    def test_emit_swallows_callback_errors(self):
        d = BaseDetector({})
        d.on_event(lambda e: 1 / 0)  # raises ZeroDivisionError
        ev = AnomalyEvent(symbol="X", event_type="t", severity="LOW", data={})
        d._emit(ev)  # should not raise


# ---------------------------------------------------------------------------
# PriceVelocityDetector
# ---------------------------------------------------------------------------


class TestPriceVelocityDetector:
    @pytest.fixture()
    def config(self):
        return {
            "priceVelocity": {
                "enabled": True,
                "windows": [{"seconds": 10, "threshold": 1.0}],
                "cooldownSeconds": 5,
            }
        }

    def test_no_emit_below_threshold(self, config):
        d = PriceVelocityDetector(config)
        events = []
        d.on_event(events.append)

        base = time.time() - 20
        d.on_price_update("BTC", 100.0, base)
        for i in range(1, 15):
            d.on_price_update("BTC", 100.0 + 0.001 * i, base + i)

        assert len(events) == 0

    def test_emit_on_rapid_move(self, config):
        d = PriceVelocityDetector(config)
        events = []
        d.on_event(events.append)

        base = time.time() - 20
        # Price at t=0
        d.on_price_update("BTC", 100.0, base)
        # Build history
        for i in range(1, 12):
            d.on_price_update("BTC", 100.0, base + i)
        # Sudden jump at t=12 (within 10s window)
        d.on_price_update("BTC", 102.0, base + 12)

        assert len(events) == 1
        assert events[0].event_type == "price_velocity"
        assert events[0].data["change_pct"] == pytest.approx(2.0, abs=0.1)

    def test_cooldown_prevents_repeat(self, config):
        d = PriceVelocityDetector(config)
        events = []
        d.on_event(events.append)

        base = time.time() - 30
        d.on_price_update("BTC", 100.0, base)
        for i in range(1, 12):
            d.on_price_update("BTC", 100.0, base + i)
        d.on_price_update("BTC", 102.0, base + 12)
        assert len(events) == 1

        # Another spike within cooldown (5s)
        d.on_price_update("BTC", 104.0, base + 13)
        assert len(events) == 1  # still 1

    def test_disabled_does_nothing(self):
        config = {"priceVelocity": {"enabled": False}}
        d = PriceVelocityDetector(config)
        events = []
        d.on_event(events.append)
        d.on_price_update("BTC", 100.0, time.time())
        d.on_price_update("BTC", 200.0, time.time() + 1)
        assert len(events) == 0

    def test_severity_levels(self, config):
        d = PriceVelocityDetector(config)
        events = []
        d.on_event(events.append)

        base = time.time() - 30
        d.on_price_update("ETH", 100.0, base)
        for i in range(1, 12):
            d.on_price_update("ETH", 100.0, base + i)
        # 4% change in 10s window with threshold 1% → severity HIGH (>= 3x)
        d.on_price_update("ETH", 104.0, base + 12)

        assert len(events) == 1
        assert events[0].severity == "HIGH"


# ---------------------------------------------------------------------------
# VolumeSpikeDetector
# ---------------------------------------------------------------------------


class TestVolumeSpikeDetector:
    @pytest.fixture()
    def config(self):
        return {
            "volumeSpike": {
                "enabled": True,
                "multiplier": 3.0,
                "windowMinutes": 2,
                "minNotifyInterval": "5s",
            }
        }

    def test_no_emit_normal_volume(self, config):
        d = VolumeSpikeDetector(config)
        events = []
        d.on_event(events.append)

        base = time.time() - 120
        # Steady cumulative volume: +10 per second
        for i in range(100):
            d.on_volume_update("BTC", 1000 + i * 10, base + i)

        assert len(events) == 0

    def test_emit_on_volume_spike(self, config):
        d = VolumeSpikeDetector(config)
        events = []
        d.on_event(events.append)

        base = time.time() - 200
        # Normal volume for 150s: +10 per second (cumulative)
        for i in range(150):
            d.on_volume_update("BTC", 1000 + i * 10, base + i)

        # Sudden spike in the last 10s: +200 per second
        for i in range(150, 160):
            d.on_volume_update("BTC", 1000 + 150 * 10 + (i - 150) * 200, base + i)

        assert len(events) >= 1
        assert events[0].event_type == "volume_spike"
        assert events[0].data["ratio"] >= 3.0

    def test_disabled_does_nothing(self):
        config = {"volumeSpike": {"enabled": False}}
        d = VolumeSpikeDetector(config)
        events = []
        d.on_event(events.append)
        d.on_volume_update("BTC", 1000, time.time())
        assert len(events) == 0

    def test_handles_volume_counter_reset(self, config):
        """Volume drops when 24h window rolls — should not crash."""
        d = VolumeSpikeDetector(config)
        events = []
        d.on_event(events.append)

        base = time.time() - 120
        for i in range(50):
            d.on_volume_update("BTC", 5000 + i * 10, base + i)
        # Volume "resets" (drops)
        d.on_volume_update("BTC", 100, base + 51)
        d.on_volume_update("BTC", 110, base + 52)
        # Should not crash
        assert True

    def test_update_config(self, config):
        d = VolumeSpikeDetector(config)
        assert d.multiplier == 3.0

        new_config = {
            "volumeSpike": {
                "enabled": True,
                "multiplier": 5.0,
                "windowMinutes": 5,
                "minNotifyInterval": "10s",
            }
        }
        d.update_config(new_config)
        assert d.multiplier == 5.0
        assert d.window_minutes == 5


# ---------------------------------------------------------------------------
# AnomalyEvent
# ---------------------------------------------------------------------------


class TestAnomalyEvent:
    def test_default_timestamp(self):
        ev = AnomalyEvent(symbol="X", event_type="t", severity="LOW", data={})
        assert ev.timestamp > 0

    def test_custom_timestamp(self):
        ev = AnomalyEvent(symbol="X", event_type="t", severity="LOW", data={}, timestamp=42.0)
        assert ev.timestamp == 42.0


# ---------------------------------------------------------------------------
# Combined Alert Formatting
# ---------------------------------------------------------------------------


class TestFormatCombinedAlert:
    """Tests for PriceSentry._format_combined_alert."""

    def _price_event(self, symbol="BTC/USDT:USDT", change=2.5, window=30):
        return AnomalyEvent(
            symbol=symbol,
            event_type="price_velocity",
            severity="MEDIUM",
            data={
                "change_pct": change,
                "window_seconds": window,
                "threshold": 0.5,
                "price_from": 60000.0,
                "price_to": 60000.0 * (1 + change / 100),
            },
        )

    def _volume_event(self, symbol="BTC/USDT:USDT", ratio=4.0):
        return AnomalyEvent(
            symbol=symbol,
            event_type="volume_spike",
            severity="MEDIUM",
            data={"ratio": ratio, "recent_avg": 500, "window_avg": 125, "window_minutes": 10},
        )

    def test_price_only_up(self):
        events = {"price_velocity": self._price_event(change=1.5)}
        msg = PriceSentry._format_combined_alert("BTC/USDT:USDT", events)
        assert "1.50%" in msg
        assert "fakeout" in msg.lower()

    def test_price_only_down(self):
        events = {"price_velocity": self._price_event(change=-2.0)}
        msg = PriceSentry._format_combined_alert("BTC/USDT:USDT", events)
        assert "2.00%" in msg
        assert "bounce" in msg.lower()

    def test_volume_only(self):
        events = {"volume_spike": self._volume_event()}
        msg = PriceSentry._format_combined_alert("BTC/USDT:USDT", events)
        assert "4.0x" in msg
        assert "breakout" in msg.lower()

    def test_price_up_with_volume(self):
        events = {
            "price_velocity": self._price_event(change=3.0),
            "volume_spike": self._volume_event(ratio=4.0),
        }
        msg = PriceSentry._format_combined_alert("BTC/USDT:USDT", events)
        assert "3.00%" in msg
        assert "4.0x" in msg
        assert "rally" in msg.lower() or "continuation" in msg.lower()

    def test_price_down_with_heavy_volume(self):
        events = {
            "price_velocity": self._price_event(change=-5.0),
            "volume_spike": self._volume_event(ratio=6.0),
        }
        msg = PriceSentry._format_combined_alert("BTC/USDT:USDT", events)
        assert "capitulation" in msg.lower() or "support" in msg.lower()

    def test_empty_events(self):
        msg = PriceSentry._format_combined_alert("X", {})
        assert msg == ""
