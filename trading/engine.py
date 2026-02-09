import asyncio
import logging
from datetime import datetime
from trading.bybit_client import BybitClient
from trading.risk_manager import RiskManager
from ai.model import AIModel
from ai.features import build_features, FEATURE_COLUMNS
from ai.presets import calculate_adaptive_params, get_preset
from database.crud import (
    get_all_active_users, get_api_keys, get_open_trades,
    create_trade, close_trade, update_daily_pnl, log_event,
    get_user_by_id,
)
from config import CATEGORY

logger = logging.getLogger(__name__)

_public_client = None


def get_public_client() -> BybitClient:
    global _public_client
    if _public_client is None:
        _public_client = BybitClient(api_key="", api_secret="")
    return _public_client


class TradingEngine:
    def __init__(self, ai_model: AIModel, notify_callback=None):
        self.ai_model = ai_model
        self.risk_manager = RiskManager()
        self.notify_callback = notify_callback
        self.is_running = False

    async def notify(self, telegram_id: int, message: str):
        if self.notify_callback:
            try:
                await self.notify_callback(telegram_id, message)
            except Exception as e:
                logger.error(f"Notify error: {e}")

    async def analyze_symbol(self, symbol: str, timeframe: str = "15") -> dict:
        client = get_public_client()
        candles = client.get_klines(symbol=symbol, interval=timeframe, limit=200)
        if not candles:
            return {"signal": "HOLD", "confidence": 0.0}

        ticker = client.get_ticker(symbol)
        oi_data = client.get_open_interest(symbol)

        df = build_features(candles, ticker, oi_data)
        if df.empty:
            return {"signal": "HOLD", "confidence": 0.0}

        available = [c for c in FEATURE_COLUMNS if c in df.columns]
        if not available:
            return {"signal": "HOLD", "confidence": 0.0}

        last_row = df[available].iloc[-1].values
        prediction = self.ai_model.predict(last_row)

        atr_pct = float(df["atr_pct"].iloc[-1]) if "atr_pct" in df.columns else 0.01
        prediction["atr_pct"] = atr_pct
        prediction["last_price"] = float(df["close"].iloc[-1])

        return prediction

    async def process_user(self, user_data: dict):
        user_id = user_data["id"]
        telegram_id = user_data["telegram_id"]
        preset_name = user_data["trader_preset"]
        trading_mode = user_data["trading_mode"]
        coins = user_data["coins"]
        min_confidence = user_data["min_confidence"]
        preset = get_preset(preset_name)
        timeframes = preset.get("timeframes", ["15"])
        primary_tf = timeframes[0]

        is_paper = trading_mode == "paper"
        user_client = None

        if not is_paper:
            keys = await get_api_keys(user_id)
            if not keys:
                return
            user_client = BybitClient(keys[0], keys[1])

        for symbol in coins:
            try:
                has_position = await self.risk_manager.check_duplicate_position(user_id, symbol)
                if has_position:
                    continue

                can_open, reason = await self.risk_manager.check_can_open(user_id, user_data)
                if not can_open:
                    continue

                analysis = await self.analyze_symbol(symbol, primary_tf)
                signal = analysis["signal"]
                confidence = analysis["confidence"]

                if signal == "HOLD" or confidence < min_confidence:
                    continue

                params = calculate_adaptive_params(preset_name, confidence, analysis.get("atr_pct", 0.01))
                price = analysis["last_price"]

                if is_paper:
                    user = await get_user_by_id(user_id)
                    balance = user["paper_balance"]
                    instrument = {
                        "min_qty": 0.001, "max_qty": 1000000,
                        "qty_step": 0.001, "tick_size": 0.01,
                    }
                else:
                    bal = user_client.get_balance()
                    if not bal:
                        continue
                    balance = bal["available"]
                    instrument = user_client.get_instrument_info(symbol)
                    if not instrument:
                        continue

                qty = self.risk_manager.calculate_position_size(
                    balance, params["position_size_pct"], params["leverage"], price, instrument
                )
                if qty <= 0:
                    continue

                side = "Buy" if signal == "BUY" else "Sell"
                tick = instrument.get("tick_size", 0.01)
                levels = self.risk_manager.calculate_sl_tp(
                    side, price, params["sl_pct"],
                    params["tp1_pct"], params["tp2_pct"], params["tp3_pct"], tick
                )

                order_id = None
                if not is_paper:
                    user_client.set_leverage(symbol, params["leverage"])
                    result = user_client.place_order(
                        symbol=symbol, side=side, qty=qty,
                        sl_price=levels["sl"], tp_price=levels["tp1"],
                    )
                    if not result:
                        await log_event("ERROR", "engine", f"Order failed for user {user_id} on {symbol}")
                        continue
                    order_id = result["order_id"]

                position_usdt = qty * price / params["leverage"]
                trade_id = await create_trade(
                    user_id=user_id, symbol=symbol, side=side, entry_price=price,
                    leverage=params["leverage"], position_size_usdt=position_usdt,
                    quantity=qty, sl_price=levels["sl"],
                    tp1_price=levels["tp1"], tp2_price=levels["tp2"], tp3_price=levels["tp3"],
                    confidence=confidence, ai_reasoning=f"{signal} conf={confidence:.1f}%",
                    is_paper=is_paper, order_id=order_id,
                )

                msg = (
                    f"{'[ДЕМО] ' if is_paper else ''}{'ПОКУПКА' if side == 'Buy' else 'ПРОДАЖА'} {symbol}\n"
                    f"💵 Цена: {price}\n"
                    f"⚙️ Плечо: {params['leverage']}x\n"
                    f"📦 Размер: {position_usdt:.2f} USDT\n"
                    f"🛡 SL: {levels['sl']} | 🎯 TP: {levels['tp1']}/{levels['tp2']}/{levels['tp3']}\n"
                    f"🤖 Уверенность AI: {confidence:.1f}%"
                )
                await self.notify(telegram_id, msg)
                await log_event("INFO", "engine", f"Trade opened: {side} {symbol} for user {user_id}")

            except Exception as e:
                logger.error(f"Error processing {symbol} for user {user_id}: {e}")
                await log_event("ERROR", "engine", f"{symbol} error for user {user_id}: {str(e)}")

    async def check_positions(self, user_data: dict):
        user_id = user_data["id"]
        telegram_id = user_data["telegram_id"]
        trading_mode = user_data["trading_mode"]
        is_paper = trading_mode == "paper"

        open_trades = await get_open_trades(user_id)
        if not open_trades:
            return

        for trade in open_trades:
            try:
                symbol = trade["symbol"]
                client = get_public_client()
                ticker = client.get_ticker(symbol)
                if not ticker:
                    continue

                current_price = ticker["last_price"]
                side = trade["side"]
                sl = trade["sl_price"]
                tp1 = trade["tp1_price"]

                should_close = False
                close_reason = ""

                if side == "Buy":
                    if sl and current_price <= sl:
                        should_close = True
                        close_reason = "SL hit"
                    elif tp1 and current_price >= tp1:
                        should_close = True
                        close_reason = "TP hit"
                else:
                    if sl and current_price >= sl:
                        should_close = True
                        close_reason = "SL hit"
                    elif tp1 and current_price <= tp1:
                        should_close = True
                        close_reason = "TP hit"

                if should_close:
                    pnl_data = self.risk_manager.calculate_pnl(
                        side, trade["entry_price"], current_price,
                        trade["quantity"], trade["leverage"]
                    )

                    if not is_paper:
                        keys = await get_api_keys(user_id)
                        if keys:
                            uc = BybitClient(keys[0], keys[1])
                            uc.close_position(symbol, side, trade["quantity"])

                    await close_trade(trade["id"], current_price, pnl_data["pnl"], pnl_data["pnl_percent"])
                    await update_daily_pnl(user_id, pnl_data["pnl_percent"], pnl_data["pnl"] > 0)

                    if is_paper:
                        from database.crud import update_user, get_user_by_id
                        user = await get_user_by_id(user_id)
                        new_balance = user["paper_balance"] + pnl_data["pnl"]
                        await update_user(telegram_id, paper_balance=new_balance)

                    emoji = "+" if pnl_data["pnl"] > 0 else ""
                    msg = (
                        f"{'[PAPER] ' if is_paper else ''}{close_reason}: {symbol}\n"
                        f"Side: {side}\n"
                        f"Entry: {trade['entry_price']} -> Exit: {current_price}\n"
                        f"PnL: {emoji}{pnl_data['pnl']:.4f} USDT ({emoji}{pnl_data['pnl_percent']:.2f}%)"
                    )
                    await self.notify(telegram_id, msg)

            except Exception as e:
                logger.error(f"Position check error for trade {trade['id']}: {e}")

    async def run_cycle(self):
        try:
            active_users = await get_all_active_users()
            for user_data in active_users:
                await self.check_positions(user_data)
                await self.process_user(user_data)
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Cycle error: {e}")
            await log_event("ERROR", "engine", f"Cycle error: {str(e)}")

    async def start(self, interval: int = 60):
        self.is_running = True
        logger.info("Trading engine started")
        await log_event("INFO", "engine", "Trading engine started")
        while self.is_running:
            await self.run_cycle()
            await asyncio.sleep(interval)

    def stop(self):
        self.is_running = False
        logger.info("Trading engine stopped")

    async def train_model(self, symbols: list[str] = None, timeframe: str = "60"):
        if symbols is None:
            symbols = ["BTCUSDT", "ETHUSDT"]

        client = get_public_client()
        all_dfs = []
        for symbol in symbols:
            candles = client.get_klines(symbol=symbol, interval=timeframe, limit=200)
            if candles:
                ticker = client.get_ticker(symbol)
                df = build_features(candles, ticker)
                if not df.empty:
                    df["symbol"] = symbol
                    all_dfs.append(df)

        if not all_dfs:
            return False

        import pandas as pd
        combined = pd.concat(all_dfs, ignore_index=True)
        available = [c for c in FEATURE_COLUMNS if c in combined.columns]
        return self.ai_model.train(combined, available)
