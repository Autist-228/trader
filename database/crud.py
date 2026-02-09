import json
from datetime import datetime, date
from database.models import get_db
from utils.encryption import encrypt_value, decrypt_value


async def create_user(telegram_id: int, username: str = None, first_name: str = None, is_admin: bool = False) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username, first_name, is_admin, is_registered) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, username, first_name, 1 if is_admin else 0, 1 if is_admin else 0),
        )
        await db.commit()
        row = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user = await row.fetchone()
        user_id = user["id"]
        await db.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
        await db.commit()
        return user_id
    finally:
        await db.close()


async def get_user(telegram_id: int) -> dict | None:
    db = await get_db()
    try:
        row = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = await row.fetchone()
        if user:
            return dict(user)
        return None
    finally:
        await db.close()


async def get_user_by_id(user_id: int) -> dict | None:
    db = await get_db()
    try:
        row = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = await row.fetchone()
        if user:
            return dict(user)
        return None
    finally:
        await db.close()


async def update_user(telegram_id: int, **kwargs) -> None:
    db = await get_db()
    try:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [telegram_id]
        await db.execute(f"UPDATE users SET {sets} WHERE telegram_id = ?", vals)
        await db.commit()
    finally:
        await db.close()


async def get_user_settings(user_id: int) -> dict | None:
    db = await get_db()
    try:
        row = await db.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
        s = await row.fetchone()
        if s:
            d = dict(s)
            d["coins"] = json.loads(d["coins"])
            return d
        return None
    finally:
        await db.close()


async def update_user_settings(user_id: int, **kwargs) -> None:
    db = await get_db()
    try:
        if "coins" in kwargs and isinstance(kwargs["coins"], list):
            kwargs["coins"] = json.dumps(kwargs["coins"])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [user_id]
        await db.execute(f"UPDATE user_settings SET {sets} WHERE user_id = ?", vals)
        await db.commit()
    finally:
        await db.close()


