# pwatch

Cryptocurrency futures price monitor with Telegram alerts.

## Install

```bash
uv tool install git+https://github.com/Xeron2000/pwatch
```

## Usage

```bash
pwatch                                         # Start monitoring
pwatch update-markets                          # Update market data
pwatch update-markets --exchanges okx binance  # Update specific exchanges
pwatch config-path                             # Show config directory
```

First run guides you through setup — you'll need a [Telegram Bot Token](https://t.me/botfather).

## Config

Located at `~/.config/pwatch/config.yaml`:

```yaml
exchange: "okx"
defaultTimeframe: "5m"
checkInterval: "1m"
defaultThreshold: 1
notificationSymbols: "auto"  # top symbols after quality filters, refreshes every 4h
autoModeProfile: "conservative"
autoModeLimit: 40
autoModeMinQuoteVolume24h: 80000000      # filter out low-turnover symbols
autoModeMinOpenInterestUsd: 25000000     # avoid low-OI, easier-to-manipulate contracts
autoModeMinListingAgeDays: 45            # exclude very new listings
autoModeMaxRecentVolatilityPct: 6.0      # exclude ultra-wild symbols before they enter the pool

telegram:
  token: "your-bot-token"
  chatId: "your-chat-id"
```

## License

MIT
