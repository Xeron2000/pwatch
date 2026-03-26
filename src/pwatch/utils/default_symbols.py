"""Default trading symbols based on market cap top 50 (excluding stablecoins)."""

# Market cap top 50 cryptocurrency trading pairs (USDT quoted, excluding stablecoins)
# Format: Symbol/USDT:USDT (for perpetual futures)
DEFAULT_TOP50_SYMBOLS = [
    "BTC/USDT:USDT",  # Bitcoin
    "ETH/USDT:USDT",  # Ethereum
    "BNB/USDT:USDT",  # BNB
    "XRP/USDT:USDT",  # XRP
    "SOL/USDT:USDT",  # Solana
    "DOGE/USDT:USDT",  # Dogecoin
    "ADA/USDT:USDT",  # Cardano
    "TRX/USDT:USDT",  # TRON
    "HYPE/USDT:USDT",  # Hyperliquid
    "SUI/USDT:USDT",  # Sui
    "BCH/USDT:USDT",  # Bitcoin Cash
    "LINK/USDT:USDT",  # Chainlink
    "ZEC/USDT:USDT",  # Zcash
    "HBAR/USDT:USDT",  # Hedera
    "XLM/USDT:USDT",  # Stellar
    "XMR/USDT:USDT",  # Monero
    "AVAX/USDT:USDT",  # Avalanche
    "SHIB/USDT:USDT",  # Shiba Inu
    "LEO/USDT:USDT",  # UNUS SED LEO
    "DOT/USDT:USDT",  # Polkadot
    "LTC/USDT:USDT",  # Litecoin
    "UNI/USDT:USDT",  # Uniswap
    "NEAR/USDT:USDT",  # NEAR Protocol
    "APT/USDT:USDT",  # Aptos
    "ICP/USDT:USDT",  # Internet Computer
    "PEPE/USDT:USDT",  # Pepe
    "KAS/USDT:USDT",  # Kaspa
    "RENDER/USDT:USDT",  # Render
    "ARB/USDT:USDT",  # Arbitrum
    "OP/USDT:USDT",  # Optimism
    "INJ/USDT:USDT",  # Injective
    "VET/USDT:USDT",  # VeChain
    "ETC/USDT:USDT",  # Ethereum Classic
    "OKB/USDT:USDT",  # OKB
    "CRO/USDT:USDT",  # Cronos
    "FIL/USDT:USDT",  # Filecoin
    "MNT/USDT:USDT",  # Mantle
    "IMX/USDT:USDT",  # Immutable
    "STX/USDT:USDT",  # Stacks
    "TIA/USDT:USDT",  # Celestia
    "SEI/USDT:USDT",  # Sei
    "BONK/USDT:USDT",  # Bonk
    "WIF/USDT:USDT",  # dogwifhat
    "FLOKI/USDT:USDT",  # Floki
    "FET/USDT:USDT",  # Artificial Superintelligence Alliance
    "AAVE/USDT:USDT",  # Aave
    "QNT/USDT:USDT",  # Quant
    "FTM/USDT:USDT",  # Fantom / Sonic
    "ALGO/USDT:USDT",  # Algorand
    "THETA/USDT:USDT",  # Theta Network
]

# Valid configuration options
VALID_EXCHANGES = ["okx", "bybit", "binance"]
VALID_TIMEFRAMES = ["1m", "5m", "15m", "1h", "1d"]

