"""Main CLI entry point for pwatch."""

import argparse
import asyncio
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

from pwatch.paths import (
    get_config_dir,
    get_config_path,
    get_log_path,
    get_markets_path,
    get_pid_path,
)


def get_user_input(prompt, default=None, secret=False):
    """Get user input with optional default value."""
    if default:
        suffix = f" [{default}]"
    else:
        suffix = ""

    if secret:
        import getpass

        value = getpass.getpass(f"{prompt}{suffix}: ")
    else:
        value = input(f"{prompt}{suffix}: ")

    if not value and default:
        return default
    return value


def print_section(title: str, char: str = "─"):
    """Print a section header."""
    print(f"\n📌 {title}")
    print(char * 40)


def print_help(text: str):
    """Print help text."""
    print(text)
    print()


def validate_exchange(value: str, language: str) -> tuple[bool, str]:
    """Validate exchange input."""
    from pwatch.utils.default_symbols import VALID_EXCHANGES, get_prompt

    value = value.lower().strip()
    if value in VALID_EXCHANGES:
        return True, value
    return False, get_prompt(language, "invalid_exchange")


def validate_timeframe(value: str, language: str) -> tuple[bool, str]:
    """Validate timeframe input."""
    from pwatch.utils.default_symbols import VALID_TIMEFRAMES, get_prompt

    value = value.lower().strip()
    if value in VALID_TIMEFRAMES:
        return True, value
    return False, get_prompt(language, "invalid_timeframe")


def validate_positive_number(value: str, language: str) -> tuple[bool, float | str]:
    """Validate positive number input."""
    from pwatch.utils.default_symbols import get_prompt

    try:
        num = float(value)
        if num > 0:
            return True, num
        return False, get_prompt(language, "invalid_threshold")
    except ValueError:
        return False, get_prompt(language, "invalid_number")


def validate_required_chat_id(value: str, language: str) -> tuple[bool, str]:
    """Validate that Telegram chat ID is present and numeric."""
    trimmed = value.strip()
    if not trimmed:
        return False, "Chat ID is required" if language == "en" else "Chat ID 为必填项"
    if trimmed.lstrip("-").isdigit():
        return True, trimmed
    return False, "Chat ID must be numeric" if language == "en" else "Chat ID 必须为数字字符串"


def get_validated_input(prompt: str, default: str, validator, language: str, secret: bool = False) -> str:
    """Get user input with validation."""
    while True:
        value = get_user_input(prompt, default=default, secret=secret)
        if not value and default:
            value = default
        valid, result = validator(value, language)
        if valid:
            return result
        print(f"❌ {result}")


def ask_yes_no(prompt: str, language: str, default: bool = False) -> bool:
    """Ask a yes/no question."""
    from pwatch.utils.default_symbols import get_prompt

    hint = get_prompt(language, "yes_no_hint")
    default_str = "y" if default else "n"
    response = get_user_input(f"{prompt} {hint}", default=default_str).lower().strip()
    return response in ("y", "yes", "是")


