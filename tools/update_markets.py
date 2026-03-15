import argparse
import logging
import sys
from pathlib import Path

import yaml

# Ensure src directory is on the import path when run directly
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
for candidate in (SRC_DIR, ROOT_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from pwatch.paths import get_config_path
from pwatch.utils.setup_logging import setup_logging
from pwatch.utils.supported_markets import list_cached_exchanges, refresh_supported_markets

DEFAULT_EXCHANGES = ["okx", "binance", "bybit"]


def load_config():
    """Loads the YAML configuration file."""
    config_path = get_config_path()
    try:
        with config_path.open("r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("Config not found: %s", config_path)
        return None


def update_supported_markets(exchange_names):
    """Fetches markets for a list of exchanges and saves them to a JSON file."""
    refreshed = refresh_supported_markets(exchange_names)
    if refreshed:
        logging.info(
            "Refresh completed with %s exchanges updated: %s",
            len(refreshed),
            ", ".join(sorted(refreshed)),
        )
    else:
        logging.warning("Supported markets were not updated; no exchanges produced data.")


def main():
    """Main function to run the script."""
    setup_logging()
    parser = argparse.ArgumentParser(description="Update supported markets for exchanges.")
    parser.add_argument(
        "--exchanges",
        nargs="+",
        help="A list of exchange names to update. If not provided, all exchanges from config will be used.",
    )
    args = parser.parse_args()

    exchange_names = list(args.exchanges or [])

    if not exchange_names:
        seeds = list(DEFAULT_EXCHANGES)

        config = load_config()
        if config:
            config_exchanges = config.get("exchanges")
            if isinstance(config_exchanges, (list, tuple)):
                seeds.extend(str(name) for name in config_exchanges if name)
            primary = config.get("exchange")
            if primary:
                seeds.append(str(primary))

        cached = list_cached_exchanges()
        seeds.extend(cached)

        exchange_names = seeds
        logging.info(
            "Using default exchange set (merged with config/cached): %s",
            ", ".join(dict.fromkeys(seeds)),
        )

    exchange_names = list(dict.fromkeys(name for name in exchange_names if name))
    if not exchange_names:
        logging.warning(
            "No exchanges specified. Provide --exchanges, define them in config, or ensure cached markets exist."
        )
        return

    logging.info("Updating supported markets for: %s", ", ".join(exchange_names))

    update_supported_markets(exchange_names)

    logging.info("Market update completed")


if __name__ == "__main__":
    main()
