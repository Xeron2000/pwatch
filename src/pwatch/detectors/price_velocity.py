"""Price velocity detector — detects rapid price movements in real time.

Evaluates price change percentage over multiple sliding windows on every
WebSocket tick.  When any window's change exceeds its threshold, an event
is emitted.
"""

import time
from collections import deque

from .base import AnomalyEvent, BaseDetector

# Keep enough samples for the longest window (default 120s at ~1 tick/s)
_MAX_SAMPLES = 300
_DEFAULT_WINDOWS = [
    {"seconds": 30, "threshold": 0.5},
    {"seconds": 60, "threshold": 0.8},
    {"seconds": 120, "threshold": 1.2},
]
# Don't re-notify the same symbol+window within this period
_NOTIFY_COOLDOWN_S = 60


class PriceVelocityDetector(BaseDetector):
    """Detects when price moves too fast within configurable time windows."""

    def __init__(self, config: dict):
        super().__init__(config)
        pv = config.get("priceVelocity", {})
        self.enabled = pv.get("enabled", True)
        self.windows = pv.get("windows", _DEFAULT_WINDOWS)
        self.cooldown_s = pv.get("cooldownSeconds", _NOTIFY_COOLDOWN_S)

        # symbol -> deque of (timestamp_s, price)
        self._price_history: dict[str, deque] = {}
        # "symbol_windowSeconds" -> last notify timestamp
        self._last_notify: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on_price_update(self, symbol: str, price: float, timestamp: float):
        if not self.enabled:
            return

        history = self._price_history.get(symbol)
        if history is None:
            history = deque(maxlen=_MAX_SAMPLES)
            self._price_history[symbol] = history

        history.append((timestamp, price))
        self._check_velocity(symbol, price, timestamp)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_velocity(self, symbol: str, current_price: float, now: float):
        history = self._price_history[symbol]
        if len(history) < 5:
            return

        for window in self.windows:
            window_seconds = window["seconds"]
            threshold = window["threshold"]

            target_time = now - window_seconds

            # Find the price closest to (but not after) target_time
            past_price = None
            for t, p in history:
                if t <= target_time:
                    past_price = p

            if past_price is None or past_price <= 0:
                continue

            change_pct = ((current_price - past_price) / past_price) * 100

            if abs(change_pct) < threshold:
                continue

            # Cooldown per symbol+window
            key = f"{symbol}_{window_seconds}"
            last = self._last_notify.get(key, 0)
            if now - last < self.cooldown_s:
                continue
            self._last_notify[key] = now

            abs_change = abs(change_pct)
            if abs_change >= threshold * 3:
                severity = "HIGH"
            elif abs_change >= threshold * 2:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            self._emit(
                AnomalyEvent(
                    symbol=symbol,
                    event_type="price_velocity",
                    severity=severity,
                    data={
                        "change_pct": round(change_pct, 2),
                        "window_seconds": window_seconds,
                        "threshold": threshold,
                        "price_from": round(past_price, 8),
                        "price_to": round(current_price, 8),
                    },
                    timestamp=now,
                )
            )
            # Emit only for the shortest triggering window
            break

    def update_config(self, config: dict):
        super().update_config(config)
        pv = config.get("priceVelocity", {})
        self.enabled = pv.get("enabled", True)
        self.windows = pv.get("windows", _DEFAULT_WINDOWS)
        self.cooldown_s = pv.get("cooldownSeconds", _NOTIFY_COOLDOWN_S)
