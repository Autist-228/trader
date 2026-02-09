from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.crud import (
    get_user, get_all_users, get_platform_stats, get_user_total_pnl,
    get_api_keys, save_api_keys, update_user, get_open_trades, log_event,
)
from trading.bybit_client import BybitClient
from bot.keyboards import admin_kb, main_menu_kb, back_kb
from config import ADMIN_TELEGRAM_ID

router = Router()


class AdminApiKeys(StatesGroup):
    waiting_key = State()
    waiting_secret = State()


class BroadcastState(StatesGroup):
    waiting_message = State()


def is_admin(telegram_id: int) -> bool:
    return telegram_id == ADMIN_TELEGRAM_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Access denied.")
        return

    stats = await get_platform_stats()
    text = (
        f"Admin Panel\n\n"
        f"Users: {stats['total_users']}\n"
        f"Active Bots: {stats['active_bots']}\n"
        f"Total Trades: {stats['total_trades']}\n"
        f"Platform PnL: {stats['total_pnl']:.4f} USDT\n"
        f"Win Rate: {stats['win_rate']:.1f}%\n"
        f"Today Trades: {stats['today_trades']}\n"
    )

    await message.answer(text, reply_markup=admin_kb())


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied")
        return

    users = await get_all_users()
    if not users:
        await callback.message.edit_text("No users yet.", reply_markup=admin_kb())
        await callback.answer()
        return

    text = f"Users ({len(users)}):\n\n"
    for u in users:
        pnl = await get_user_total_pnl(u["id"])
        admin_tag = " [ADMIN]" if u["is_admin"] else ""
        bot_status = "ON" if u["is_bot_active"] else "OFF"
        mode = "P" if u["trading_mode"] == "paper" else "L"
        pnl_sign = "+" if pnl["total_pnl"] > 0 else ""

        text += (
            f"#{u['id']} @{u['username'] or 'N/A'}{admin_tag}\n"
            f"  {u['first_name'] or ''} | TG: {u['telegram_id']}\n"
            f"  Mode: {mode} | Bot: {bot_status} | Preset: {u['trader_preset']}\n"
            f"  PnL: {pnl_sign}{pnl['total_pnl']:.4f} | Trades: {pnl['total_trades']}\n\n"
        )

    if len(text) > 4000:
        text = text[:3900] + "\n\n... (truncated)"

    await callback.message.edit_text(text, reply_markup=admin_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied")
        return

    stats = await get_platform_stats()
    users = await get_all_users()

    best_user = None
    worst_user = None
    best_pnl = float("-inf")
    worst_pnl = float("inf")

    for u in users:
        pnl = await get_user_total_pnl(u["id"])
        if pnl["total_pnl"] > best_pnl:
            best_pnl = pnl["total_pnl"]
            best_user = u
        if pnl["total_pnl"] < worst_pnl:
            worst_pnl = pnl["total_pnl"]
            worst_user = u

    text = (
        f"Platform Statistics\n\n"
        f"Total Users: {stats['total_users']}\n"
        f"Active Bots: {stats['active_bots']}\n"
        f"Total Trades: {stats['total_trades']}\n"
        f"Today Trades: {stats['today_trades']}\n"
        f"Platform PnL: {stats['total_pnl']:.4f} USDT\n"
        f"Win Rate: {stats['win_rate']:.1f}%\n"
    )

    if best_user:
        text += f"\nBest: @{best_user['username'] or 'N/A'} ({best_pnl:+.4f} USDT)"
    if worst_user:
        text += f"\nWorst: @{worst_user['username'] or 'N/A'} ({worst_pnl:+.4f} USDT)"

    await callback.message.edit_text(text, reply_markup=admin_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_model")
async def admin_model(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied")
        return

    from ai.model import AIModel
    model = AIModel()
    status = model.get_status()

    text = (
        f"AI Model Status\n\n"
        f"Type: {status['model_type']}\n"
        f"Trained: {'Yes' if status['is_trained'] else 'No'}\n"
        f"Last Train: {status['last_train_time'] or 'Never'}\n"
    )

    await callback.message.edit_text(text, reply_markup=admin_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_retrain")
async def admin_retrain(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied")
        return

    await callback.message.edit_text("Retraining model... This may take a minute.")
    await callback.answer()

    try:
        from trading.engine import TradingEngine
        from ai.model import AIModel
        model = AIModel()
        engine = TradingEngine(model)
        success = await engine.train_model()

        if success:
            await callback.message.edit_text(
                "Model retrained successfully!",
                reply_markup=admin_kb(),
            )
            await log_event("INFO", "admin", "Model retrained by admin")
        else:
            await callback.message.edit_text(
                "Training failed. Not enough data or error occurred.",
                reply_markup=admin_kb(),
            )
    except Exception as e:
        await callback.message.edit_text(
            f"Training error: {str(e)}",
            reply_markup=admin_kb(),
        )


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied")
        return

    await callback.message.edit_text("Send the message to broadcast to all users:")
    await state.set_state(BroadcastState.waiting_message)
    await callback.answer()


@router.message(BroadcastState.waiting_message)
async def admin_broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    broadcast_text = message.text
    users = await get_all_users()
    sent = 0
    failed = 0

    for u in users:
        try:
            await message.bot.send_message(
                u["telegram_id"],
                f"[Broadcast from Admin]\n\n{broadcast_text}",
            )
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"Broadcast sent!\nDelivered: {sent}\nFailed: {failed}",
        reply_markup=admin_kb(),
    )
    await state.clear()


@router.callback_query(F.data == "admin_logs")
async def admin_logs(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied")
        return

    from database.models import get_db
    db = await get_db()
    try:
        rows = await db.execute(
            "SELECT * FROM bot_logs ORDER BY created_at DESC LIMIT 15"
        )
        logs = await rows.fetchall()
    finally:
        await db.close()

    if not logs:
        await callback.message.edit_text("No logs yet.", reply_markup=admin_kb())
        await callback.answer()
        return

    text = "Recent Logs:\n\n"
    for log in logs:
        log = dict(log)
        text += f"[{log['level']}] {log['module']}: {log['message']}\n{log['created_at']}\n\n"

    if len(text) > 4000:
        text = text[:3900] + "\n\n... (truncated)"

    await callback.message.edit_text(text, reply_markup=admin_kb())
    await callback.answer()


@router.callback_query(F.data == "admin_set_api")
async def admin_set_api(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Access denied")
        return

    await callback.message.edit_text("Send your Bybit API Key:")
    await state.set_state(AdminApiKeys.waiting_key)
    await callback.answer()


@router.message(AdminApiKeys.waiting_key)
async def admin_api_key(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    key = message.text.strip()
    await state.update_data(api_key=key)
    await message.delete()
    await message.answer("Got it. Now send API Secret:")
    await state.set_state(AdminApiKeys.waiting_secret)


@router.message(AdminApiKeys.waiting_secret)
async def admin_api_secret(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return

    secret = message.text.strip()
    data = await state.get_data()
    key = data["api_key"]
    await message.delete()

    status_msg = await message.answer("Validating...")

    try:
        client = BybitClient(key, secret)
        bal = client.get_balance()
        if bal is None:
            await status_msg.edit_text("Invalid keys.", reply_markup=admin_kb())
            await state.clear()
            return

        user = await get_user(message.from_user.id)
        if not user:
            from database.crud import create_user
            await create_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                is_admin=True,
            )
            user = await get_user(message.from_user.id)

        await save_api_keys(user["id"], key, secret)
        await update_user(message.from_user.id, is_registered=1)

        await status_msg.edit_text(
            f"Admin API keys saved!\nBalance: {bal['total']:.2f} USDT",
            reply_markup=admin_kb(),
        )
        await log_event("INFO", "admin", "Admin API keys updated")
    except Exception as e:
        await status_msg.edit_text(f"Error: {e}", reply_markup=admin_kb())

    await state.clear()
