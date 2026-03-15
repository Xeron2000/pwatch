# core/sentry.py

import asyncio
import logging
import time
from queue import Empty, Queue
from threading import RLock
from typing import List, Optional, Set, Tuple

from pwatch.core.config_manager import ConfigUpdateEvent, config_manager
from pwatch.core.notifier import Notifier
from pwatch.detectors import AnomalyEvent, PriceVelocityDetector, VolumeSpikeDetector
from pwatch.utils.cache_manager import notification_cooldown
from pwatch.utils.config_validator import config_validator
from pwatch.utils.error_handler import ErrorSeverity, error_handler
from pwatch.utils.get_exchange import get_exchange
from pwatch.utils.monitor_top_movers import monitor_top_movers
from pwatch.utils.parse_timeframe import parse_timeframe
from pwatch.utils.performance_monitor import performance_monitor
from pwatch.utils.supported_markets import load_usdt_contracts
from pwatch.utils.top_volume_symbols import fetch_top_volume_symbols


def load_config() -> dict:
    """Backward compatible shim for legacy tests mocking core.sentry.load_config."""
    return config_manager.get_config()


class PriceSentry:
    # 4-hour refresh interval for auto mode (in seconds)
    AUTO_REFRESH_INTERVAL = 4 * 60 * 60

    def __init__(self):
        try:
            # Start performance monitoring
            performance_monitor.start()

            self._config_lock = RLock()
            self._config_events: "Queue[ConfigUpdateEvent]" = Queue()
            self.notification_symbols: Optional[List[str]] = None
            self._notification_symbol_set: Set[str] = set()
            # Initialize matched_symbols early to prevent AttributeError
            self.matched_symbols: List[str] = []
            # Track auto mode and last refresh time
            self._auto_mode: bool = False
            self._last_auto_refresh: float = 0

            # Anomaly event queue (fed by detectors running in WS thread)
            self._anomaly_events: "Queue[AnomalyEvent]" = Queue()

            # Load configuration (patchable for unit tests while defaulting to manager data)
            self.config = load_config()

            # Validate configuration
            validation_result = config_validator.validate_config(self.config)
            if not validation_result.is_valid:
                error_handler.handle_config_error(
                    Exception("Configuration validation failed"),
                    {
                        "component": "PriceSentry",
                        "operation": "config_validation",
                        "errors": validation_result.errors,
                    },
                    ErrorSeverity.CRITICAL,
                )
                raise ValueError(f"Configuration validation failed: {validation_result.errors}")

            # Log validation warnings and info
            if validation_result.warnings:
                for warning in validation_result.warnings:
                    logging.warning(f"Configuration warning: {warning}")

            if validation_result.info:
                for info in validation_result.info:
                    logging.info(f"Configuration info: {info}")

            self.notifier = Notifier(self.config)

            exchange_name = self.config.get("exchange", "binance")
            self.exchange = get_exchange(exchange_name)

            try:
                self._sync_symbols(exchange_name)
            except ValueError as exc:
                error_handler.handle_config_error(
                    exc,
                    {
                        "exchange": exchange_name,
                        "operation": "symbol_bootstrap",
                    },
                    ErrorSeverity.ERROR,
                )
                logging.error("Failed to bootstrap symbols: %s", exc)
                return

            if not self.matched_symbols:
                logging.warning(
                    "No USDT contract symbols found for exchange %s. "
                    "Run tools/update_markets.py to refresh supported markets.",
                    exchange_name,
                )
                error_handler.handle_config_error(
                    Exception("No matched symbols found"),
                    {
                        "exchange": exchange_name,
                        "operation": "symbol_bootstrap",
                    },
                    ErrorSeverity.WARNING,
                )
                return

            self._refresh_runtime_settings()
            self._setup_detectors()

            config_manager.subscribe(self._enqueue_config_update)
            logging.info("PriceSentry initialized successfully")

        except Exception as e:
            error_handler.handle_config_error(
                e,
                {"component": "PriceSentry", "operation": "initialization"},
                ErrorSeverity.CRITICAL,
            )
            raise

    async def run(self):
        if not self.matched_symbols:
            return

        try:
            self.exchange.start_websocket(self.matched_symbols)
            logging.info(f"Started WebSocket connection for {len(self.matched_symbols)} symbols")
        except Exception as e:
            error_handler.handle_network_error(
                e,
                {
                    "component": "PriceSentry",
                    "operation": "websocket_start",
                    "symbols_count": len(self.matched_symbols),
                },
                ErrorSeverity.ERROR,
            )
            raise

        # Wait for WebSocket to receive initial price data
        warmup_seconds = 5
        logging.info(f"Waiting {warmup_seconds}s for WebSocket to collect initial price data...")
        await asyncio.sleep(warmup_seconds)

        last_check_time = time.time()  # Start from now, not 0
        last_ws_check_time = time.time()

        try:
            logging.info("Entering main loop, starting price movement monitoring")
            minutes_snapshot, _, check_interval, _, _ = self._snapshot_runtime_state()
            interval_minutes = max(check_interval / 60, 1)
            logging.info(
                "Check interval set to %.2f minutes (%s seconds)",
                interval_minutes,
                int(check_interval),
            )
            while True:
                self._process_config_updates()

                # Process real-time anomaly events from detectors
                await self._process_anomaly_events()

                # Check for auto mode refresh (every 4 hours)
                if self._auto_mode:
                    self._check_auto_refresh()

                (
                    minutes_snapshot,
                    threshold_snapshot,
                    check_interval,
                    symbols_snapshot,
                    notification_filter_snapshot,
                ) = self._snapshot_runtime_state()

                current_time = time.time()

                if current_time - last_check_time >= check_interval:
                    logging.info(
                        "Checking price movements, %s seconds since last check",
                        int(current_time - last_check_time),
                    )

                    try:
                        if not symbols_snapshot:
                            logging.warning("No symbols available for monitoring")
                            last_check_time = current_time
                            continue

                        result = await monitor_top_movers(
                            minutes_snapshot,
                            symbols_snapshot,
                            threshold_snapshot,
                            self.exchange,
                            self.config,
                            notification_filter_snapshot,
                            cooldown_manager=notification_cooldown,
                        )

                        if result:
                            message, top_movers_sorted = result
                            logging.info(f"Detected price movements exceeding threshold, message content: {message}")

                            # Step 1: Send text notification immediately
                            if self.notifier.send(message):
                                # Record notifications for cooldown tracking
                                cooldown_source = self.config.get("notificationCooldown", "5m")
                                try:
                                    cooldown_seconds = parse_timeframe(cooldown_source) * 60
                                except Exception:
                                    cooldown_seconds = 300.0

                                for mover in top_movers_sorted:
                                    symbol = mover[0]
                                    notification_cooldown.record_notification(symbol, cooldown_seconds)
                        else:
                            logging.info("No price movements exceeding threshold detected")
                    except Exception as e:
                        error_handler.handle_api_error(
                            e,
                            {
                                "component": "PriceSentry",
                                "operation": "monitor_top_movers",
                            },
                            ErrorSeverity.ERROR,
                        )
                        logging.error(f"Error in price monitoring: {e}")
                        continue

                    last_check_time = current_time

                if current_time - last_ws_check_time >= 60:
                    last_ws_check_time = current_time
                    logging.debug("Checking WebSocket connection status")
                    if not self.exchange.ws_connected:
                        logging.warning("WebSocket connection disconnected, attempting to reconnect")
                        try:
                            self.exchange.check_ws_connection()
                        except Exception as e:
                            error_handler.handle_network_error(
                                e,
                                {
                                    "component": "PriceSentry",
                                    "operation": "websocket_reconnect",
                                },
                                ErrorSeverity.WARNING,
                            )
                    if hasattr(self.exchange, "last_prices"):
                        logging.debug(f"Number of symbols with cached prices: {len(self.exchange.last_prices)}")

                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logging.info("Received keyboard interrupt. Shutting down...")
        finally:
            try:
                self.exchange.close()
            except Exception as e:
                error_handler.handle_api_error(
                    e,
                    {"component": "PriceSentry", "operation": "cleanup"},
                    ErrorSeverity.WARNING,
                )

    def _enqueue_config_update(self, event: ConfigUpdateEvent) -> None:
        """Receive config updates from ConfigManager on background threads."""
        try:
            self._config_events.put_nowait(event)
        except Exception:
            # Fallback to blocking put; queue is unbounded but guard just in case.
            self._config_events.put(event)

    def _setup_detectors(self) -> None:
        """Create and register anomaly detectors on the exchange."""
        self._velocity_detector = PriceVelocityDetector(self.config)
        self._volume_detector = VolumeSpikeDetector(self.config)

        def _on_anomaly(event: AnomalyEvent) -> None:
            try:
                self._anomaly_events.put_nowait(event)
            except Exception:
                self._anomaly_events.put(event)

        self._velocity_detector.on_event(_on_anomaly)
        self._volume_detector.on_event(_on_anomaly)

        self.exchange.register_detector(self._velocity_detector)
        self.exchange.register_detector(self._volume_detector)

        logging.info(
            "Anomaly detectors registered (velocity=%s, volume=%s)",
            self.config.get("priceVelocity", {}).get("enabled", True),
            self.config.get("volumeSpike", {}).get("enabled", True),
        )

    async def _process_anomaly_events(self) -> None:
        """Drain the anomaly event queue, combine per-symbol, and send notifications."""
        events: list[AnomalyEvent] = []
        while True:
            try:
                events.append(self._anomaly_events.get_nowait())
            except Empty:
                break

        if not events:
            return

        # Group events by symbol, keeping best severity per event_type
        severity_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        by_symbol: dict[str, dict[str, AnomalyEvent]] = {}
        for ev in events:
            sym_events = by_symbol.setdefault(ev.symbol, {})
            existing = sym_events.get(ev.event_type)
            if existing is None or severity_rank.get(ev.severity, 0) > severity_rank.get(existing.severity, 0):
                sym_events[ev.event_type] = ev

        for symbol, sym_events in by_symbol.items():
            message = self._format_combined_alert(symbol, sym_events)
            if message:
                self.notifier.send(message)

    @staticmethod
    def _format_combined_alert(symbol: str, events: dict[str, AnomalyEvent]) -> str:
        """Format combined price + volume events into a single alert with trading hints."""
        price_ev = events.get("price_velocity")
        volume_ev = events.get("volume_spike")

        if not price_ev and not volume_ev:
            return ""

        # Determine overall severity
        severity_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
        max_sev = max(
            (severity_rank.get(e.severity, 0) for e in events.values()),
            default=0,
        )
        icon = "🚨" if max_sev >= 3 else "⚠️" if max_sev >= 2 else "ℹ️"

        lines = [f"{icon} **`{symbol}`**\n"]

        # Price info
        if price_ev:
            d = price_ev.data
            change = d["change_pct"]
            arrow = "🔼" if change > 0 else "🔽"
            lines.append(
                f"{arrow} **{abs(change):.2f}%** in {d['window_seconds']}s "
                f"(*{d['price_from']:.4f}* → *{d['price_to']:.4f}*)"
            )

        # Volume info
        if volume_ev:
            d = volume_ev.data
            lines.append(f"📊 Volume: **{d['ratio']:.1f}x** avg ({d['window_minutes']}m window)")

        # Trading suggestion
        lines.append("")
        if price_ev and volume_ev:
            change = price_ev.data["change_pct"]
            ratio = volume_ev.data["ratio"]
            if change > 0:
                if ratio >= 5:
                    lines.append("💡 Heavy volume breakout — strong long signal")
                else:
                    lines.append("💡 Volume-confirmed rally — watch for continuation")
            else:
                if ratio >= 5:
                    lines.append("💡 Capitulation selling — watch for support levels")
                else:
                    lines.append("💡 Volume-confirmed drop — risk of further downside")
        elif volume_ev:
            lines.append("💡 Abnormal volume — watch for directional breakout")
        elif price_ev:
            change = price_ev.data["change_pct"]
            if change > 0:
                lines.append("💡 Low-volume pump — potential fakeout, wait for confirmation")
            else:
                lines.append("💡 Low-volume dip — possible shakeout, may bounce")

        return "\n".join(lines)

    def _process_config_updates(self) -> None:
        while True:
            try:
                event = self._config_events.get_nowait()
            except Empty:
                break
            self._apply_config_update(event)

    def _apply_config_update(self, event: ConfigUpdateEvent) -> None:
        start_time = time.time()
        changed_keys = ", ".join(sorted(event.diff.changed_keys)) or "<none>"
        logging.info("Processing configuration update; changed keys: %s", changed_keys)
        if event.warnings:
            for warning in event.warnings:
                logging.warning("Configuration warning: %s", warning)

        with self._config_lock:
            self.config = event.new_config

        self._refresh_runtime_settings()

        if event.diff.requires_symbol_reload:
            self._reload_runtime_components(event)

        elapsed = time.time() - start_time
        if elapsed > 5:
            logging.warning(
                "Configuration update processing exceeded 5s target: %.2fs",
                elapsed,
            )
        else:
            logging.info("Configuration update applied in %.2fs", elapsed)

    def _refresh_runtime_settings(self) -> None:
        with self._config_lock:
            timeframe = self.config.get("defaultTimeframe", "5m")
            try:
                minutes = parse_timeframe(timeframe)
            except Exception as exc:
                logging.error(
                    "Failed to parse timeframe '%s': %s. Using previous value.",
                    timeframe,
                    exc,
                )
                minutes = getattr(self, "minutes", parse_timeframe("5m"))
            self.minutes = minutes
            interval_source = self.config.get("checkInterval") or timeframe
            try:
                interval_minutes = parse_timeframe(interval_source)
            except Exception as exc:
                logging.error(
                    "Failed to parse check interval '%s': %s. Using previous value.",
                    interval_source,
                    exc,
                )
                interval_seconds = getattr(
                    self,
                    "_check_interval",
                    getattr(self, "minutes", parse_timeframe("5m")) * 60,
                )
            else:
                if interval_minutes <= 0:
                    logging.warning(
                        "Parsed check interval '%s' resolved to %s minutes. Falling back to timeframe duration.",
                        interval_source,
                        interval_minutes,
                    )
                    interval_minutes = max(self.minutes, 1)
                interval_seconds = max(interval_minutes, 1) * 60
            self._check_interval = interval_seconds
            self.check_interval_minutes = max(int(interval_seconds / 60) or 1, 1)
            self.threshold = self.config.get("defaultThreshold", 1)

            # Update notification cooldown settings
            cooldown_source = self.config.get("notificationCooldown", "5m")
            try:
                cooldown_seconds = parse_timeframe(cooldown_source) * 60
                notification_cooldown.update_default_cooldown(cooldown_seconds)
            except Exception as exc:
                logging.error(f"Failed to parse notificationCooldown '{cooldown_source}': {exc}")

            self._rebuild_notification_filter_locked()
            if hasattr(self, "notifier") and self.notifier is not None:
                self.notifier.update_config(self.config)

            # Update detector configs
            if hasattr(self, "_velocity_detector"):
                self._velocity_detector.update_config(self.config)
            if hasattr(self, "_volume_detector"):
                self._volume_detector.update_config(self.config)

    def _reload_runtime_components(self, event: ConfigUpdateEvent) -> None:
        exchange_name = self.config.get("exchange", "binance")
        logging.info(
            "Reloading exchange and symbol set due to config update (keys: %s)",
            ", ".join(sorted(event.diff.changed_keys)) or "<none>",
        )

        try:
            self.exchange.close()
        except Exception as exc:
            logging.warning(f"Failed to close existing exchange cleanly: {exc}")

        try:
            self.exchange = get_exchange(exchange_name)
        except Exception as exc:
            error_handler.handle_config_error(
                exc,
                {
                    "component": "PriceSentry",
                    "operation": "exchange_reload",
                    "exchange": exchange_name,
                },
                ErrorSeverity.CRITICAL,
            )
            logging.error("Exchange reload aborted: %s", exc)
            return

        try:
            self._sync_symbols(exchange_name)
        except ValueError as exc:
            error_handler.handle_config_error(
                exc,
                {
                    "component": "PriceSentry",
                    "operation": "symbol_reload",
                    "exchange": exchange_name,
                },
                ErrorSeverity.ERROR,
            )
            logging.error("Symbol reload aborted: %s", exc)
            return

        if not self.matched_symbols:
            logging.warning("Symbol reload produced empty set; skipping websocket")
            error_handler.handle_config_error(
                Exception("No matched symbols found"),
                {
                    "component": "PriceSentry",
                    "operation": "symbol_reload",
                    "exchange": exchange_name,
                },
                ErrorSeverity.WARNING,
            )
            return

        try:
            self.exchange.start_websocket(self.matched_symbols)
        except Exception as exc:
            error_handler.handle_network_error(
                exc,
                {
                    "component": "PriceSentry",
                    "operation": "websocket_restart",
                    "symbols_count": len(self.matched_symbols),
                },
                ErrorSeverity.ERROR,
            )
            logging.error("Failed to restart websocket after config change: %s", exc)
            return

        logging.info(
            "Exchange and symbol sets reloaded successfully (%s symbols)",
            len(self.matched_symbols),
        )

    def _rebuild_notification_filter_locked(self) -> None:
        selection = self.config.get("notificationSymbols")
        monitored = list(getattr(self, "matched_symbols", []))
        monitored_set = set(monitored)

        if not selection:
            self.notification_symbols = None
            self._notification_symbol_set = set()
            return

        allowed: List[str] = []
        missing: List[str] = []

        if isinstance(selection, list):
            for raw_symbol in selection:
                if not isinstance(raw_symbol, str):
                    continue
                candidate = raw_symbol.strip()
                if not candidate:
                    continue
                if monitored_set and candidate not in monitored_set:
                    missing.append(candidate)
                    continue
                allowed.append(candidate)
        else:
            logging.warning(
                "Ignored notificationSymbols of type %s; expected list of symbol strings.",
                type(selection).__name__,
            )

        if missing:
            logging.warning(
                "Notification symbols ignored because they are not monitored: %s",
                ", ".join(sorted(set(missing))),
            )

        if allowed:
            self.notification_symbols = allowed
            self._notification_symbol_set = set(allowed)
        else:
            self.notification_symbols = None
            self._notification_symbol_set = set()

    def _sync_symbols(self, exchange_name: str) -> None:
        selection = self.config.get("notificationSymbols")

        # Check for auto mode
        is_auto = selection == "auto" or (not selection)
        self._auto_mode = is_auto

        if is_auto:
            auto_limit = self.config.get("autoModeLimit", 50)
            logging.info("Auto mode enabled, fetching top %s volume symbols", auto_limit)
            monitored_symbols = fetch_top_volume_symbols(exchange_name, limit=auto_limit)
            self._last_auto_refresh = time.time()

            if not monitored_symbols:
                logging.error("Failed to fetch top volume symbols in auto mode")
                raise ValueError("Failed to fetch top volume symbols")

            with self._config_lock:
                self.matched_symbols = monitored_symbols
                self._rebuild_notification_filter_locked()

            logging.info(
                "Auto mode: loaded %s top volume symbols for %s: %s",
                len(monitored_symbols),
                exchange_name,
                ", ".join(monitored_symbols[:8]) + (" ..." if len(monitored_symbols) > 8 else ""),
            )
            return

        # Manual mode: validate against available symbols
        available_symbols = load_usdt_contracts(exchange_name)

        if not available_symbols:
            with self._config_lock:
                self.matched_symbols = []
                self._rebuild_notification_filter_locked()
            logging.warning(
                "No USDT contract symbols available for exchange %s. "
                "Ensure supported_markets.json is up-to-date.",
                exchange_name,
            )
            return

        if not isinstance(selection, list) or not selection:
            message = (
                "Configuration must include at least one notification symbol or set to 'auto'. "
                "Save the configuration with a non-empty list before restarting."
            )
            logging.error(message)
            raise ValueError(message)

        available_set = set(available_symbols)
        monitored_symbols: List[str] = []
        missing_symbols: List[str] = []

        for raw_symbol in selection:
            if not isinstance(raw_symbol, str):
                continue
            candidate = raw_symbol.strip()
            if not candidate:
                continue
            if candidate in available_set:
                monitored_symbols.append(candidate)
            else:
                missing_symbols.append(candidate)

        if not monitored_symbols:
            detail = ""
            if missing_symbols:
                detail = " Missing symbols: " + ", ".join(sorted(set(missing_symbols))) + "."
            message = (
                "No valid notification symbols remain after filtering against available contracts. "
                "Select at least one supported symbol and retry." + detail
            )
            logging.error(message)
            logging.info(
                "Hint: Ensure symbols are in the correct format (e.g., 'BTC/USDT:USDT' for OKX). "
                "Run 'uv run python tools/update_markets.py --exchanges %s' to refresh market data.",
                exchange_name,
            )
            raise ValueError(message)

        with self._config_lock:
            self.matched_symbols = monitored_symbols
            self._rebuild_notification_filter_locked()

        if monitored_symbols:
            logging.info(
                "Loaded %s USDT contract symbols for exchange %s: %s",
                len(monitored_symbols),
                exchange_name,
                ", ".join(monitored_symbols[:5]) + (" ..." if len(monitored_symbols) > 5 else ""),
            )
        else:
            logging.warning(
                "No USDT contract symbols available for exchange %s. "
                "Ensure supported_markets.json is up-to-date.",
                exchange_name,
            )

    def _check_auto_refresh(self) -> None:
        """Check if auto mode symbols need refresh (every 4 hours)."""
        if not self._auto_mode:
            return

        current_time = time.time()
        if current_time - self._last_auto_refresh < self.AUTO_REFRESH_INTERVAL:
            return

        exchange_name = self.config.get("exchange", "binance")
        logging.info("Auto mode: refreshing top volume symbols (4-hour interval)")

        try:
            new_symbols = fetch_top_volume_symbols(exchange_name, limit=self.config.get("autoModeLimit", 50))
            if not new_symbols:
                logging.warning("Auto refresh returned empty symbols, keeping current list")
                return

            old_symbols = set(self.matched_symbols)
            new_symbols_set = set(new_symbols)

            if old_symbols != new_symbols_set:
                added = new_symbols_set - old_symbols
                removed = old_symbols - new_symbols_set
                if added:
                    logging.info("Auto refresh: added symbols: %s", ", ".join(sorted(added)))
                if removed:
                    logging.info("Auto refresh: removed symbols: %s", ", ".join(sorted(removed)))

                # Restart websocket with new symbols
                try:
                    self.exchange.close()
                except Exception as e:
                    logging.warning(f"Failed to close websocket during auto refresh: {e}")

                with self._config_lock:
                    self.matched_symbols = new_symbols
                    self._rebuild_notification_filter_locked()

                try:
                    self.exchange.start_websocket(new_symbols)
                    logging.info("Auto refresh: websocket restarted with %s symbols", len(new_symbols))
                except Exception as e:
                    logging.error(f"Failed to restart websocket after auto refresh: {e}")
            else:
                logging.info("Auto refresh: no symbol changes detected")

            self._last_auto_refresh = current_time

        except Exception as e:
            logging.error(f"Auto refresh failed: {e}")

    def _snapshot_runtime_state(
        self,
    ) -> Tuple[int, float, float, List[str], Optional[List[str]]]:
        with self._config_lock:
            minutes = getattr(self, "minutes", parse_timeframe("5m"))
            threshold = getattr(self, "threshold", 1.0)
            check_interval = getattr(
                self,
                "_check_interval",
                getattr(self, "minutes", parse_timeframe("5m")) * 60,
            )
            symbols_snapshot = list(getattr(self, "matched_symbols", []))
            notification_snapshot = list(self.notification_symbols) if self.notification_symbols else None
        return (
            minutes,
            threshold,
            check_interval,
            symbols_snapshot,
            notification_snapshot,
        )
