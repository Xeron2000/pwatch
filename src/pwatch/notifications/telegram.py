import logging

import requests

_TIMEOUT = 30  # seconds


def send_telegram_message(message, telegram_token, chat_id):
    if not telegram_token or not chat_id:
        logging.warning("Telegram token or chat ID is missing.")
        return False

    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        response = requests.post(url, data=data, timeout=_TIMEOUT)
        if response.status_code == 200:
            logging.info("Message sent to Telegram successfully")
            return True
        else:
            logging.warning("Failed to send Telegram message: HTTP %d", response.status_code)
            return False
    except requests.RequestException as e:
        logging.error("Error sending Telegram message: %s", e)
        return False


def send_telegram_photo(caption, telegram_token, chat_id, image_bytes):
    """Send a photo with optional caption to a Telegram chat."""
    if not telegram_token or not chat_id:
        logging.warning("Telegram token or chat ID is missing.")
        return False

    url = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
    data = {"chat_id": chat_id, "caption": caption or "", "parse_mode": "Markdown"}
    files = {"photo": ("chart.png", image_bytes, "image/png")}

    try:
        response = requests.post(url, data=data, files=files, timeout=_TIMEOUT)
        if response.status_code == 200:
            logging.info("Photo sent to Telegram successfully")
            return True
        else:
            logging.warning("Failed to send Telegram photo: HTTP %d", response.status_code)
            return False
    except requests.RequestException as e:
        logging.error("Error sending Telegram photo: %s", e)
        return False
