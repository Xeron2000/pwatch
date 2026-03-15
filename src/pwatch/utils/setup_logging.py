import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(log_level="INFO"):
    """Configures the logging for the application."""
    log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Use RotatingFileHandler
    file_handler = RotatingFileHandler("pricesentry.log", maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(log_formatter)

    # Stream handler for console output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)

    # Get root logger
    logger = logging.getLogger()
    if logger.hasHandlers():
        # Logger is already configured, do not add handlers again
        return
    logger.setLevel(log_level.upper())
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    # Suppress noisy loggers
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
