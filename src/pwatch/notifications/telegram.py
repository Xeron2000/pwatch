import logging
import time
from typing import Callable
import requests

_TIMEOUT = 30  # seconds

_MAX_RETRIES = 3
_RETRY_DELAY = 2.0  # seconds
_RATE_LIMIT_DELAY = 10.0  # seconds for 429 responses


def _mask_token(token: str) -> str:
    """Mask sensitive token for logging."""
    if not token or len(token) < 10:
        return "***"
    return f"{token[:6]}...{token[-4:]}"


def _retry_with_backoff(func: Callable, max_retries: int = _MAX_RETRIES, base_delay: float = _RETRY_DELAY):
    """Decorator for retry with exponential backoff."""
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except requests.RequestException as e:
                last_exception = e
                if attempt == max_retries:
                    logging.error(f"Retry attempts exhausted for {func.__name__}")
                    raise
                
                # Check for rate limit (429)
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code == 429:
                        retry_after = float(e.response.headers.get('Retry-After', _RATE_LIMIT_DELAY))
                        logging.warning(f"Rate limited, waiting {retry_after}s before retry")
                        time.sleep(retry_after)
                        continue
                
                # Exponential backoff
                delay = base_delay * (2 ** attempt)
                logging.warning(f"Attempt {attempt + 1}/{max_retries} failed, retrying in {delay}s: {e}")
                time.sleep(delay)
        raise last_exception
    return wrapper

def _send_message_internal(message, telegram_token, chat_id):
    """Internal function to send message."""
    masked_token = _mask_token(telegram_token)
    logging.debug(f"Sending message to chat {chat_id} (token: {masked_token})")
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    response = requests.post(url, data=data, timeout=_TIMEOUT)
    if response.status_code != 200:
        logging.error(f"Telegram API error: HTTP {response.status_code} (token: {masked_token})")
        exc = requests.RequestException(f"HTTP {response.status_code}")
        exc.response = response
        raise exc
    return response


@_retry_with_backoff
def send_telegram_message(message, telegram_token, chat_id):
    if not telegram_token or not chat_id:
        logging.warning("Telegram token or chat ID is missing.")
        return False
    try:
        _send_message_internal(message, telegram_token, chat_id)
        logging.info("Message sent to Telegram successfully")
        return True
    except Exception as e:
        logging.error("Error sending Telegram message after retries: %s", e)
        return False


def _send_photo_internal(caption, telegram_token, chat_id, image_bytes):
    """Internal function to send photo."""
    masked_token = _mask_token(telegram_token)
    logging.debug(f"Sending photo to chat {chat_id} (token: {masked_token})")
    url = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
    data = {"chat_id": chat_id, "caption": caption or "", "parse_mode": "Markdown"}
    files = {"photo": ("chart.png", image_bytes, "image/png")}
    response = requests.post(url, data=data, files=files, timeout=_TIMEOUT)
    if response.status_code != 200:
        logging.error(f"Telegram API error: HTTP {response.status_code} (token: {masked_token})")
        exc = requests.RequestException(f"HTTP {response.status_code}")
        exc.response = response
        raise exc
    return response


@_retry_with_backoff
def send_telegram_photo(caption, telegram_token, chat_id, image_bytes):
    """Send a photo with optional caption to a Telegram chat."""
    if not telegram_token or not chat_id:
        logging.warning("Telegram token or chat ID is missing.")
        return False
    try:
        _send_photo_internal(caption, telegram_token, chat_id, image_bytes)
        logging.info("Photo sent to Telegram successfully")
        return True
    except Exception as e:
        logging.error("Error sending Telegram photo after retries: %s", e)
        return False
