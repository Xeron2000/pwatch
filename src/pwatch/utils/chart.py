from __future__ import annotations

import io
import time
from typing import List, Optional

import matplotlib
import pytz

matplotlib.use("Agg")  # 使用非GUI后端
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from pwatch.utils.parse_timeframe import parse_timeframe


def _compute_sma(values: List[float], window: int) -> List[Optional[float]]:
    """Compute simple moving average, padding with None before first full window."""
    if window <= 1:
        return list(values)

    result: List[Optional[float]] = []
    running_sum = 0.0
    for i, value in enumerate(values):
        running_sum += value
        if i >= window:
            running_sum -= values[i - window]
        if i >= window - 1:
            result.append(running_sum / window)
        else:
            result.append(None)
    return result


def _setup_matplotlib_style(theme: str):
    """设置matplotlib样式"""
    if theme.lower() == "dark":
        plt.style.use("dark_background")
        facecolor = "#1a1a1a"  # 适中的深色背景
        edgecolor = "#404040"
        grid_color = "#404040"
        text_color = "#e0e0e0"
        # 优化的红绿K线颜色
        up_color = "#29e330"  # 亮绿色
        down_color = "#ca1a0e"  # 亮红色
        wick_color = "#ffffff"  # 白色引线
    else:
        plt.style.use("default")
        facecolor = "#ffffff"
        edgecolor = "#e0e0e0"
        grid_color = "#f0f0f0"
        text_color = "#333333"
        # 浅色主题红绿K线颜色
        up_color = "#1cd926"  # 深绿色
        down_color = "#e02323"  # 深红色
        wick_color = "#424242"  # 深灰色引线

    return {
        "facecolor": facecolor,
        "edgecolor": edgecolor,
        "grid_color": grid_color,
        "text_color": text_color,
        "up_color": up_color,
        "down_color": down_color,
        "wick_color": wick_color,
    }


def generate_candlestick_png(
    ccxt_exchange,
    symbol: str,
    timeframe: str = "1m",
    lookback_minutes: int = 60,
    theme: str = "dark",
    moving_averages: Optional[List[int]] = None,
    width: int = 800,
    height: int = 500,
    scale: int = 2,
) -> bytes:
    """
    Generate a candlestick PNG for the given symbol using ccxt OHLCV data.

    Args:
        ccxt_exchange: An instantiated ccxt exchange (e.g., base_exchange.exchange)
        symbol: Market symbol like "BTC/USDT"
        timeframe: ccxt timeframe string (e.g., "1m", "5m", "1h")
        lookback_minutes: How many minutes of history to visualize
        theme: "dark" or "light"
        moving_averages: List of window sizes for SMA lines
        width: Image width in pixels
        height: Image height in pixels
        scale: Pixel ratio multiplier for export

    Returns:
        PNG bytes
    """
    # Lazy import to avoid hard dependency when charts are disabled
    try:
        import matplotlib.pyplot as plt
        import mplfinance as mpf
        import pandas as pd
    except Exception as e:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "matplotlib, pandas, and mplfinance are required for chart generation. "
            "Install with: pip install matplotlib pandas mplfinance"
        ) from e

    if moving_averages is None:
        moving_averages = []

    try:
        tf_minutes = parse_timeframe(timeframe)
    except Exception:
        # Fallback parsing for safety
        unit = timeframe[-1]
        num = int(timeframe[:-1])
        if unit == "m":
            tf_minutes = num
        elif unit == "h":
            tf_minutes = num * 60
        elif unit == "d":
            tf_minutes = num * 1440
        else:
            tf_minutes = 1

    # Add extra bars for MAs and chart context
    extra = (max(moving_averages) if moving_averages else 0) + 5
    approx_candles = int((lookback_minutes + tf_minutes - 1) // tf_minutes)
    limit = max(20, approx_candles + extra)

    since_ms = int((time.time() - lookback_minutes * 60) * 1000)

    try:
        ohlcv = ccxt_exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)
    except Exception:
        # Retry without since if the exchange rejects it
        ohlcv = ccxt_exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

    if not ohlcv or len(ohlcv) < 5:
        raise RuntimeError(f"Not enough OHLCV data for {symbol} {timeframe}")

    # Convert to pandas DataFrame
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    # Set up matplotlib style
    style_colors = _setup_matplotlib_style(theme)

    # Create custom style for mplfinance
    mc = mpf.make_marketcolors(
        up=style_colors["up_color"],
        down=style_colors["down_color"],
        edge=style_colors["wick_color"],
        wick=style_colors["wick_color"],
        volume="in",
    )

    s = mpf.make_mpf_style(
        marketcolors=mc,
        facecolor=style_colors["facecolor"],
        edgecolor=style_colors["edgecolor"],
        gridcolor=style_colors["grid_color"],
        figcolor=style_colors["facecolor"],
        y_on_right=False,
        gridstyle="--",  # 虚线网格
    )

    # Prepare additional plots for moving averages
    ap = []
    ma_colors = ["#ff9800", "#2196f3", "#9c27b0", "#00bcd4"]  # 橙、蓝、紫、青（更柔和）
    for i, window in enumerate(moving_averages):
        if window and window > 1 and window <= len(df):
            ma = df["close"].rolling(window=window).mean()
            ap.append(
                mpf.make_addplot(
                    ma,
                    label=f"MA{window}",
                    width=1.8,  # 适中的线条宽度
                    color=ma_colors[i % len(ma_colors)],
                )
            )

    # Calculate figure size in inches
    dpi = 150  # 提高DPI以获得更清晰的图像
    fig_width = width / dpi
    fig_height = height / dpi

    # Create the plot
    fig, axes = mpf.plot(
        df,
        type="candle",
        style=s,
        title=f"{symbol} ({timeframe}) - Recent Price",
        volume=False,
        figsize=(fig_width, fig_height),
        addplot=ap if ap else None,
        returnfig=True,
        tight_layout=True,
        scale_padding={"left": 0.1, "right": 0.9, "top": 0.9, "bottom": 0.1},
    )

    # Customize the plot
    ax_main = axes[0]
    ax_main.set_title(
        f"{symbol} ({timeframe}) - Recent Price",
        color=style_colors["text_color"],
        fontsize=12,
        pad=10,
    )

    # Format x-axis
    ax_main.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax_main.xaxis.set_major_locator(mticker.MaxNLocator(6))
    plt.setp(ax_main.get_xticklabels(), rotation=45, ha="right")

    # Save to bytes
    buf = io.BytesIO()
    plt.savefig(
        buf,
        format="png",
        dpi=dpi * scale,
        bbox_inches="tight",
        facecolor=style_colors["facecolor"],
        edgecolor="none",
    )
    buf.seek(0)

    # Clean up
    plt.close(fig)

    return buf.getvalue()


