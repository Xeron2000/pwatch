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

    def test_send_with_message_only(self, sample_config):
        with patch("pwatch.core.notifier.send_notifications") as mock_send_notifications:
            notifier = Notifier(sample_config)
            notifier.send("Test message")

            mock_send_notifications.assert_called_once_with(
                "Test message",
                ["telegram"],
                sample_config.get("telegram", {}),
                image_bytes=None,
                image_caption=None,
            )

    def test_send_with_image(self, sample_config):
        with patch("pwatch.core.notifier.send_notifications") as mock_send_notifications:
            notifier = Notifier(sample_config)
            image_bytes = b"fake_image_data"
            image_caption = "Test caption"

            notifier.send(
                "Test message with image",
                image_bytes=image_bytes,
                image_caption=image_caption,
            )

            mock_send_notifications.assert_called_once_with(
                "Test message with image",
                ["telegram"],
                sample_config.get("telegram", {}),
                image_bytes=image_bytes,
                image_caption=image_caption,
            )

    def test_send_ignores_empty_messages(self, sample_config):
        with patch("pwatch.core.notifier.send_notifications") as mock_send_notifications:
            notifier = Notifier(sample_config)

            notifier.send("")
            notifier.send(None)
            notifier.send("   ")

            mock_send_notifications.assert_not_called()

    def test_send_handles_exception(self, sample_config):
        with patch(
            "pwatch.core.notifier.send_notifications", side_effect=Exception("Network error")
        ):
            notifier = Notifier(sample_config)

            result = notifier.send("Test message")
            # Should not raise despite underlying exception
            assert result is False

    def test_send_returns_true_on_success(self, sample_config):
        """Verify send returns True when notification is sent successfully."""
        with patch("pwatch.core.notifier.send_notifications", return_value=True):
            notifier = Notifier(sample_config)
            result = notifier.send("Test message")
            assert result is True

    def test_send_returns_false_on_empty_message(self, sample_config):
        """Verify send returns False for empty messages."""
        notifier = Notifier(sample_config)

        assert notifier.send("") is False
        assert notifier.send("   ") is False

    def test_send_returns_false_on_all_channels_fail(self, sample_config):
        """Verify send returns False when all channels fail."""
        with patch("pwatch.core.notifier.send_notifications", return_value=False):
            notifier = Notifier(sample_config)
            result = notifier.send("Test message")
            assert result is False

    def test_send_returns_false_on_exception(self, sample_config):
        """Verify send returns False when exception occurs."""
        with patch(
            "pwatch.core.notifier.send_notifications", side_effect=Exception("Network error")
        ):
            notifier = Notifier(sample_config)
            result = notifier.send("Test message")
            assert result is False
