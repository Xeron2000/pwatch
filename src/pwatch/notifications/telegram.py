import requests


def send_telegram_message(message, telegram_token, chat_id):
    if not telegram_token or not chat_id:
        print("Telegram token or chat ID is missing.")
        return False

    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("Message sent to telegram successfully!")
            return True
        else:
            print(f"Failed to send message: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"Error while sending Telegram message: {e}")
        return False


def send_telegram_photo(caption, telegram_token, chat_id, image_bytes):
    """
    Send a photo with optional caption to a Telegram chat.

    Args:
        caption (str): Caption text (supports Markdown)
        telegram_token (str): Bot token
        chat_id (str): Target chat id
        image_bytes (bytes): PNG or JPEG bytes

    Returns:
        bool: True on success
    """
    if not telegram_token or not chat_id:
        print("Telegram token or chat ID is missing.")
        return False

    url = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
    data = {"chat_id": chat_id, "caption": caption or "", "parse_mode": "Markdown"}
    files = {"photo": ("chart.png", image_bytes, "image/png")}

    try:
        response = requests.post(url, data=data, files=files)
        if response.status_code == 200:
            print("Photo sent to telegram successfully!")
            return True
        else:
            print(f"Failed to send photo: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"Error while sending Telegram photo: {e}")
        return False
