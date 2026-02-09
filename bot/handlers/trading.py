from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.crud import (
    get_user, update_user, get_api_keys, get_open_trades,
    get_trade_history, get_user_total_pnl, get_user_settings,
)
from trading.bybit_client import BybitClient
from bot.keyboards import main_menu_kb, back_kb
from config import COIN_DISPLAY

router = Router()


class ApiKeyInput(StatesGroup):
    waiting_key = State()
    waiting_secret = State()


@router.callback_query(F.data == "status")
async def show_status(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Please /start first")
        return

    open_trades = await get_open_trades(user["id"])
    pnl_data = await get_user_total_pnl(user["id"])

    text = (
        f"Status\n\n"
        f"Mode: {'Paper' if user['trading_mode'] == 'paper' else 'LIVE'}\n"
        f"Preset: {user['trader_preset'].capitalize()}\n"
        f"Bot: {'Active' if user['is_bot_active'] else 'Stopped'}\n\n"
        f"Open Positions: {len(open_trades)}\n"
        f"Total Trades: {pnl_data['total_trades']}\n"
        f"Total PnL: {pnl_data['total_pnl']:.4f} USDT\n"
        f"Win Rate: {(pnl_data['wins'] / pnl_data['total_trades'] * 100) if pnl_data['total_trades'] > 0 else 0:.1f}%\n"
    )

    keys = await get_api_keys(user["id"])
    if keys:
        try:
            client = BybitClient(keys[0], keys[1])
            bal = client.get_balance()
            if bal:
                text += (
                    f"\nBybit Balance:\n"
                    f"  Total: {bal['total']:.2f} USDT\n"
                    f"  Available: {bal['available']:.2f} USDT\n"
                    f"  Unrealized PnL: {bal['unrealized_pnl']:.4f} USDT\n"
                )
        except Exception:
            pass

    if user["trading_mode"] == "paper":
        text += f"\nPaper Balance: {user['paper_balance']:.2f} USDT"

    await callback.message.edit_text(text, reply_markup=main_menu_kb())
    await callback.answer()


@router.message(Command("status"))
async def cmd_status(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Please /start first")
        return

    open_trades = await get_open_trades(user["id"])
    pnl_data = await get_user_total_pnl(user["id"])

    text = (
        f"Status\n\n"
        f"Mode: {'Paper' if user['trading_mode'] == 'paper' else 'LIVE'}\n"
        f"Bot: {'Active' if user['is_bot_active'] else 'Stopped'}\n"
        f"Open: {len(open_trades)} | Total: {pnl_data['total_trades']}\n"
        f"PnL: {pnl_data['total_pnl']:.4f} USDT\n"
    )

    keys = await get_api_keys(user["id"])
    if keys:
        try:
            client = BybitClient(keys[0], keys[1])
            bal = client.get_balance()
            if bal:
                text += f"Balance: {bal['total']:.2f} USDT\n"
        except Exception:
            pass

    if user["trading_mode"] == "paper":
        text += f"Paper: {user['paper_balance']:.2f} USDT"

    await message.answer(text)


@router.callback_query(F.data == "balance")
async def show_balance(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Please /start first")
        return

    text = "Balance\n\n"

    keys = await get_api_keys(user["id"])
    if keys:
        try:
            client = BybitClient(keys[0], keys[1])
            bal = client.get_balance()
            if bal:
                text += (
                    f"Bybit Account:\n"
                    f"  Total: {bal['total']:.2f} USDT\n"
                    f"  Available: {bal['available']:.2f} USDT\n"
                    f"  Unrealized PnL: {bal['unrealized_pnl']:.4f} USDT\n"
                )
            else:
                text += "Could not fetch Bybit balance\n"
        except Exception:
            text += "Error connecting to Bybit\n"
    else:
        text += "No API keys set. Go to Settings -> API Keys\n"

    if user["trading_mode"] == "paper":
        text += f"\nPaper Balance: {user['paper_balance']:.2f} USDT"

    await callback.message.edit_text(text, reply_markup=main_menu_kb())
    await callback.answer()


@router.message(Command("balance"))
async def cmd_balance(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Please /start first")
        return

    text = ""
    keys = await get_api_keys(user["id"])
    if keys:
        try:
            client = BybitClient(keys[0], keys[1])
            bal = client.get_balance()
            if bal:
                text = f"Balance: {bal['total']:.2f} USDT (available: {bal['available']:.2f})"
            else:
                text = "Could not fetch balance"
        except Exception:
            text = "Error connecting to Bybit"
    else:
        text = "No API keys set"

    if user["trading_mode"] == "paper":
        text += f"\nPaper: {user['paper_balance']:.2f} USDT"

    await message.answer(text)


@router.callback_query(F.data == "start_bot")
async def start_bot(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user or not user["is_registered"]:
        await callback.answer("Complete registration first")
        return

    if user["is_bot_active"]:
        await callback.answer("Bot is already running")
        return

    if user["trading_mode"] == "live":
        keys = await get_api_keys(user["id"])
        if not keys:
            await callback.answer("Set API keys first")
            return

    await update_user(callback.from_user.id, is_bot_active=1)
    await callback.message.edit_text(
        "Bot STARTED!\n\n"
        f"Mode: {'Paper' if user['trading_mode'] == 'paper' else 'LIVE'}\n"
        f"Preset: {user['trader_preset'].capitalize()}\n\n"
        "AI is now analyzing markets and will open positions when conditions are met.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer("Bot started!")


@router.callback_query(F.data == "stop_bot")
async def stop_bot(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Please /start first")
        return

    if not user["is_bot_active"]:
        await callback.answer("Bot is not running")
        return

    await update_user(callback.from_user.id, is_bot_active=0)
    await callback.message.edit_text(
        "Bot STOPPED.\n\nNo new trades will be opened. Existing positions remain open.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer("Bot stopped")


@router.callback_query(F.data == "positions")
async def show_positions(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Please /start first")
        return

    trades = await get_open_trades(user["id"])
    if not trades:
        await callback.message.edit_text("No open positions.", reply_markup=main_menu_kb())
        await callback.answer()
        return

    text = f"Open Positions ({len(trades)}):\n\n"
    for t in trades:
        display = COIN_DISPLAY.get(t["symbol"], t["symbol"])
        paper_tag = "[P] " if t["is_paper"] else ""
        text += (
            f"{paper_tag}{t['side']} {display}\n"
            f"  Entry: {t['entry_price']} | Leverage: {t['leverage']}x\n"
            f"  SL: {t['sl_price']} | TP: {t['tp1_price']}\n"
            f"  Size: {t['position_size_usdt']:.2f} USDT\n"
            f"  Confidence: {t['confidence']:.1f}%\n\n"
        )

    await callback.message.edit_text(text, reply_markup=main_menu_kb())
    await callback.answer()


@router.message(Command("positions"))
async def cmd_positions(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Please /start first")
        return

    trades = await get_open_trades(user["id"])
    if not trades:
        await message.answer("No open positions.")
        return

    text = f"Open Positions ({len(trades)}):\n\n"
    for t in trades:
        display = COIN_DISPLAY.get(t["symbol"], t["symbol"])
        paper_tag = "[P] " if t["is_paper"] else ""
        text += (
            f"{paper_tag}{t['side']} {display}\n"
            f"  Entry: {t['entry_price']} | Lev: {t['leverage']}x\n"
            f"  SL: {t['sl_price']} | TP: {t['tp1_price']}\n\n"
        )

    await message.answer(text)


@router.callback_query(F.data == "history")
async def show_history(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Please /start first")
        return

    trades = await get_trade_history(user["id"], limit=10)
    if not trades:
        await callback.message.edit_text("No trade history.", reply_markup=main_menu_kb())
        await callback.answer()
        return

    text = "Recent Trades:\n\n"
    for t in trades:
        display = COIN_DISPLAY.get(t["symbol"], t["symbol"])
        pnl_sign = "+" if t["pnl"] > 0 else ""
        status = t["status"].upper()
        paper_tag = "[P] " if t["is_paper"] else ""
        text += (
            f"{paper_tag}{t['side']} {display} [{status}]\n"
            f"  Entry: {t['entry_price']}"
        )
        if t["exit_price"]:
            text += f" -> {t['exit_price']}"
        text += f"\n  PnL: {pnl_sign}{t['pnl']:.4f} USDT ({pnl_sign}{t['pnl_percent']:.2f}%)\n\n"

    await callback.message.edit_text(text, reply_markup=main_menu_kb())
    await callback.answer()


@router.message(Command("history"))
async def cmd_history(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Please /start first")
        return

    trades = await get_trade_history(user["id"], limit=10)
    if not trades:
        await message.answer("No trade history.")
        return

    text = "Recent Trades:\n\n"
    for t in trades:
        display = COIN_DISPLAY.get(t["symbol"], t["symbol"])
        pnl_sign = "+" if t["pnl"] > 0 else ""
        text += f"{t['side']} {display}: {pnl_sign}{t['pnl']:.4f} USDT\n"

    await message.answer(text)


@router.callback_query(F.data == "pnl")
async def show_pnl(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Please /start first")
        return

    pnl_data = await get_user_total_pnl(user["id"])
    wins = pnl_data["wins"] or 0
    losses = pnl_data["losses"] or 0
    total = pnl_data["total_trades"] or 0
    wr = (wins / total * 100) if total > 0 else 0
    pnl_sign = "+" if pnl_data["total_pnl"] > 0 else ""

    text = (
        f"PnL Summary\n\n"
        f"Total PnL: {pnl_sign}{pnl_data['total_pnl']:.4f} USDT\n"
        f"Total Trades: {total}\n"
        f"Wins: {wins} | Losses: {losses}\n"
        f"Win Rate: {wr:.1f}%\n"
    )

    await callback.message.edit_text(text, reply_markup=main_menu_kb())
    await callback.answer()


@router.message(Command("pnl"))
async def cmd_pnl(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Please /start first")
        return

    pnl_data = await get_user_total_pnl(user["id"])
    total = pnl_data["total_trades"] or 0
    pnl_sign = "+" if pnl_data["total_pnl"] > 0 else ""

    await message.answer(
        f"PnL: {pnl_sign}{pnl_data['total_pnl']:.4f} USDT | "
        f"Trades: {total} | "
        f"WR: {(pnl_data['wins'] / total * 100) if total > 0 else 0:.1f}%"
    )


@router.callback_query(F.data == "close_all")
async def close_all_positions(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Please /start first")
        return

    trades = await get_open_trades(user["id"])
    if not trades:
        await callback.answer("No open positions")
        return

    from trading.bybit_client import BybitClient
    from trading.risk_manager import RiskManager
    from database.crud import close_trade, update_daily_pnl, get_api_keys
    from trading.engine import get_public_client

    rm = RiskManager()
    closed = 0

    for trade in trades:
        try:
            client = get_public_client()
            ticker = client.get_ticker(trade["symbol"])
            if not ticker:
                continue

            price = ticker["last_price"]
            pnl_data = rm.calculate_pnl(
                trade["side"], trade["entry_price"], price,
                trade["quantity"], trade["leverage"]
            )

            if not trade["is_paper"]:
                keys = await get_api_keys(user["id"])
                if keys:
                    uc = BybitClient(keys[0], keys[1])
                    uc.close_position(trade["symbol"], trade["side"], trade["quantity"])

            await close_trade(trade["id"], price, pnl_data["pnl"], pnl_data["pnl_percent"])
            await update_daily_pnl(user["id"], pnl_data["pnl_percent"], pnl_data["pnl"] > 0)

            if trade["is_paper"]:
                from database.crud import get_user_by_id
                u = await get_user_by_id(user["id"])
                new_bal = u["paper_balance"] + pnl_data["pnl"]
                await update_user(callback.from_user.id, paper_balance=new_bal)

            closed += 1
        except Exception:
            continue

    await callback.message.edit_text(
        f"Closed {closed}/{len(trades)} positions.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer(f"Closed {closed} positions")


@router.callback_query(F.data == "set_api_keys")
async def set_api_keys_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Enter your Bybit API Key:\n\n"
        "(Create at bybit.com -> API Management)\n"
        "(Enable Futures trading, disable withdrawals)"
    )
    await state.set_state(ApiKeyInput.waiting_key)
    await callback.answer()


@router.message(ApiKeyInput.waiting_key)
async def api_key_input(message: Message, state: FSMContext):
    key = message.text.strip()
    if len(key) < 10:
        await message.answer("Invalid key. Try again:")
        return
    await state.update_data(api_key=key)
    await message.delete()
    await message.answer("Got it. Now send API Secret:")
    await state.set_state(ApiKeyInput.waiting_secret)


@router.message(ApiKeyInput.waiting_secret)
async def api_secret_input(message: Message, state: FSMContext):
    secret = message.text.strip()
    if len(secret) < 10:
        await message.answer("Invalid secret. Try again:")
        return

    data = await state.get_data()
    key = data["api_key"]
    await message.delete()

    status_msg = await message.answer("Validating...")

    try:
        client = BybitClient(key, secret)
        bal = client.get_balance()
        if bal is None:
            await status_msg.edit_text("Invalid keys. Try /settings -> API Keys again.")
            await state.clear()
            return

        from database.crud import save_api_keys
        user = await get_user(message.from_user.id)
        await save_api_keys(user["id"], key, secret)
        await update_user(message.from_user.id, is_registered=1)

        await status_msg.edit_text(
            f"API keys saved!\nBalance: {bal['total']:.2f} USDT",
            reply_markup=main_menu_kb(),
        )
    except Exception as e:
        await status_msg.edit_text(f"Error: {e}")

    await state.clear()
