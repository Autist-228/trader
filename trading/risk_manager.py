import logging
from datetime import date
from database.crud import get_open_trades, get_daily_pnl

logger = logging.getLogger(__name__)


class RiskManager:
    async def check_can_open(self, user_id: int, settings: dict) -> tuple[bool, str]:
        open_trades = await get_open_trades(user_id)
        if len(open_trades) >= settings["max_positions"]:
            return False, f"Max positions reached ({settings['max_positions']})"

        daily = await get_daily_pnl(user_id)
        if daily:
            if daily["total_pnl"] < 0 and abs(daily["total_pnl"]) >= settings["max_daily_loss"]:
                return False, f"Daily loss limit reached ({settings['max_daily_loss']}%)"

        return True, "OK"

    async def check_duplicate_position(self, user_id: int, symbol: str) -> bool:
        open_trades = await get_open_trades(user_id)
        for t in open_trades:
            if t["symbol"] == symbol:
                return True
        return False

    def calculate_position_size(
        self, balance: float, position_size_pct: float, leverage: int, price: float, instrument: dict
    ) -> float:
        usdt_amount = balance * (position_size_pct / 100)
        qty = (usdt_amount * leverage) / price

        step = instrument["qty_step"]
        qty = round(qty // step * step, 10)

        qty = max(instrument["min_qty"], min(qty, instrument["max_qty"]))
        return qty

    def calculate_sl_tp(
        self, side: str, entry_price: float, sl_pct: float,
        tp1_pct: float, tp2_pct: float, tp3_pct: float, tick_size: float,
    ) -> dict:
        def round_price(p: float) -> float:
            return round(round(p / tick_size) * tick_size, 10)

        if side == "Buy":
            sl = entry_price * (1 - sl_pct / 100)
            tp1 = entry_price * (1 + tp1_pct / 100)
            tp2 = entry_price * (1 + tp2_pct / 100)
            tp3 = entry_price * (1 + tp3_pct / 100)
        else:
            sl = entry_price * (1 + sl_pct / 100)
            tp1 = entry_price * (1 - tp1_pct / 100)
            tp2 = entry_price * (1 - tp2_pct / 100)
            tp3 = entry_price * (1 - tp3_pct / 100)

        return {
            "sl": round_price(sl),
            "tp1": round_price(tp1),
            "tp2": round_price(tp2),
            "tp3": round_price(tp3),
        }

    def calculate_pnl(self, side: str, entry_price: float, exit_price: float, quantity: float, leverage: int) -> dict:
        if side == "Buy":
            pnl = (exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price) * quantity

        position_value = entry_price * quantity / leverage
        pnl_pct = (pnl / position_value * 100) if position_value > 0 else 0

        return {"pnl": round(pnl, 4), "pnl_percent": round(pnl_pct, 2)}
