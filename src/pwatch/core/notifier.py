# core/notifier.py

import logging
from typing import Any, Dict, Optional

from pwatch.utils.send_notifications import send_notifications


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
        image_bytes: Optional[bytes] = None,
        image_caption: Optional[str] = None,
        chart_metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send notification to configured channels.

        Returns:
            True if at least one notification was sent successfully, False otherwise.
        """
        if not message or not message.strip():
            return False

        try:
            return send_notifications(
                message,
                self.notification_channels,
                self.telegram_config,
                image_bytes=image_bytes,
                image_caption=image_caption,
            )
        except Exception as exc:
            # Log the error but don't raise it
            logging.error("Error sending notification: %s", exc)
            return False