async def save_api_keys(user_id: int, api_key: str, api_secret: str) -> None:
    enc_key = encrypt_value(api_key)
    enc_secret = encrypt_value(api_secret)
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO user_api_keys (user_id, encrypted_api_key, encrypted_api_secret)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
               encrypted_api_key = excluded.encrypted_api_key,
               encrypted_api_secret = excluded.encrypted_api_secret,
               is_valid = 1,
               created_at = datetime('now')""",
            (user_id, enc_key, enc_secret),
        )
        await db.commit()
    finally:
        await db.close()


async def get_api_keys(user_id: int) -> tuple[str, str] | None:
    db = await get_db()
    try:
        row = await db.execute(
            "SELECT encrypted_api_key, encrypted_api_secret FROM user_api_keys WHERE user_id = ? AND is_valid = 1",
            (user_id,),
        )
        keys = await row.fetchone()
        if keys:
            return decrypt_value(keys["encrypted_api_key"]), decrypt_value(keys["encrypted_api_secret"])
        return None
    finally:
        await db.close()


async def create_trade(
    user_id: int, symbol: str, side: str, entry_price: float,
    leverage: float, position_size_usdt: float, quantity: float,
    sl_price: float = None, tp1_price: float = None, tp2_price: float = None,
    tp3_price: float = None, confidence: float = 0.0, ai_reasoning: str = None,
    is_paper: bool = True, order_id: str = None,
) -> int:
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO trades (user_id, symbol, side, entry_price, leverage, position_size_usdt,
               quantity, sl_price, tp1_price, tp2_price, tp3_price, confidence, ai_reasoning,
               is_paper, order_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, symbol, side, entry_price, leverage, position_size_usdt,
             quantity, sl_price, tp1_price, tp2_price, tp3_price, confidence,
             ai_reasoning, 1 if is_paper else 0, order_id),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def close_trade(trade_id: int, exit_price: float, pnl: float, pnl_percent: float) -> None:
    db = await get_db()
    try:
        await db.execute(
            """UPDATE trades SET exit_price = ?, pnl = ?, pnl_percent = ?,
               status = 'closed', closed_at = datetime('now')
               WHERE id = ?""",
            (exit_price, pnl, pnl_percent, trade_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_open_trades(user_id: int) -> list[dict]:
    db = await get_db()
    try:
        rows = await db.execute(
            "SELECT * FROM trades WHERE user_id = ? AND status = 'open' ORDER BY opened_at DESC",
            (user_id,),
        )
        trades = await rows.fetchall()
        return [dict(t) for t in trades]
    finally:
        await db.close()


async def get_trade_history(user_id: int, limit: int = 20) -> list[dict]:
    db = await get_db()
    try:
        rows = await db.execute(
            "SELECT * FROM trades WHERE user_id = ? ORDER BY opened_at DESC LIMIT ?",
            (user_id, limit),
        )
        trades = await rows.fetchall()
        return [dict(t) for t in trades]
    finally:
        await db.close()


async def get_all_active_users() -> list[dict]:
    db = await get_db()
    try:
        rows = await db.execute(
            """SELECT u.*, us.coins, us.leverage_min, us.leverage_max, us.position_size_min,
               us.position_size_max, us.sl_min, us.sl_max, us.tp_min, us.tp_max,
               us.max_daily_loss, us.max_drawdown, us.max_positions, us.min_confidence
               FROM users u
               JOIN user_settings us ON us.user_id = u.id
               WHERE u.is_bot_active = 1 AND u.is_registered = 1""",
        )
        users = await rows.fetchall()
        result = []
        for u in users:
            d = dict(u)
            d["coins"] = json.loads(d["coins"])
            result.append(d)
        return result
    finally:
        await db.close()


async def get_all_users() -> list[dict]:
    db = await get_db()
    try:
        rows = await db.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = await rows.fetchall()
        return [dict(u) for u in users]
    finally:
        await db.close()


async def get_daily_pnl(user_id: int, target_date: str = None) -> dict | None:
    if target_date is None:
        target_date = date.today().isoformat()
    db = await get_db()
    try:
        row = await db.execute(
            "SELECT * FROM daily_pnl WHERE user_id = ? AND date = ?",
            (user_id, target_date),
        )
        pnl = await row.fetchone()
        if pnl:
            return dict(pnl)
        return None
    finally:
        await db.close()


async def update_daily_pnl(user_id: int, pnl: float, is_win: bool) -> None:
    today = date.today().isoformat()
    db = await get_db()
    try:
        existing = await db.execute(
            "SELECT * FROM daily_pnl WHERE user_id = ? AND date = ?", (user_id, today)
        )
        row = await existing.fetchone()
        if row:
            await db.execute(
                """UPDATE daily_pnl SET total_pnl = total_pnl + ?, total_trades = total_trades + 1,
                   winning_trades = winning_trades + ?, losing_trades = losing_trades + ?
                   WHERE user_id = ? AND date = ?""",
                (pnl, 1 if is_win else 0, 0 if is_win else 1, user_id, today),
            )
        else:
            await db.execute(
                """INSERT INTO daily_pnl (user_id, date, total_pnl, total_trades, winning_trades, losing_trades)
                   VALUES (?, ?, ?, 1, ?, ?)""",
                (user_id, today, pnl, 1 if is_win else 0, 0 if is_win else 1),
            )
        await db.commit()
    finally:
        await db.close()


async def get_user_total_pnl(user_id: int) -> dict:
    db = await get_db()
    try:
        row = await db.execute(
            """SELECT COALESCE(SUM(pnl), 0) as total_pnl,
               COUNT(*) as total_trades,
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses
               FROM trades WHERE user_id = ? AND status = 'closed'""",
            (user_id,),
        )
        result = await row.fetchone()
        return dict(result) if result else {"total_pnl": 0, "total_trades": 0, "wins": 0, "losses": 0}
    finally:
        await db.close()


async def get_platform_stats() -> dict:
    db = await get_db()
    try:
        users_row = await db.execute("SELECT COUNT(*) as cnt FROM users")
        users_count = (await users_row.fetchone())["cnt"]

        active_row = await db.execute("SELECT COUNT(*) as cnt FROM users WHERE is_bot_active = 1")
        active_count = (await active_row.fetchone())["cnt"]

        trades_row = await db.execute(
            """SELECT COUNT(*) as total, COALESCE(SUM(pnl), 0) as total_pnl,
               SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
               FROM trades WHERE status = 'closed'"""
        )
        trades = dict(await trades_row.fetchone())

        today_row = await db.execute(
            "SELECT COUNT(*) as cnt FROM trades WHERE date(opened_at) = date('now')"
        )
        today_trades = (await today_row.fetchone())["cnt"]

        return {
            "total_users": users_count,
            "active_bots": active_count,
            "total_trades": trades["total"],
            "total_pnl": trades["total_pnl"],
            "win_rate": (trades["wins"] / trades["total"] * 100) if trades["total"] > 0 else 0,
            "today_trades": today_trades,
        }
    finally:
        await db.close()


async def log_event(level: str, module: str, message: str) -> None:
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO bot_logs (level, module, message) VALUES (?, ?, ?)",
            (level, module, message),
        )
        await db.commit()
    finally:
        await db.close()
