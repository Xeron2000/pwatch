from typing import List

from pwatch.utils.send_notifications import send_notifications


def test_send_notifications_with_chat_id(monkeypatch):
    sent: List[tuple] = []

    def fake_send_message(message, token, chat_id):
        sent.append(("msg", chat_id, message))
        return True

    monkeypatch.setattr(
        "pwatch.utils.send_notifications.send_telegram_message", fake_send_message
    )

    result = send_notifications(
        "Hello",
        ["telegram"],
        {"token": "dummy-token", "chatId": "123456"},
    )

    assert sent == [("msg", "123456", "Hello")]
    assert result == {"success": True, "reason": "sent", "retryable": False}


def test_send_notifications_with_photo(monkeypatch):
    sent: List[tuple] = []

    def fake_send_photo(caption, token, chat_id, image_bytes):
        sent.append((chat_id, image_bytes))
        return True

    monkeypatch.setattr("pwatch.utils.send_notifications.send_telegram_photo", fake_send_photo)

    result = send_notifications(
        "Hello",
        ["telegram"],
        {"token": "dummy-token", "chatId": "123456"},
        image_bytes=b"bytes",
        image_caption="caption",
    )

    assert sent == [("123456", b"bytes")]
    assert result == {"success": True, "reason": "sent", "retryable": False}


def test_send_notifications_missing_chat_id(monkeypatch):
    sent: List[tuple] = []

    def fake_send_message(message, token, chat_id):
        sent.append(("msg", chat_id, message))
        return True

    monkeypatch.setattr(
        "pwatch.utils.send_notifications.send_telegram_message", fake_send_message
    )

    result = send_notifications(
        "Hello",
        ["telegram"],
        {"token": "dummy-token"},
    )

    assert sent == []
    assert result == {
        "success": False,
        "reason": "missing_chat_id",
        "retryable": False,
    }


def test_send_notifications_missing_token(monkeypatch):
    sent: List[tuple] = []

    def fake_send_message(message, token, chat_id):
        sent.append(("msg", chat_id, message))
        return True

    monkeypatch.setattr(
        "pwatch.utils.send_notifications.send_telegram_message", fake_send_message
    )

    result = send_notifications(
        "Hello",
        ["telegram"],
        {"chatId": "123456"},
    )

    assert sent == []
    assert result == {
        "success": False,
        "reason": "missing_token",
        "retryable": False,
    }


def test_send_notifications_telegram_transport_error_is_retryable(monkeypatch):
    def fake_send_message(message, token, chat_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "pwatch.utils.send_notifications.send_telegram_message", fake_send_message
    )

    result = send_notifications(
        "Hello",
        ["telegram"],
        {"token": "dummy-token", "chatId": "123456"},
    )

    assert result == {
        "success": False,
        "reason": "telegram_send_exception",
        "retryable": True,
    }


def test_send_notifications_unsupported_channel(monkeypatch):
    result = send_notifications(
        "Hello",
        ["email"],
        {"token": "dummy-token", "chatId": "123456"},
    )

    assert result == {
        "success": False,
        "reason": "unsupported_channel",
        "retryable": False,
    }
