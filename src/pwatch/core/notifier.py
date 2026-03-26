# core/notifier.py

import logging
from typing import Any, Dict

from pwatch.utils.send_notifications import send_notifications


def _result(success: bool, reason: str, retryable: bool) -> Dict[str, Any]:
    return {"success": success, "reason": reason, "retryable": retryable}


class Notifier:
    def __init__(self, config):
        self.notification_channels = config.get("notificationChannels", [])
        self.telegram_config = config.get("telegram", {})

    def update_config(self, config) -> None:
        """Refresh notifier settings after configuration hot reload."""
        self.notification_channels = config.get("notificationChannels", [])
        self.telegram_config = config.get("telegram", {})

    def send(
        self,
        message: str,
    ) -> Dict[str, Any]:
        """Send notification to configured channels and return a structured result."""
        if not message or not str(message).strip():
            return _result(False, "empty_message", False)

        try:
            return send_notifications(
                message,
                self.notification_channels,
                self.telegram_config,
            )
        except Exception as exc:
            logging.error("Error sending notification: %s", exc)
            return _result(False, "notifier_exception", True)
