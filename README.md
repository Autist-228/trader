# AI Trading Bot for Bybit Futures

Multi-user Telegram-based AI trading platform for Bybit USDT Perpetual futures.

## Features

- **AI Model**: LightGBM classifier with 50+ technical features
- **3 AI Traders**: Conservative, Balanced, Aggressive presets
- **6 Coins**: BTC, ETH, SOL, XRP, DOGE, BNB
- **Paper Trading**: Built-in simulator using real Bybit prices
- **Live Trading**: Real orders on Bybit via API
- **Multi-user**: Any user can register via Telegram
- **Admin Panel**: Full user management and statistics
- **Risk Management**: Adaptive TP/SL, position sizing, daily limits
- **Encrypted Keys**: AES-256 encryption for all API keys

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/Autist-228/trader.git
cd trader
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_TELEGRAM_ID=your_telegram_id
ENCRYPTION_KEY=your_32_byte_hex_key
```

Generate encryption key:
```bash
python -c "import os; print(os.urandom(32).hex())"
```

### 3. Run

```bash
python main.py
```

## Deploy on VPS

### Ubuntu VPS ($5-10/month)

```bash
sudo apt update && sudo apt install -y python3 python3-pip git screen

git clone https://github.com/Autist-228/trader.git
cd trader
pip3 install -r requirements.txt

cp .env.example .env
nano .env  # fill in your values

screen -S trader
python3 main.py
# Press Ctrl+A, then D to detach
```

To check logs:
```bash
screen -r trader
```

## Commands

### User Commands
- `/start` - Main menu
- `/status` - Current status
- `/balance` - Check balance
- `/positions` - Open positions
- `/history` - Trade history
- `/pnl` - Profit/Loss summary
- `/settings` - Bot settings
- `/help` - Help

### Admin Commands
- `/admin` - Admin panel
- Users, stats, model status, retrain, broadcast, logs

## Architecture

```
main.py                  # Entry point
config.py                # Configuration
database/
  models.py              # SQLite schema
  crud.py                # Database operations
ai/
  features.py            # 50+ technical features
  model.py               # LightGBM model
  presets.py              # 3 AI trader presets
trading/
  bybit_client.py        # Bybit API wrapper
  risk_manager.py        # Risk management
  engine.py              # Trading engine
bot/
  keyboards.py           # Telegram keyboards
  handlers/
    start.py             # Registration
    settings.py          # Settings
    trading.py           # Trading controls
    admin.py             # Admin panel
utils/
  encryption.py          # AES-256 encryption
```
