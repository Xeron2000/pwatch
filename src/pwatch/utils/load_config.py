import logging
from pathlib import Path

import yaml

from pwatch.paths import get_config_path, get_symbols_path


def load_config(configPath=None):
    """
    Loads the configuration from a YAML file.

    Args:
        configPath (str): The path to the configuration file.

    Returns:
        dict: The configuration as a dictionary.

    Raises:
        ValueError: If the configuration is missing any of the required keys.
        Exception: If there is an error loading the configuration.

    Required keys in the configuration file:
        - 'exchange': The name of the exchange to connect to.
        - 'defaultTimeframe': The default timeframe (K-line aggregation window).
        - 'checkInterval': Optional monitoring frequency (defaults to timeframe when omitted).
        - 'defaultThreshold': The default price change threshold.
        - 'notificationChannels': The channels for receiving notifications.
    Optional keys:
        - 'symbolsFilePath': Path to the symbols file. Defaults to "config/symbols.txt".
    """
    path = Path(configPath) if configPath else get_config_path()

    try:
        with open(str(path), "r") as file:
            config = yaml.safe_load(file)

        # Handle empty file case
        if config is None:
            config = {}

        required_keys = [
            "exchange",
            "defaultTimeframe",
            "defaultThreshold",
            "notificationChannels",
            "notificationTimezone",
        ]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")

        if "notificationTimezone" not in config or not config["notificationTimezone"]:
            config["notificationTimezone"] = "Asia/Shanghai"  # Default timezone

        if "symbolsFilePath" not in config or not config["symbolsFilePath"]:
            config["symbolsFilePath"] = str(get_symbols_path())

        # Monitoring falls back to timeframe when no explicit interval is provided
        if "checkInterval" not in config or not config["checkInterval"]:
            config["checkInterval"] = config.get("defaultTimeframe", "5m")

        return config
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        raise