def interactive_config():
    """Interactive configuration setup with language selection and default symbols."""
    from pwatch.utils.default_symbols import get_prompt

    # Language selection
    print("\n" + "=" * 60)
    print(get_prompt("en", "language_select"))
    print("=" * 60)
    print(get_prompt("en", "language_options"))
    print()

    lang_choice = input("Enter option [1]: ").strip() or "1"
    language = "en" if lang_choice == "1" else "zh"

    # Welcome message
    print("\n" + "=" * 60)
    print(f"🚀 {get_prompt(language, 'welcome')}")
    print("=" * 60)

    config = {}

    # ==================== Exchange Selection ====================
    print_section(get_prompt(language, "exchange_prompt"))
    print_help(get_prompt(language, "exchange_help"))

    config["exchange"] = get_validated_input(
        get_prompt(language, "exchange_prompt"),
        default="okx",
        validator=validate_exchange,
        language=language,
    )

    # ==================== Timeframe Selection ====================
    print_section(get_prompt(language, "timeframe_prompt"))
    print_help(get_prompt(language, "timeframe_help"))
    print(f"   {get_prompt(language, 'timeframe_options')}\n")

    config["defaultTimeframe"] = get_validated_input(
        get_prompt(language, "timeframe_prompt"),
        default="5m",
        validator=validate_timeframe,
        language=language,
    )

    # ==================== Check Interval ====================
    print_section(get_prompt(language, "check_interval_prompt"))
    print_help(get_prompt(language, "check_interval_help"))
    print(f"   {get_prompt(language, 'timeframe_options')}\n")

    config["checkInterval"] = get_validated_input(
        get_prompt(language, "check_interval_prompt"),
        default="1m",
        validator=validate_timeframe,
        language=language,
    )

    # ==================== Threshold ====================
    print_section(get_prompt(language, "threshold_prompt"))
    print_help(get_prompt(language, "threshold_help"))
    print(get_prompt(language, "threshold_examples"))
    print()

    config["defaultThreshold"] = get_validated_input(
        get_prompt(language, "threshold_prompt"),
        default="1",
        validator=validate_positive_number,
        language=language,
    )

    # ==================== Timezone ====================
    config["notificationChannels"] = ["telegram"]
    config["notificationTimezone"] = get_user_input(get_prompt(language, "timezone_prompt"), default="Asia/Shanghai")

    # ==================== Trading Pairs ====================
    print_section(get_prompt(language, "symbols_prompt"))
    print_help(get_prompt(language, "symbols_mode_help"))
    print(f"   {get_prompt(language, 'symbols_format_help')}")
    print(f"   {get_prompt(language, 'symbols_hint')}\n")

    symbols_input = input("[auto]: ").strip()

    if not symbols_input or symbols_input.lower() == "auto":
        config["notificationSymbols"] = "auto"
        print(f"✅ {get_prompt(language, 'using_auto_mode')}")
    elif symbols_input.lower() == "default":
        config["notificationSymbols"] = "default"
        print(f"✅ {get_prompt(language, 'using_default_symbols')}")
    else:
        config["notificationSymbols"] = [
            s.strip() + (":USDT" if ":" not in s else "") for s in symbols_input.split(",") if s.strip()
        ]

    # ==================== Telegram Configuration ====================
    print_section(get_prompt(language, "telegram_section"))
    print_help(get_prompt(language, "telegram_token_help"))

    telegram = {}
    telegram["token"] = get_user_input(get_prompt(language, "telegram_token_prompt"), secret=True)

    print()
    print_help(get_prompt(language, "telegram_chatid_help"))
    print(f"   {get_prompt(language, 'telegram_chatid_optional')}\n")

    telegram["chatId"] = get_validated_input(
        get_prompt(language, "telegram_chatid_prompt"),
        default="",
        validator=validate_required_chat_id,
        language=language,
    )
    config["telegram"] = telegram


    # ==================== Advanced Configuration (Optional) ====================
    print_section(get_prompt(language, "advanced_config_prompt"))
    print(f"   {get_prompt(language, 'advanced_config_hint')}\n")

    if ask_yes_no(get_prompt(language, "advanced_config_prompt"), language, default=False):
        # Notification Cooldown
        print()
        print_help(get_prompt(language, "cooldown_help"))
        cooldown_input = get_user_input(get_prompt(language, "cooldown_prompt"), default="5m")
        config["notificationCooldown"] = cooldown_input.strip() or "5m"

        # Priority Thresholds
        print()
        print_help(get_prompt(language, "priority_help"))

        priority_thresholds = {}
        low_input = get_user_input(get_prompt(language, "priority_low_prompt"), default="0.5")
        medium_input = get_user_input(get_prompt(language, "priority_medium_prompt"), default="1")
        high_input = get_user_input(get_prompt(language, "priority_high_prompt"), default="3")

        try:
            priority_thresholds["low"] = float(low_input)
            priority_thresholds["medium"] = float(medium_input)
            priority_thresholds["high"] = float(high_input)
            config["priorityThresholds"] = priority_thresholds
        except ValueError:
            pass


    print("\n" + "=" * 60)
    print(f"✅ {get_prompt(language, 'config_complete')}")
    print("=" * 60 + "\n")

    return config