def generate_multi_candlestick_png(
    ccxt_exchange,
    symbols: List[str],
    timeframe: str = "1m",
    lookback_minutes: int = 60,
    theme: str = "dark",
    moving_averages: Optional[List[int]] = None,
    width: int = 1200,
    height: int = 900,
    scale: int = 2,
    timezone: str = "Asia/Shanghai",
) -> bytes:
    """Generate a composite PNG with up to 6 candlestick charts (2xN grid)."""
    # Lazy import
    try:
        import matplotlib.pyplot as plt
        import mplfinance as mpf
        import pandas as pd
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "matplotlib, pandas, and mplfinance are required for chart generation. "
            "Install with: pip install matplotlib pandas mplfinance"
        ) from e

    if moving_averages is None:
        moving_averages = []

    # Limit to 6 symbols
    symbols = list(symbols)[:6]
    if not symbols:
        raise ValueError("No symbols provided for multi-candlestick chart")

    # Determine grid size: 2 columns, rows = ceil(n/2)
    num = len(symbols)
    cols = 1 if num == 1 else 2
    rows = (num + cols - 1) // cols

    # Set up matplotlib style
    style_colors = _setup_matplotlib_style(theme)

    # Create custom style for mplfinance
    mc = mpf.make_marketcolors(
        up=style_colors["up_color"],
        down=style_colors["down_color"],
        edge=style_colors["wick_color"],
        wick=style_colors["wick_color"],
        volume="in",
    )

    mpf.make_mpf_style(
        marketcolors=mc,
        facecolor=style_colors["facecolor"],
        edgecolor=style_colors["edgecolor"],
        gridcolor=style_colors["grid_color"],
        figcolor=style_colors["facecolor"],
        y_on_right=False,
        gridstyle="--",  # 虚线网格
    )

    # Calculate figure size in inches
    dpi = 150  # 提高DPI以获得更清晰的图像
    fig_width = width / dpi
    fig_height = height / dpi

    # Create figure with subplots
    fig, axes = plt.subplots(rows, cols, figsize=(fig_width, fig_height), facecolor=style_colors["facecolor"])
    if rows == 1 and cols == 1:
        axes = [axes]
    elif rows == 1:
        axes = list(axes)
    else:
        axes = axes.flatten()

    # Resolve timezone
    try:
        tzinfo = pytz.timezone(timezone)
    except Exception:
        tzinfo = pytz.timezone("Asia/Shanghai")

    # Fetch and plot each symbol
    for idx, symbol in enumerate(symbols):
        ax = axes[idx]

        try:
            tf_minutes = parse_timeframe(timeframe)
        except Exception:
            unit = timeframe[-1]
            numv = int(timeframe[:-1])
            if unit == "m":
                tf_minutes = numv
            elif unit == "h":
                tf_minutes = numv * 60
            elif unit == "d":
                tf_minutes = numv * 1440
            else:
                tf_minutes = 1

        extra = (max(moving_averages) if moving_averages else 0) + 5
        approx_candles = int((lookback_minutes + tf_minutes - 1) // tf_minutes)
        limit = max(20, approx_candles + extra)
        since_ms = int((time.time() - lookback_minutes * 60) * 1000)

        try:
            ohlcv = ccxt_exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=limit)
        except Exception:
            ohlcv = ccxt_exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

        if not ohlcv or len(ohlcv) < 5:
            # Skip this subplot if no data
            ax.text(
                0.5,
                0.5,
                f"No data for {symbol}",
                ha="center",
                va="center",
                transform=ax.transAxes,
                color=style_colors["text_color"],
            )
            ax.set_title(f"{symbol} ({timeframe})", color=style_colors["text_color"])
            continue

        # Convert to pandas DataFrame
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(tzinfo)
        df.set_index("timestamp", inplace=True)

        # Create a simple candlestick plot using matplotlib
        ax.clear()

        # Plot candlesticks with enhanced visibility
        for i, (ts, row) in enumerate(df.iterrows()):
            # 设置颜色
            up_color = style_colors["up_color"]
            down_color = style_colors["down_color"]
            wick_color = style_colors["wick_color"]

            if row["close"] >= row["open"]:
                body_color = up_color
                alpha = 0.85  # 上涨K线稍微不透明
            else:
                body_color = down_color
                alpha = 0.75  # 下跌K线稍微透明

            # 绘制引线（加粗）
            ax.plot(
                [i, i],
                [row["low"], row["high"]],
                color=wick_color,
                linewidth=1.2,
                alpha=0.8,
                zorder=1,
            )

            # 绘制实体
            body_height = abs(row["close"] - row["open"])
            body_bottom = min(row["close"], row["open"])

            # 添加轻微的边框以提高可见性
            ax.bar(
                i,
                body_height,
                bottom=body_bottom,
                color=body_color,
                alpha=alpha,
                width=0.5,
                edgecolor=wick_color,
                linewidth=0.3,
                zorder=2,
            )

        # Plot moving averages with enhanced colors
        ma_colors = [
            "#ff9800",
            "#2196f3",
            "#9c27b0",
            "#00bcd4",
        ]  # 橙、蓝、紫、青（更柔和）
        for i, window in enumerate(moving_averages):
            if window and window > 1 and window <= len(df):
                ma = df["close"].rolling(window=window).mean()
                ax.plot(
                    range(len(df)),
                    ma,
                    label=f"MA{window}",
                    linewidth=1.8,
                    color=ma_colors[i % len(ma_colors)],
                    alpha=0.9,
                )

        ax.set_title(f"{symbol} ({timeframe})", color=style_colors["text_color"], fontsize=10)
        ax.set_facecolor(style_colors["facecolor"])
        ax.tick_params(colors=style_colors["text_color"])
        ax.grid(True, alpha=0.3, color=style_colors["grid_color"])

        # Set x-axis labels
        x_ticks = range(0, len(df), max(1, len(df) // 5))
        ax.set_xticks(x_ticks)
        ax.set_xticklabels([df.index[i].strftime("%H:%M") for i in x_ticks], rotation=45)

        # 只在第一个子图显示图例，并且只有在有标签的情况下
        if idx == 0 and ax.get_legend_handles_labels()[0]:
            ax.legend(fontsize=8)

    # Hide empty subplots
    for idx in range(num, len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()

    # Save to bytes
    buf = io.BytesIO()
    plt.savefig(
        buf,
        format="png",
        dpi=dpi * scale,
        bbox_inches="tight",
        facecolor=style_colors["facecolor"],
        edgecolor="none",
    )
    buf.seek(0)

    # Clean up
    plt.close(fig)

    return buf.getvalue()
