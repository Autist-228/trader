import aiosqlite
import json
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "data/trader.db")


async def get_db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                is_admin INTEGER DEFAULT 0,
                is_registered INTEGER DEFAULT 0,
                trading_mode TEXT DEFAULT 'paper',
                trader_preset TEXT DEFAULT 'balanced',
                is_bot_active INTEGER DEFAULT 0,
                paper_balance REAL DEFAULT 10000.0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                leverage_min REAL DEFAULT 2.0,
                leverage_max REAL DEFAULT 5.0,
                position_size_min REAL DEFAULT 1.0,
                position_size_max REAL DEFAULT 3.0,
                sl_min REAL DEFAULT 1.0,
                sl_max REAL DEFAULT 3.0,
                tp_min REAL DEFAULT 2.0,
                tp_max REAL DEFAULT 5.0,
                max_daily_loss REAL DEFAULT 5.0,
                max_drawdown REAL DEFAULT 15.0,
                max_positions INTEGER DEFAULT 3,
                min_confidence REAL DEFAULT 65.0,
                coins TEXT DEFAULT '["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","BNBUSDT"]',
                notify_new_trade INTEGER DEFAULT 1,
                notify_close_trade INTEGER DEFAULT 1,
                notify_sl_hit INTEGER DEFAULT 1,
                notify_daily_report INTEGER DEFAULT 1,
                notify_errors INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS user_api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                encrypted_api_key TEXT NOT NULL,
                encrypted_api_secret TEXT NOT NULL,
                is_valid INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                leverage REAL NOT NULL,
                position_size_usdt REAL NOT NULL,
                quantity REAL NOT NULL,
                sl_price REAL,
                tp1_price REAL,
                tp2_price REAL,
                tp3_price REAL,
                pnl REAL DEFAULT 0.0,
                pnl_percent REAL DEFAULT 0.0,
                confidence REAL DEFAULT 0.0,
                ai_reasoning TEXT,
                status TEXT DEFAULT 'open',
                is_paper INTEGER DEFAULT 1,
                order_id TEXT,
                opened_at TEXT DEFAULT (datetime('now')),
                closed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS daily_pnl (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                total_pnl REAL DEFAULT 0.0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                UNIQUE(user_id, date),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS bot_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT DEFAULT 'INFO',
                module TEXT,
                message TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        await db.commit()
    finally:
        await db.close()