def ensure_config_exists():
    """Ensure configuration file exists, create interactively if not."""
    config_file = get_config_path()

    if config_file.exists():
        logging.info(f"Configuration file exists: {config_file}")
        return config_file

    print("\n⚠️  No config file found. Starting interactive setup...")
    print("⚠️  未找到配置文件，开始交互式配置...\n")
    config = interactive_config()

    import yaml

    config_file.touch(mode=0o600, exist_ok=True)
    with config_file.open("w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    print(f"✅ Config saved to: {config_file}")
    print(f"✅ 配置文件已保存: {config_file}")
    print(f"📝 Edit this file later if needed: {config_file}")
    print(f"📝 如需修改，请编辑: {config_file}\n")

    return config_file


def show_data_info():
    """Show data directory information."""
    config_dir = get_config_dir()
    print(f"📁 配置目录: {config_dir}")
    print(f"   - 配置文件: {get_config_path()}")
    print(f"   - 市场数据: {get_markets_path()}")
    print()


def update_markets(config):
    """Update supported markets for configured exchange."""
    exchange = config.get("exchange", "binance")

    logging.info(f"Updating supported markets for {exchange}...")

    from pwatch.utils.supported_markets import refresh_supported_markets

    try:
        refreshed = refresh_supported_markets([exchange])
        if refreshed:
            logging.info(f"Successfully updated markets for: {', '.join(sorted(refreshed))}")
            return True
        else:
            logging.warning("No market data received")
            return False
    except Exception as e:
        logging.warning(f"Failed to update markets: {e}")
        return False


def ensure_market_data(config):
    """Ensure market data is available before starting."""
    exchange = config.get("exchange", "binance")

    markets_file = get_markets_path()

    if not markets_file.exists():
        logging.info("Market data file not found, updating now...")
        return update_markets(config)

    import json

    with markets_file.open("r") as f:
        markets_data = json.load(f)

    if exchange not in markets_data or not markets_data[exchange]:
        logging.info(f"No market data for {exchange}, updating now...")
        return update_markets(config)

    logging.info(f"Market data verified for {exchange}")
    return True


async def run_monitoring():
    """Run price monitoring service."""
    from pwatch.core.sentry import PriceSentry
    from pwatch.notifications.telegram_bot_service import TelegramBotService
    from pwatch.utils.setup_logging import setup_logging

    bot_service = None
    try:
        sentry = PriceSentry()

        log_level = sentry.config.get("logLevel")
        if log_level:
            setup_logging(log_level)
        else:
            setup_logging()

        telegram_cfg = sentry.config.get("telegram", {})
        bot_service = TelegramBotService(telegram_cfg.get("token"))

        await bot_service.start()
        await sentry.run()
    except Exception as e:
        logging.error(f"Error in monitoring: {e}")
        raise
    finally:
        if bot_service:
            try:
                await bot_service.stop()
            except Exception:
                pass


def load_config(config_path):
    """Load configuration file."""
    import yaml

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def cmd_update_markets(args):
    """Subcommand: update supported market data."""
    from pwatch.utils.setup_logging import setup_logging
    from pwatch.utils.supported_markets import list_cached_exchanges, refresh_supported_markets

    setup_logging()

    DEFAULT_EXCHANGES = ["okx", "binance", "bybit"]
    exchange_names = list(args.exchanges or [])

    if not exchange_names:
        seeds = list(DEFAULT_EXCHANGES)

        config_path = get_config_path()
        if config_path.exists():
            config = load_config(config_path)
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

    exchange_names = list(dict.fromkeys(name for name in exchange_names if name))
    if not exchange_names:
        logging.warning("No exchanges to update.")
        return

    logging.info("Updating supported markets for: %s", ", ".join(exchange_names))
    refreshed = refresh_supported_markets(exchange_names)
    if refreshed:
        logging.info("Updated %s exchanges: %s", len(refreshed), ", ".join(sorted(refreshed)))
    else:
        logging.warning("No exchanges produced market data.")




def _read_pid_file() -> tuple[int, str | None] | None:
    pid_path = get_pid_path()
    if not pid_path.exists():
        return None
    try:
        lines = pid_path.read_text(encoding="utf-8").splitlines()
        pid = int(lines[0].strip())
        command = lines[1].strip() if len(lines) > 1 else None
        return pid, command
    except (OSError, ValueError, IndexError):
        return None


def _pid_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _pid_matches_runner(pid: int) -> bool:
    cmdline_path = Path(f"/proc/{pid}/cmdline")
    try:
        cmdline = cmdline_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    runner = _get_runner_module()
    return runner in cmdline


def _get_running_pid() -> int | None:
    record = _read_pid_file()
    if record is None:
        return None
    pid, _command = record
    if _pid_is_running(pid) and _pid_matches_runner(pid):
        return pid
    try:
        get_pid_path().unlink()
    except OSError:
        pass
    return None


def _get_python_executable() -> str:
    return sys.executable


def _get_runner_module() -> str:
    return "pwatch.app.runner"


def _run_start_preflight() -> None:
    config_path = ensure_config_exists()
    show_data_info()
    config = load_config(config_path)

    if "telegram" in config.get("notificationChannels", []):
        if not _validate_telegram_token(config):
            print("❌ Telegram token 无效或未配置")
            print("请检查 ~/.config/pwatch/config.yaml 中的 telegram.token 设置")
            print("格式: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz")
            sys.exit(1)
        telegram_chat_id = str(config.get("telegram", {}).get("chatId", "")).strip()
        if not telegram_chat_id:
            print("❌ Telegram chatId 未配置")
            print("请检查 ~/.config/pwatch/config.yaml 中的 telegram.chatId 设置")
            sys.exit(1)
        print("✅ Telegram 配置验证通过")

    print("📊 正在验证市场数据...")
    if not ensure_market_data(config):
        logging.error("❌ 无法获取市场数据，请检查网络或使用代理")
        sys.exit(1)


def _write_pid_file(pid: int) -> None:
    get_pid_path().write_text(f"{pid}\n{_get_runner_module()}\n", encoding="utf-8")


def cmd_start(_args):
    """Start price monitoring in the background."""
    running_pid = _get_running_pid()
    log_path = get_log_path()
    if running_pid is not None:
        print(f"pwatch is already running in background (PID: {running_pid})")
        print(f"Log: {log_path}")
        return

    _run_start_preflight()

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log_file:
        process = subprocess.Popen(
            [_get_python_executable(), "-m", _get_runner_module()],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    if process.poll() is not None:
        raise SystemExit("Failed to start pwatch in background")

    _write_pid_file(process.pid)
    print(f"pwatch started in background (PID: {process.pid})")
    print(f"Log: {log_path}")


def cmd_status(_args):
    """Show background process status."""
    running_pid = _get_running_pid()
    if running_pid is None:
        print("pwatch is not running")
        return
    print(f"pwatch is running (PID: {running_pid})")
    print(f"Log: {get_log_path()}")


def cmd_stop(_args):
    """Stop the background process if running."""
    running_pid = _get_running_pid()
    if running_pid is None:
        print("pwatch is not running")
        return
    os.kill(running_pid, signal.SIGTERM)
    try:
        get_pid_path().unlink()
    except OSError:
        pass
    print(f"pwatch stopped (PID: {running_pid})")


def cmd_logs(_args):
    """Print the current log file contents."""
    log_path = get_log_path()
    if not log_path.exists():
        print(f"Log file not found: {log_path}")
        return
    print(log_path.read_text(encoding="utf-8", errors="replace"), end="")


def _validate_telegram_token(config: dict) -> bool:
    """Validate Telegram token format. Returns True if valid."""
    import re
    telegram_config = config.get("telegram", {})
    token = telegram_config.get("token", "")
    if not token or token == "YOUR_TELEGRAM_TOKEN":
        return False
    # Token format: digits:alphanumeric
    if not re.match(r"^\d+:[A-Za-z0-9_-]+$", token):
        return False
    return True

def cmd_run(args):
    """Subcommand: run price monitoring (default)."""
    from pwatch.utils.setup_logging import setup_logging

    setup_logging(console=True)

    print("\n🚀 pwatch 启动中...\n")

    try:
        _run_start_preflight()
        asyncio.run(run_monitoring())

        asyncio.run(run_monitoring())

    except KeyboardInterrupt:
        logging.info("\n\n👋 pwatch 已停止")
    except Exception as e:
        logging.error(f"❌ 启动失败: {e}")
        sys.exit(1)


def cmd_config_path(_args):
    """Subcommand: print config directory path."""
    print(get_config_dir())


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(prog="pwatch", description="Cryptocurrency futures price monitor")
    sub = parser.add_subparsers(dest="command")

    # pwatch run (foreground)
    sub.add_parser("run", help="Start price monitoring in foreground")
    sub.add_parser("start", help="Start price monitoring in background")
    sub.add_parser("status", help="Show background process status")
    sub.add_parser("stop", help="Stop background process")
    sub.add_parser("logs", help="Print background log file")

    # pwatch update-markets
    um = sub.add_parser("update-markets", help="Fetch and cache supported market data")
    um.add_argument("--exchanges", nargs="+", help="Exchanges to update (default: all)")

    # pwatch config-path
    sub.add_parser("config-path", help="Print config directory path")

    args = parser.parse_args()

    commands = {
        "run": cmd_run,
        "start": cmd_start,
        "status": cmd_status,
        "stop": cmd_stop,
        "logs": cmd_logs,
        "update-markets": cmd_update_markets,
        "config-path": cmd_config_path,
    }

    handler = commands.get(args.command, cmd_start)
    handler(args)


if __name__ == "__main__":
    main()
