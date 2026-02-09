import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")
DB_PATH = os.getenv("DB_PATH", "data/trader.db")

SUPPORTED_COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT"]

COIN_DISPLAY = {
    "BTCUSDT": "BTC/USDT",
    "ETHUSDT": "ETH/USDT",
    "SOLUSDT": "SOL/USDT",
    "XRPUSDT": "XRP/USDT",
    "DOGEUSDT": "DOGE/USDT",
    "BNBUSDT": "BNB/USDT",
}

TIMEFRAMES = {
    "5m": "5",
    "15m": "15",
    "1h": "60",
    "4h": "240",
}

CATEGORY = "linear"
