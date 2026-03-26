import logging
import sys
from logging.handlers import RotatingFileHandler

from pwatch.paths import get_log_path


def setup_logging(log_level="INFO", console: bool = True):
    """Configure application logging."""
    log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = RotatingFileHandler(
        str(get_log_path()),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setFormatter(log_formatter)

    logger = logging.getLogger()
    if logger.hasHandlers():
        return
    logger.setLevel(log_level.upper())
    logger.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(log_formatter)
        logger.addHandler(stream_handler)

    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)