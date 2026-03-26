import asyncio
import logging
import traceback
from typing import Optional

from pwatch.core.sentry import PriceSentry
from pwatch.notifications.telegram_bot_service import TelegramBotService
from pwatch.utils.setup_logging import setup_logging


async def main():
    bot_service: Optional[TelegramBotService] = None
    try:
        sentry = PriceSentry()
        log_level = sentry.config.get("logLevel")
        if log_level:
            setup_logging(log_level, console=False)
        else:
            setup_logging(console=False)

        telegram_cfg = sentry.config.get("telegram", {}) if sentry.config else {}
        bot_service = TelegramBotService(telegram_cfg.get("token"))
        await bot_service.start()

        await sentry.run()
    except Exception as e:
        logging.error(f"An error occurred in main: {e}")
        traceback.print_exc()
    finally:
        if bot_service is not None:
            try:
                await bot_service.stop()
            except Exception as exc:  # defensive cleanup
                logging.warning(f"Failed to stop Telegram bot service cleanly: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
