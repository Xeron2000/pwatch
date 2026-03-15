def parse_timeframe(timeframe):
    """
    Converts a timeframe string into minutes.

    The input string should represent a timeframe, ending with 'm', 'h', or 'd',
    indicating minutes, hours, and days respectively. The numeric part of the string
    is parsed and converted to minutes.

    Args:
        timeframe (str): A string representing a timeframe, e.g., '15m', '2h', '1d'.

    Returns:
        int: The equivalent number of minutes.

    Raises:
        ValueError: If the timeframe format is invalid or not recognized.
    """

    # Check for whitespace
    if " " in timeframe or "\t" in timeframe or "\n" in timeframe:
        raise ValueError("Invalid timeframe format. Use 'Xm', 'Xh', or 'Xd'.")

    if timeframe.endswith("m"):
        value = float(timeframe[:-1])
        if value < 0:
            raise ValueError("Invalid timeframe format. Use 'Xm', 'Xh', or 'Xd'.")
        return 0 if value <= 0.05 else int(value)  # Values <= 0.05m return 0
    elif timeframe.endswith("h"):
        value = float(timeframe[:-1])
        if value < 0:
            raise ValueError("Invalid timeframe format. Use 'Xm', 'Xh', or 'Xd'.")
        return 0 if value <= 0.005 else int(value * 60)  # Values <= 0.005h return 0
    elif timeframe.endswith("d"):
        value = float(timeframe[:-1])
        if value < 0:
            raise ValueError("Invalid timeframe format. Use 'Xm', 'Xh', or 'Xd'.")
        return 0 if value <= 0.001 else int(value * 1440)  # Values <= 0.001d return 0
    else:
        raise ValueError("Invalid timeframe format. Use 'Xm', 'Xh', or 'Xd'.")
