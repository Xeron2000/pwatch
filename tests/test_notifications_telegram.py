"""
Tests for notifications/telegram.py - Telegram notification service.
"""

from unittest.mock import Mock, patch

import requests

from pwatch.notifications.telegram import send_telegram_message


class TestTelegramNotification:
    """Test cases for Telegram notification functions."""

    def test_send_telegram_message_success(self):
        """Test successful Telegram message sending."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = send_telegram_message("Test message", "test_token", "test_chat_id")

            assert result is True
            mock_post.assert_called_once()

            call_args = mock_post.call_args
            assert "https://api.telegram.org/bottest_token/sendMessage" in call_args[0][0]
            assert call_args[1]["data"]["chat_id"] == "test_chat_id"
            assert call_args[1]["data"]["text"] == "Test message"
            assert call_args[1]["data"]["parse_mode"] == "Markdown"

    def test_send_telegram_message_missing_token(self):
        """Test Telegram message sending with missing token."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            result = send_telegram_message(
                "Test message",
                "",
                "test_chat_id",
            )

            assert result is False
            mock_post.assert_not_called()

    def test_send_telegram_message_missing_chat_id(self):
        """Test Telegram message sending with missing chat ID."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            result = send_telegram_message(
                "Test message",
                "test_token",
                "",
            )

            assert result is False
            mock_post.assert_not_called()

    def test_send_telegram_message_api_error(self):
        """Test Telegram message sending with API error."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            mock_post.return_value = mock_response

            result = send_telegram_message(
                "Test message", "test_token", "test_chat_id"
            )

            assert result is False

    def test_send_telegram_message_network_error(self):
        """Test Telegram message sending with network error."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            mock_post.side_effect = requests.RequestException("Network error")

            result = send_telegram_message(
                "Test message", "test_token", "test_chat_id"
            )

            assert result is False

    def test_send_telegram_message_special_characters(self):
        """Test Telegram message sending with special characters."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            message = "Price 🚀 UP! BTC: $50,000.00"
            result = send_telegram_message(message, "test_token", "test_chat_id")

            assert result is True
            call_args = mock_post.call_args
            assert call_args[1]["data"]["text"] == message

    def test_send_telegram_message_long_text(self):
        """Test Telegram message sending with long text."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            long_message = "A" * 1000
            result = send_telegram_message(long_message, "test_token", "test_chat_id")

            assert result is True
            call_args = mock_post.call_args
            assert call_args[1]["data"]["text"] == long_message