# Language-specific prompts
PROMPTS = {
    "zh": {
        # Basic prompts
        "language_select": "Please select language / 请选择语言:",
        "language_options": "1. English\n2. 中文",
        "welcome": "欢迎使用 pwatch 配置向导",
        "exchange_prompt": "选择交易所",
        "timeframe_prompt": "默认时间周期",
        "check_interval_prompt": "监控检查间隔",
        "threshold_prompt": "价格变化阈值 (%)",
        "timezone_prompt": "通知时区",
        "symbols_prompt": "监控交易对",
        "symbols_hint": "直接回车使用 auto 模式（自动选择通过质量过滤的活跃合约），或手动输入（逗号分隔）",
        "telegram_section": "Telegram 配置",
        "telegram_token_prompt": "Bot Token",
        "telegram_chatid_prompt": "Chat ID (可选，用作回退通道)",
        "config_complete": "配置完成!",
        "using_default_symbols": "使用默认市值前50币种",
        "using_auto_mode": "使用 auto 模式，将自动选择通过质量过滤的活跃交易对",
        # Exchange help
        "exchange_help": """💡 交易所说明:
   • OKX    - 推荐，无地区限制，API 稳定
   • Bybit  - 推荐，无地区限制，合约品种丰富
   • Binance - 中国大陆需要代理访问""",
        # Timeframe help
        "timeframe_help": """💡 时间周期说明:
   • 1m  - 最敏感，适合短线/高频监控
   • 5m  - 适中，推荐日常使用
   • 15m - 过滤小波动，减少通知
   • 1h  - 适合中长线趋势监控
   • 1d  - 适合长线投资者""",
        "timeframe_options": "可选值: 1m, 5m, 15m, 1h, 1d",
        # Check interval help
        "check_interval_help": """💡 检查间隔说明:
   检查间隔 ≠ 时间周期
   • 时间周期: K线聚合窗口（如 5m 表示 5 分钟 K 线）
   • 检查间隔: 多久检查一次价格变化
   建议: 检查间隔 ≤ 时间周期""",
        # Threshold help
        "threshold_help": """💡 阈值说明:
   价格变化超过此百分比才发送通知
   避免频繁通知，过滤小幅波动""",
        "threshold_examples": """   示例:
   • 0.5% - 敏感，适合短线交易者
   • 1%   - 适中，推荐大多数用户
   • 3%   - 宽松，只关注大幅波动""",
        # Symbols mode help
        "symbols_mode_help": """💡 交易对模式说明:
   1. auto (推荐)
      自动选择通过质量过滤的活跃 USDT 永续合约
      会综合成交额、持仓量、上市时间和近期波动率
      每 4 小时自动刷新列表

   2. default
      固定使用市值前 50 币种
      列表不会自动更新

   3. 手动输入
      自定义交易对列表
      用逗号分隔多个交易对""",
        "symbols_format_help": "格式: SYMBOL/USDT:USDT (如: BTC/USDT:USDT, ETH/USDT:USDT)",
        # Telegram help
        "telegram_token_help": """💡 如何获取 Bot Token:
   1. 在 Telegram 中搜索 @BotFather
   2. 发送 /newbot 创建新机器人
   3. 按提示设置机器人名称
   4. 复制返回的 Token (格式: 123456:ABC-DEF...)""",
        "telegram_chatid_help": """💡 如何获取 Chat ID:
   方法1: 搜索 @userinfobot，发送任意消息获取
   方法2: 搜索 @getmyid_bot，发送 /start 获取

   获取群组 ID: 将机器人加入群组后发送消息""",
        "telegram_chatid_optional": "Chat ID 为必填，用于发送 Telegram 通知",
        # Advanced config
        "advanced_config_prompt": "是否配置高级选项?",
        "advanced_config_hint": "高级选项包括: 通知冷却、优先级阈值等",
        "cooldown_help": """💡 通知冷却时间:
   同一交易对在冷却时间内不会重复通知
   避免短时间内收到大量相同通知
   格式: 5m, 10m, 30m, 1h 等""",
        "cooldown_prompt": "通知冷却时间",
        "priority_help": """💡 优先级阈值:
   根据价格变化幅度设置通知优先级
   高优先级通知会绕过冷却时间限制""",
        "priority_low_prompt": "低优先级阈值 (%)",
        "priority_medium_prompt": "中优先级阈值 (%)",
        "priority_high_prompt": "高优先级阈值 (%)",
        # Validation messages
        "invalid_exchange": "无效的交易所，请选择: okx, bybit, binance",
        "invalid_timeframe": "无效的时间周期，请选择: 1m, 5m, 15m, 1h, 1d",
        "invalid_threshold": "阈值必须是正数",
        "invalid_number": "请输入有效的数字",
        "yes_no_hint": "(y/n)",
    },
    "en": {
        # Basic prompts
        "language_select": "Please select language / 请选择语言:",
        "language_options": "1. English\n2. 中文",
        "welcome": "Welcome to pwatch setup",
        "exchange_prompt": "Select exchange",
        "timeframe_prompt": "Default timeframe",
        "check_interval_prompt": "Check interval",
        "threshold_prompt": "Price change threshold (%)",
        "timezone_prompt": "Notification timezone",
        "symbols_prompt": "Trading pairs to monitor",
        "symbols_hint": "Press Enter for auto mode (quality-filtered active contracts), or input manually (comma-separated)",
        "telegram_section": "Telegram Configuration",
        "telegram_token_prompt": "Bot Token",
        "telegram_chatid_prompt": "Chat ID (required for Telegram delivery)",
        "config_complete": "Configuration complete!",
        "using_default_symbols": "Using default top 50 symbols by market cap",
        "using_auto_mode": "Using auto mode, will select quality-filtered active symbols",
        # Exchange help
        "exchange_help": """💡 Exchange Info:
   • OKX    - Recommended, no regional restrictions, stable API
   • Bybit  - Recommended, no regional restrictions, rich derivatives
   • Binance - May require proxy in some regions (e.g., China)""",
        # Timeframe help
        "timeframe_help": """💡 Timeframe Info:
   • 1m  - Most sensitive, for scalping/high-frequency
   • 5m  - Balanced, recommended for daily use
   • 15m - Filters small moves, fewer notifications
   • 1h  - For medium/long-term trend monitoring
   • 1d  - For long-term investors""",
        "timeframe_options": "Options: 1m, 5m, 15m, 1h, 1d",
        # Check interval help
        "check_interval_help": """💡 Check Interval Info:
   Check interval ≠ Timeframe
   • Timeframe: K-line aggregation window (e.g., 5m = 5-minute candles)
   • Check interval: How often to check for price changes
   Tip: Check interval should be ≤ Timeframe""",
        # Threshold help
        "threshold_help": """💡 Threshold Info:
   Notifications are sent only when price change exceeds this percentage
   Helps filter out minor fluctuations""",
        "threshold_examples": """   Examples:
   • 0.5% - Sensitive, for active traders
   • 1%   - Balanced, recommended for most users
   • 3%   - Relaxed, only major movements""",
        # Symbols mode help
        "symbols_mode_help": """💡 Trading Pairs Mode:
   1. auto (Recommended)
      Automatically select quality-filtered active USDT perpetual contracts
      Uses quote volume, open interest, listing age, and recent volatility
      Refreshes every 4 hours

   2. default
      Fixed top 50 by market cap
      List does not auto-update

   3. Manual input
      Custom trading pairs list
      Separate multiple pairs with commas""",
        "symbols_format_help": "Format: SYMBOL/USDT:USDT (e.g., BTC/USDT:USDT, ETH/USDT:USDT)",
        # Telegram help
        "telegram_token_help": """💡 How to get Bot Token:
   1. Search @BotFather in Telegram
   2. Send /newbot to create a new bot
   3. Follow prompts to set bot name
   4. Copy the returned Token (format: 123456:ABC-DEF...)""",
        "telegram_chatid_help": """💡 How to get Chat ID:
   Method 1: Search @userinfobot, send any message
   Method 2: Search @getmyid_bot, send /start

   For group ID: Add bot to group and send a message""",
        "telegram_chatid_optional": "Chat ID is required for Telegram delivery",
        # Advanced config
        "advanced_config_prompt": "Configure advanced options?",
        "advanced_config_hint": "Advanced options include: notification cooldown and priority thresholds.",
        "cooldown_help": """💡 Notification Cooldown:
   Same trading pair won't trigger repeated notifications within cooldown period
   Prevents notification spam
   Format: 5m, 10m, 30m, 1h, etc.""",
        "cooldown_prompt": "Notification cooldown",
        "priority_help": """💡 Priority Thresholds:
   Set notification priority based on price change magnitude
   High priority notifications bypass cooldown limits""",
        "priority_low_prompt": "Low priority threshold (%)",
        "priority_medium_prompt": "Medium priority threshold (%)",
        "priority_high_prompt": "High priority threshold (%)",
        # Validation messages
        "invalid_exchange": "Invalid exchange, please choose: okx, bybit, binance",
        "invalid_timeframe": "Invalid timeframe, please choose: 1m, 5m, 15m, 1h, 1d",
        "invalid_threshold": "Threshold must be a positive number",
        "invalid_number": "Please enter a valid number",
        "yes_no_hint": "(y/n)",
    },
}


def get_default_symbols(exchange: str) -> list[str]:
    """
    Get default symbols based on exchange format.

    Args:
        exchange: Exchange name (okx, bybit, binance)

    Returns:
        List of default symbols in the correct format for the exchange
    """
    # All exchanges use the same format: SYMBOL/USDT:USDT
    return DEFAULT_TOP50_SYMBOLS.copy()


def get_prompt(language: str, key: str) -> str:
    """
    Get localized prompt text.

    Args:
        language: Language code ('zh' or 'en')
        key: Prompt key

    Returns:
        Localized prompt text
    """
    lang = language if language in PROMPTS else "en"
    return PROMPTS[lang].get(key, PROMPTS["en"][key])
