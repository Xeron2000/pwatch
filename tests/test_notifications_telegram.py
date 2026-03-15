"""
Tests for notifications/telegram.py - Telegram notification service.
"""

from unittest.mock import Mock, patch

import requests

from pwatch.notifications.telegram import send_telegram_message, send_telegram_photo


class TestTelegramNotification:
    """Test cases for Telegram notification functions."""

    def test_send_telegram_message_success(self):
        """Test successful Telegram message sending."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            result = send_telegram_message("Test message", "test_token", "test_chat_id")

            assert result is True
            mock_post.assert_called_once()

            # Verify the call parameters
            call_args = mock_post.call_args
            assert (
                "https://api.telegram.org/bottest_token/sendMessage" in call_args[0][0]
            )
            assert call_args[1]["data"]["chat_id"] == "test_chat_id"
            assert call_args[1]["data"]["text"] == "Test message"
            assert call_args[1]["data"]["parse_mode"] == "Markdown"

    def test_send_telegram_message_missing_token(self):
        """Test Telegram message sending with missing token."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            with patch("builtins.print") as mock_print:
                result = send_telegram_message(
                    "Test message",
                    "",  # Empty token
                    "test_chat_id",
                )

                assert result is False
                mock_post.assert_not_called()
                mock_print.assert_called_with("Telegram token or chat ID is missing.")

    def test_send_telegram_message_missing_chat_id(self):
        """Test Telegram message sending with missing chat ID."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            with patch("builtins.print") as mock_print:
                result = send_telegram_message(
                    "Test message",
                    "test_token",
                    "",  # Empty chat ID
                )

                assert result is False
                mock_post.assert_not_called()
                mock_print.assert_called_with("Telegram token or chat ID is missing.")

    def test_send_telegram_message_api_error(self):
        """Test Telegram message sending with API error."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            with patch("builtins.print") as mock_print:
                # Mock error response
                mock_response = Mock()
                mock_response.status_code = 400
                mock_response.text = "Bad Request"
                mock_post.return_value = mock_response

                result = send_telegram_message(
                    "Test message", "test_token", "test_chat_id"
                )

                assert result is False
                mock_print.assert_called_with("Failed to send message: Bad Request")

    def test_send_telegram_message_network_error(self):
        """Test Telegram message sending with network error."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            with patch("builtins.print") as mock_print:
                # Mock network error
                mock_post.side_effect = requests.RequestException("Network error")

                result = send_telegram_message(
                    "Test message", "test_token", "test_chat_id"
                )

                assert result is False
                mock_print.assert_called_with(
                    "Error while sending Telegram message: Network error"
                )

    def test_send_telegram_photo_success(self):
        """Test successful Telegram photo sending."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            image_bytes = b"fake_image_data"
            result = send_telegram_photo(
                "Test caption", "test_token", "test_chat_id", image_bytes
            )

            assert result is True
            mock_post.assert_called_once()

            # Verify the call parameters
            call_args = mock_post.call_args
            assert "https://api.telegram.org/bottest_token/sendPhoto" in call_args[0][0]
            assert call_args[1]["data"]["chat_id"] == "test_chat_id"
            assert call_args[1]["data"]["caption"] == "Test caption"
            assert call_args[1]["data"]["parse_mode"] == "Markdown"
            assert "photo" in call_args[1]["files"]
            assert call_args[1]["files"]["photo"][1] == image_bytes

    def test_send_telegram_photo_missing_token(self):
        """Test Telegram photo sending with missing token."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            with patch("builtins.print") as mock_print:
                image_bytes = b"fake_image_data"
                result = send_telegram_photo(
                    "Test caption",
                    "",  # Empty token
                    "test_chat_id",
                    image_bytes,
                )

                assert result is False
                mock_post.assert_not_called()
                mock_print.assert_called_with("Telegram token or chat ID is missing.")

    def test_send_telegram_photo_missing_chat_id(self):
        """Test Telegram photo sending with missing chat ID."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            with patch("builtins.print") as mock_print:
                image_bytes = b"fake_image_data"
                result = send_telegram_photo(
                    "Test caption",
                    "test_token",
                    "",  # Empty chat ID
                    image_bytes,
                )

                assert result is False
                mock_post.assert_not_called()
                mock_print.assert_called_with("Telegram token or chat ID is missing.")

    def test_send_telegram_photo_empty_caption(self):
        """Test Telegram photo sending with empty caption."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            image_bytes = b"fake_image_data"
            result = send_telegram_photo(
                "",  # Empty caption
                "test_token",
                "test_chat_id",
                image_bytes,
            )

            assert result is True

            # Verify empty caption is handled correctly
            call_args = mock_post.call_args
            assert call_args[1]["data"]["caption"] == ""

    def test_send_telegram_photo_api_error(self):
        """Test Telegram photo sending with API error."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            with patch("builtins.print") as mock_print:
                # Mock error response
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
                mock_post.return_value = mock_response

                image_bytes = b"fake_image_data"
                result = send_telegram_photo(
                    "Test caption", "test_token", "test_chat_id", image_bytes
                )

                assert result is False
                mock_print.assert_called_with(
                    "Failed to send photo: Internal Server Error"
                )

    def test_send_telegram_photo_network_error(self):
        """Test Telegram photo sending with network error."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            with patch("builtins.print") as mock_print:
                # Mock network error
                mock_post.side_effect = requests.RequestException("Network error")

                image_bytes = b"fake_image_data"
                result = send_telegram_photo(
                    "Test caption", "test_token", "test_chat_id", image_bytes
                )

                assert result is False
                mock_print.assert_called_with(
                    "Error while sending Telegram photo: Network error"
                )

    def test_send_telegram_photo_file_upload(self):
        """Test Telegram photo file upload parameters."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            image_bytes = b"fake_image_data"
            send_telegram_photo(
                "Test caption", "test_token", "test_chat_id", image_bytes
            )

            # Verify file upload parameters
            call_args = mock_post.call_args
            files = call_args[1]["files"]
            assert "photo" in files
            assert files["photo"][0] == "chart.png"
            assert files["photo"][1] == image_bytes
            assert files["photo"][2] == "image/png"

    def test_send_telegram_message_special_characters(self):
        """Test Telegram message sending with special characters."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            # Mock successful response
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
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            long_message = "A" * 1000  # 1000 character message
            result = send_telegram_message(long_message, "test_token", "test_chat_id")

            assert result is True
            call_args = mock_post.call_args
            assert call_args[1]["data"]["text"] == long_message

    def test_send_telegram_photo_large_image(self):
        """Test Telegram photo sending with large image data."""
        with patch("pwatch.notifications.telegram.requests.post") as mock_post:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            large_image = b"x" * (1024 * 1024)  # 1MB image data
            result = send_telegram_photo(
                "Large image", "test_token", "test_chat_id", large_image
            )

            assert result is True
            call_args = mock_post.call_args
            assert call_args[1]["files"]["photo"][1] == large_image
