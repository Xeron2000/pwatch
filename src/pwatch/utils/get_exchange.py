from pwatch.exchanges import BinanceExchange, BybitExchange, OkxExchange


def get_exchange(exchange_name):
    """
    Create an instance of an Exchange class based on the name provided.

    Args:
        exchange_name (str): The name of the exchange to create an instance of.

    Returns:
        Exchange: An instance of an Exchange class.

    Raises:
        ValueError: If the provided exchange name is not supported.
        AttributeError: If the provided exchange name is None.
    """
    if exchange_name is None:
        raise ValueError("Exchange None not supported.")

    # Strip whitespace and check if empty
    exchange_name = exchange_name.strip()
    if not exchange_name:
        raise ValueError("Exchange   not supported.")

    if exchange_name.lower() == "okx":
        return OkxExchange()
    elif exchange_name.lower() == "binance":
        return BinanceExchange()
    elif exchange_name.lower() == "bybit":
        return BybitExchange()
    else:
        raise ValueError(f"Exchange {exchange_name} not supported.")
