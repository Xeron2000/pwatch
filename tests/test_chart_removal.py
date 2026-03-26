from unittest.mock import patch

from pwatch.core.notifier import Notifier
from pwatch.utils.send_notifications import send_notifications


def test_notifier_send_only_passes_text_and_config(sample_config):
    expected = {"success": True, "reason": "sent", "retryable": False}

    with patch("pwatch.core.notifier.send_notifications", return_value=expected) as mock_send_notifications:
        notifier = Notifier(sample_config)
        result = notifier.send("Test message")

    assert result == expected
    mock_send_notifications.assert_called_once_with(
        "Test message",
        ["telegram"],
        sample_config.get("telegram", {}),
    )


def test_send_notifications_only_uses_text_transport(monkeypatch):
    sent = []

    def fake_send_message(message, token, chat_id):
        sent.append((message, token, chat_id))
        return True

    monkeypatch.setattr(
        "pwatch.utils.send_notifications.send_telegram_message", fake_send_message
    )

    result = send_notifications(
        "Hello",
        ["telegram"],
        {"token": "dummy-token", "chatId": "123456"},
    )

    assert sent == [("Hello", "dummy-token", "123456")]
    assert result == {"success": True, "reason": "sent", "retryable": False}
