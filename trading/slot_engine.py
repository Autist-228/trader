import asyncio
import logging
import random
from datetime import datetime
from trading.bybit_client import BybitClient
from trading.risk_manager import RiskManager
from ai.model import AIModel
from ai.features import build_features, FEATURE_COLUMNS
from ai.presets import calculate_adaptive_params, get_preset

logger = logging.getLogger(__name__)

SLOT_COUNT = 10
SLOT_INITIAL_BALANCE = 10.0
SLOT_TARGET = 50.0
BOOST_PRESET = "bankroll_boost"
COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "BNBUSDT"]


class Slot:
    def __init__(self, slot_id: int, balance: float = SLOT_INITIAL_BALANCE):
        self.slot_id = slot_id
        self.balance = balance
        self.initial_balance = balance
        self.target = SLOT_TARGET
        self.is_active = True
        self.is_liquidated = False
        self.reached_target = False
        self.open_trade = None
        self.trade_history = []
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.peak_balance = balance

    @property
    def pnl(self) -> float:
        return self.balance - self.initial_balance

    @property
    def pnl_pct(self) -> float:
        return (self.pnl / self.initial_balance) * 100

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.wins / self.total_trades) * 100

    def status_line(self) -> str:
        if self.reached_target:
            tag = "TARGET"
        elif self.is_liquidated:
            tag = "LIQUIDATED"
        elif self.open_trade:
            tag = "IN TRADE"
        elif self.is_active:
            tag = "WAITING"
        else:
            tag = "STOPPED"

        pnl_sign = "+" if self.pnl >= 0 else ""
        return (
            f"Slot #{self.slot_id}: ${self.balance:.2f} [{tag}] "
            f"PnL: {pnl_sign}${self.pnl:.2f} ({pnl_sign}{self.pnl_pct:.1f}%) "
            f"Trades: {self.total_trades} W:{self.wins} L:{self.losses} WR:{self.win_rate:.0f}%"
        )


