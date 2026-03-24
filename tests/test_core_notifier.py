"""Tests for core/notifier.py - Notification system."""

from unittest.mock import patch

from pwatch.core.notifier import Notifier


class TestNotifier:
    """Test cases for Notifier class."""

    def test_init_basic(self, sample_config):
        notifier = Notifier(sample_config)

        assert notifier.notification_channels == ["telegram"]
        assert notifier.telegram_config == sample_config.get("telegram", {})

    def test_init_with_empty_config(self):
        notifier = Notifier({})

        assert notifier.notification_channels == []
        assert notifier.telegram_config == {}

    def test_send_with_message_only_returns_structured_result(self, sample_config):
        expected = {"success": True, "reason": "sent", "retryable": False}

        with patch(
            "pwatch.core.notifier.send_notifications", return_value=expected
        ) as mock_send_notifications:
            notifier = Notifier(sample_config)
            result = notifier.send("Test message")

            assert result == expected
            mock_send_notifications.assert_called_once_with(
                "Test message",
                ["telegram"],
                sample_config.get("telegram", {}),
                image_bytes=None,
                image_caption=None,
            )

    def test_send_with_image(self, sample_config):
        expected = {"success": True, "reason": "sent", "retryable": False}

        with patch(
            "pwatch.core.notifier.send_notifications", return_value=expected
        ) as mock_send_notifications:
            notifier = Notifier(sample_config)
            image_bytes = b"fake_image_data"
            image_caption = "Test caption"

            result = notifier.send(
                "Test message with image",
                image_bytes=image_bytes,
                image_caption=image_caption,
            )

            assert result == expected
            mock_send_notifications.assert_called_once_with(
                "Test message with image",
                ["telegram"],
                sample_config.get("telegram", {}),
                image_bytes=image_bytes,
                image_caption=image_caption,
            )

    def test_send_ignores_empty_messages_with_structured_failure(self, sample_config):
        with patch("pwatch.core.notifier.send_notifications") as mock_send_notifications:
            notifier = Notifier(sample_config)

            assert notifier.send("") == {
                "success": False,
                "reason": "empty_message",
                "retryable": False,
            }
            assert notifier.send(None) == {
                "success": False,
                "reason": "empty_message",
                "retryable": False,
            }
            assert notifier.send("   ") == {
                "success": False,
                "reason": "empty_message",
                "retryable": False,
            }

            mock_send_notifications.assert_not_called()

    def test_send_handles_exception_with_structured_failure(self, sample_config):
        with patch(
            "pwatch.core.notifier.send_notifications", side_effect=Exception("Network error")
        ):
            notifier = Notifier(sample_config)

            result = notifier.send("Test message")

            assert result == {
                "success": False,
                "reason": "notifier_exception",
                "retryable": True,
            }

    def test_update_config_refreshes_channels_and_telegram_settings(self, sample_config):
        notifier = Notifier(sample_config)
        notifier.update_config({
            "notificationChannels": ["telegram", "unknown"],
            "telegram": {"token": "t", "chatId": "1"},
        })

        assert notifier.notification_channels == ["telegram", "unknown"]
        assert notifier.telegram_config == {"token": "t", "chatId": "1"}
