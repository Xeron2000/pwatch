import logging
import os
from typing import Any, Dict, List

from pwatch.notifications.telegram import send_telegram_message, send_telegram_photo


def _resolve_telegram_targets(telegram_config: dict) -> List[str]:
    """Resolve Telegram recipients from config."""
    chat_ids: List[str] = []

    chat_id = telegram_config.get("chatId")
    if chat_id:
        chat_ids.append(str(chat_id))

    return chat_ids


def _result(success: bool, reason: str, retryable: bool) -> Dict[str, Any]:
    return {"success": success, "reason": reason, "retryable": retryable}


def send_notifications(
    message,
    notification_channels,
    telegram_config,
    image_bytes=None,
    image_caption=None,
 ) -> Dict[str, Any]:
    """Send notifications to configured channels and return a structured result."""
    if not notification_channels:
        return _result(False, "no_channels", False)

    last_failure = _result(False, "no_supported_channels", False)

    for channel in notification_channels:
        try:
            if channel == "telegram":
                token = os.environ.get("PWATCH_TELEGRAM_TOKEN") or telegram_config.get("token")
                if not token:
                    logging.warning("Telegram notifications enabled but token missing")
                    last_failure = _result(False, "missing_token", False)
                    continue

                chat_ids = _resolve_telegram_targets(telegram_config)
                if not chat_ids:
                    logging.warning("Telegram notifications enabled but no chatId configured")
                    last_failure = _result(False, "missing_chat_id", False)
                    continue

                for chat_id in chat_ids:
                    try:
                        delivered = False
                        if image_bytes is not None:
                            delivered = send_telegram_photo(
                                image_caption or "",
                                token,
                                chat_id,
                                image_bytes,
                            )
                        else:
                            delivered = send_telegram_message(
                                message,
                                token,
                                chat_id,
                            )

                        if delivered:
                            return _result(True, "sent", False)
                        last_failure = _result(False, "telegram_send_failed", True)
                    except Exception as exc:
                        logging.error(
                            "Failed to send Telegram notification to %s: %s",
                            chat_id,
                            exc,
                        )
                        last_failure = _result(False, "telegram_send_exception", True)
            else:
                logging.warning("Unsupported notification channel: %s", channel)
                last_failure = _result(False, "unsupported_channel", False)
        except Exception as exc:
            logging.error("Failed to send message via %s: %s", channel, exc)
            last_failure = _result(False, f"{channel}_send_exception", True)

    return last_failure