class SlotEngine:
    def __init__(self, ai_model: AIModel, log_callback=None):
        self.ai_model = ai_model
        self.risk_manager = RiskManager()
        self.slots = [Slot(i + 1) for i in range(SLOT_COUNT)]
        self.is_running = False
        self.log_callback = log_callback
        self.cycle_count = 0
        self.start_time = None
        self._public_client = None

    def _get_client(self) -> BybitClient:
        if self._public_client is None:
            self._public_client = BybitClient(api_key="", api_secret="")
        return self._public_client

    async def log(self, message: str):
        logger.info(message)
        if self.log_callback:
            try:
                await self.log_callback(message)
            except Exception:
                pass

    async def analyze(self, symbol: str, timeframe: str = "5") -> dict:
        client = self._get_client()
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

    async def process_slot(self, slot: Slot):
        if not slot.is_active or slot.is_liquidated or slot.reached_target:
            return

        if slot.open_trade:
            await self.check_slot_trade(slot)
            return

        if slot.balance < 1.0:
            slot.is_liquidated = True
            slot.is_active = False
            await self.log(f"Slot #{slot.slot_id} LIQUIDATED (balance ${slot.balance:.2f})")
            return

        if slot.balance >= slot.target:
            slot.reached_target = True
            slot.is_active = False
            await self.log(
                f"Slot #{slot.slot_id} REACHED TARGET! ${slot.initial_balance:.2f} -> ${slot.balance:.2f} "
                f"in {slot.total_trades} trades!"
            )
            return

        coins = list(COINS)
        random.shuffle(coins)

        preset = get_preset(BOOST_PRESET)
        min_confidence = preset["min_confidence"]

        for symbol in coins:
            try:
                analysis = await self.analyze(symbol, preset["timeframes"][0])
                signal = analysis["signal"]
                confidence = analysis["confidence"]

                if signal == "HOLD" or confidence < min_confidence:
                    continue

                params = calculate_adaptive_params(BOOST_PRESET, confidence, analysis.get("atr_pct", 0.01))
                price = analysis["last_price"]

                position_pct = params["position_size_pct"]
                usdt_amount = slot.balance * (position_pct / 100)
                leverage = params["leverage"]
                qty = (usdt_amount * leverage) / price

                qty_step = 0.001
                qty = round(qty // qty_step * qty_step, 10)
                if qty <= 0:
                    continue

                side = "Buy" if signal == "BUY" else "Sell"
                tick = 0.01
                levels = self.risk_manager.calculate_sl_tp(
                    side, price, params["sl_pct"],
                    params["tp1_pct"], params["tp2_pct"], params["tp3_pct"], tick
                )

                slot.open_trade = {
                    "symbol": symbol,
                    "side": side,
                    "entry_price": price,
                    "quantity": qty,
                    "leverage": leverage,
                    "sl": levels["sl"],
                    "tp1": levels["tp1"],
                    "tp2": levels["tp2"],
                    "tp3": levels["tp3"],
                    "position_usdt": usdt_amount,
                    "confidence": confidence,
                    "opened_at": datetime.utcnow().isoformat(),
                }

                await self.log(
                    f"Slot #{slot.slot_id} OPEN {side} {symbol} @ {price:.2f} "
                    f"| Lev: {leverage}x | Size: ${usdt_amount:.2f} | Conf: {confidence:.1f}% "
                    f"| SL: {levels['sl']:.2f} TP: {levels['tp1']:.2f}"
                )
                break

            except Exception as e:
                logger.error(f"Slot #{slot.slot_id} error on {symbol}: {e}")

    async def check_slot_trade(self, slot: Slot):
        trade = slot.open_trade
        if not trade:
            return

        try:
            client = self._get_client()
            ticker = client.get_ticker(trade["symbol"])
            if not ticker:
                return

            current_price = ticker["last_price"]
            side = trade["side"]
            sl = trade["sl"]
            tp1 = trade["tp1"]

            should_close = False
            close_reason = ""

            if side == "Buy":
                if current_price <= sl:
                    should_close = True
                    close_reason = "SL"
                elif current_price >= tp1:
                    should_close = True
                    close_reason = "TP"
            else:
                if current_price >= sl:
                    should_close = True
                    close_reason = "SL"
                elif current_price <= tp1:
                    should_close = True
                    close_reason = "TP"

            if should_close:
                pnl_data = self.risk_manager.calculate_pnl(
                    side, trade["entry_price"], current_price,
                    trade["quantity"], trade["leverage"]
                )
                pnl = pnl_data["pnl"]
                pnl_pct = pnl_data["pnl_percent"]

                slot.balance += pnl
                slot.total_trades += 1
                if pnl > 0:
                    slot.wins += 1
                else:
                    slot.losses += 1

                if slot.balance > slot.peak_balance:
                    slot.peak_balance = slot.balance

                pnl_sign = "+" if pnl >= 0 else ""
                await self.log(
                    f"Slot #{slot.slot_id} CLOSE [{close_reason}] {trade['symbol']} "
                    f"| {pnl_sign}${pnl:.4f} ({pnl_sign}{pnl_pct:.2f}%) "
                    f"| Balance: ${slot.balance:.2f}"
                )

                slot.trade_history.append({
                    "symbol": trade["symbol"],
                    "side": side,
                    "entry": trade["entry_price"],
                    "exit": current_price,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "reason": close_reason,
                })
                slot.open_trade = None

        except Exception as e:
            logger.error(f"Slot #{slot.slot_id} check error: {e}")

    def get_summary(self) -> str:
        active = sum(1 for s in self.slots if s.is_active)
        liquidated = sum(1 for s in self.slots if s.is_liquidated)
        reached = sum(1 for s in self.slots if s.reached_target)
        total_balance = sum(s.balance for s in self.slots)
        total_initial = sum(s.initial_balance for s in self.slots)
        total_pnl = total_balance - total_initial
        total_trades = sum(s.total_trades for s in self.slots)
        total_wins = sum(s.wins for s in self.slots)

        elapsed = ""
        if self.start_time:
            delta = datetime.utcnow() - self.start_time
            minutes = int(delta.total_seconds() / 60)
            seconds = int(delta.total_seconds() % 60)
            elapsed = f" | Elapsed: {minutes}m {seconds}s"

        lines = [
            f"=== BANKROLL BOOST STATUS (Cycle #{self.cycle_count}){elapsed} ===",
            f"Total: ${total_balance:.2f} / ${total_initial:.2f} "
            f"(PnL: {'+'if total_pnl>=0 else ''}{total_pnl:.2f})",
            f"Active: {active} | Target: {reached} | Liquidated: {liquidated}",
            f"Total Trades: {total_trades} | Wins: {total_wins} | "
            f"WR: {(total_wins/total_trades*100) if total_trades>0 else 0:.0f}%",
            "",
        ]
        for slot in self.slots:
            lines.append(slot.status_line())

        return "\n".join(lines)

    async def run(self, duration_minutes: int = 30, cycle_interval: int = 30):
        self.is_running = True
        self.start_time = datetime.utcnow()
        end_time = self.start_time.timestamp() + duration_minutes * 60

        await self.log(f"Bankroll Boost started: {SLOT_COUNT} slots x ${SLOT_INITIAL_BALANCE} = ${SLOT_COUNT * SLOT_INITIAL_BALANCE}")
        await self.log(f"Target: ${SLOT_TARGET} per slot | Duration: {duration_minutes} min | Interval: {cycle_interval}s")

        while self.is_running and datetime.utcnow().timestamp() < end_time:
            self.cycle_count += 1

            active_slots = [s for s in self.slots if s.is_active]
            if not active_slots:
                await self.log("All slots finished (liquidated or reached target)")
                break

            for slot in active_slots:
                await self.process_slot(slot)
                await asyncio.sleep(0.5)

            if self.cycle_count % 5 == 0:
                await self.log(self.get_summary())

            await asyncio.sleep(cycle_interval)

        self.is_running = False
        await self.log("\n" + self.get_summary())
        await self.log("Bankroll Boost finished!")

    def stop(self):
        self.is_running = False
