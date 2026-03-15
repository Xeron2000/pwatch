from datetime import datetime
from typing import Iterable, Optional

import pytz


async def monitor_top_movers(
    minutes,
    symbols,
    threshold,
    exchange,
    config,
    allowed_symbols: Optional[Iterable[str]] = None,
    cooldown_manager=None,
):
    """
    Retrieves the top movers for the given symbols on the given exchange
    over the given time period asynchronously.

    Args:
        minutes (int): The number of minutes in the past to monitor.
        symbols (list): A list of symbol strings for which to fetch prices.
        threshold (float): The minimum percentage price change required to be a
            "top mover".
        exchange (Exchange): An instance of the Exchange class which implements the
            'getPriceMinutesAgo' and 'getCurrentPrices' methods.
        config (dict): Configuration dictionary loaded from config.yaml
        allowed_symbols (Iterable[str] | None): Optional subset of symbols that should
            trigger notifications. When provided, only price changes for these symbols
            will be reported.
        cooldown_manager (NotificationCooldownManager | None): Optional manager for
            notification cooldowns.

    Returns:
        tuple[str, list[tuple[str, float, str]]] | None: (message, top_movers_sorted) where
            top_movers_sorted is a list of (symbol, percent_change, priority).
            Returns None if no movers meet the threshold or all are in cooldown.
    """
    if exchange is None or not all(
        hasattr(exchange, method) for method in ["get_price_minutes_ago", "get_current_prices"]
    ):
        raise ValueError("Exchange must implement 'get_price_minutes_ago' and 'get_current_prices' methods")

    initial_prices = exchange.get_price_minutes_ago(symbols, minutes)

    updated_prices = await exchange.get_current_prices(symbols)

    price_changes = {
        symbol: ((updated_prices[symbol] - initial_prices[symbol]) / initial_prices[symbol]) * 100
        for symbol in initial_prices
        if symbol in updated_prices
        if abs((updated_prices[symbol] - initial_prices[symbol]) / initial_prices[symbol]) * 100 > threshold
    }

    if allowed_symbols is not None:
        allowed_set = {symbol.strip() for symbol in allowed_symbols if isinstance(symbol, str)}
        price_changes = {symbol: change for symbol, change in price_changes.items() if symbol in allowed_set}
    else:
        allowed_set = None

    if not price_changes:
        return None

    # Priority classification
    priority_thresholds = config.get("priorityThresholds", {"high": 5.0, "medium": 2.0})
    high_threshold = priority_thresholds.get("high", 5.0)
    medium_threshold = priority_thresholds.get("medium", 2.0)
    bypass_cooldown_config = config.get("highPriorityBypassCooldown", True)

    movers_with_priority = []
    for symbol, change in price_changes.items():
        abs_change = abs(change)
        if abs_change >= high_threshold:
            priority = "HIGH"
            priority_val = 3
        elif abs_change >= medium_threshold:
            priority = "MEDIUM"
            priority_val = 2
        else:
            priority = "LOW"
            priority_val = 1

        # Check cooldown
        if cooldown_manager:
            bypass = priority == "HIGH" and bypass_cooldown_config
            if not cooldown_manager.should_notify(symbol, bypass_cooldown=bypass):
                continue
            # Note: We record the notification in PriceSentry after sending successfully
            # or we can record it here. The proposal says record_notification() should be called.
            # Record it here so we don't notify same symbol again in same loop (unlikely but safe)
            # Actually better record after successful send.

        movers_with_priority.append((symbol, change, priority, priority_val))

    if not movers_with_priority:
        return None

    # Sort by priority first (desc), then by absolute change (desc)
    top_movers_sorted = sorted(movers_with_priority, key=lambda x: (x[3], abs(x[1])), reverse=True)

    timezone_str = config.get("notificationTimezone", "Asia/Shanghai")
    message = format_movers_message(
        exchange.exchange_name,
        minutes,
        timezone_str,
        threshold,
        len(symbols),
        len(allowed_set) if allowed_set is not None else len(symbols),
        len(movers_with_priority),
        top_movers_sorted,
        initial_prices,
        updated_prices,
    )

    return message, [(m[0], m[1], m[2]) for m in top_movers_sorted]


def format_movers_message(
    exchange_name: str,
    minutes: int,
    timezone_str: str,
    threshold: float,
    monitored_count: int,
    scope_count: int,
    detected_count: int,
    top_movers: list,
    initial_prices: dict,
    updated_prices: dict,
) -> str:
    """Format the price movement alert message."""
    timezone = pytz.timezone(timezone_str)
    current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")

    header = f"**📈 {exchange_name} Price Movement Alerts ({minutes}m)**\n\n"
    time_info = f"**Time:** {current_time} ({timezone_str})\n"
    stats = (
        f"**Threshold:** {threshold}% | **Monitored:** {monitored_count} | "
        f"**Alert Scope:** {scope_count} | **Detected:** {detected_count}\n\n"
    )
    message = header + time_info + stats

    for i, mover in enumerate(top_movers[:6], 1):
        # Handle both types of mover tuples (from monitor_top_movers or filtered)
        symbol = mover[0]
        change = mover[1]
        priority = mover[2]

        price_diff = updated_prices[symbol] - initial_prices[symbol]
        arrow = "🔼" if change > 0 else "🔽"

        if priority == "HIGH":
            priority_label = "🚨 [HIGH]"
            color = "🔴" if change < 0 else "🟢"
        elif priority == "MEDIUM":
            priority_label = "⚠️ [MEDIUM]"
            color = "🟠"
        else:
            priority_label = "ℹ️ [LOW]"
            color = "🔵"

        price_range = f"(*{initial_prices[symbol]:.4f}* → *{updated_prices[symbol]:.4f}*)"
        message += (
            f"{color} **{i}. `{symbol}`** {priority_label}\n"
            f"   - **Change:** {arrow} {abs(change):.2f}%\n"
            f"   - **Diff:** {price_diff:+.4f} {price_range}\n\n"
        )

    return message
