from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.crud import create_user, get_user, update_user, save_api_keys, get_api_keys, get_user_settings
from trading.bybit_client import BybitClient
from bot.keyboards import start_kb, main_menu_kb, settings_kb
from config import ADMIN_TELEGRAM_ID

router = Router()


class ApiKeyStates(StatesGroup):
    waiting_api_key = State()
    waiting_api_secret = State()


@router.message(Command("start"))
async def cmd_start(message: Message):
    telegram_id = message.from_user.id
    user = await get_user(telegram_id)

    if user and user["is_registered"]:
        text = (
            f"Welcome back, {message.from_user.first_name}!\n\n"
            f"Mode: {'Paper' if user['trading_mode'] == 'paper' else 'LIVE'}\n"
            f"Preset: {user['trader_preset'].capitalize()}\n"
            f"Bot: {'Active' if user['is_bot_active'] else 'Stopped'}\n"
        )

        keys = await get_api_keys(user["id"])
        if keys:
            try:
                client = BybitClient(keys[0], keys[1])
                bal = client.get_balance()
                if bal:
                    text += f"\nBalance: {bal['total']:.2f} USDT"
            except Exception:
                pass

        if user["trading_mode"] == "paper":
            text += f"\nPaper Balance: {user['paper_balance']:.2f} USDT"

        await message.answer(text, reply_markup=main_menu_kb())
        return

    is_admin = telegram_id == ADMIN_TELEGRAM_ID
    if is_admin and not user:
        await create_user(
            telegram_id=telegram_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            is_admin=True,
        )
        await message.answer(
            "Welcome, Admin!\n\n"
            "You are registered as the platform administrator.\n"
            "Use /admin for admin panel.\n\n"
            "Set up your Bybit API keys to start trading.",
            reply_markup=main_menu_kb(),
        )
        return

    await message.answer(
        "Welcome to AI Trading Bot!\n\n"
        "This bot uses AI (LightGBM) to trade crypto futures on Bybit.\n\n"
        "DISCLAIMER:\n"
        "Trading involves significant risk. You can lose all your money. "
        "This bot does NOT guarantee profits. Past performance does not "
        "indicate future results. Only trade with money you can afford to lose.\n\n"
        "By pressing the button below, you accept all risks.",
        reply_markup=start_kb(),
    )


@router.callback_query(F.data == "accept_terms")
async def accept_terms(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    user = await get_user(telegram_id)
    if not user:
        await create_user(
            telegram_id=telegram_id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
        )

    await callback.message.edit_text(
        "Great! Now let's set up your Bybit API keys.\n\n"
        "1. Go to bybit.com -> API Management\n"
        "2. Create a new API key with Futures trading permission\n"
        "3. DO NOT enable withdrawal permission\n\n"
        "Send me your API Key:"
    )
    await state.set_state(ApiKeyStates.waiting_api_key)
    await callback.answer()


@router.message(ApiKeyStates.waiting_api_key)
async def receive_api_key(message: Message, state: FSMContext):
    api_key = message.text.strip()
    if len(api_key) < 10:
        await message.answer("Invalid API key. Please try again:")
        return

    await state.update_data(api_key=api_key)
    await message.delete()
    await message.answer("API Key received. Now send me your API Secret:")
    await state.set_state(ApiKeyStates.waiting_api_secret)


@router.message(ApiKeyStates.waiting_api_secret)
async def receive_api_secret(message: Message, state: FSMContext):
    api_secret = message.text.strip()
    if len(api_secret) < 10:
        await message.answer("Invalid API secret. Please try again:")
        return

    data = await state.get_data()
    api_key = data["api_key"]

    await message.delete()
    status_msg = await message.answer("Validating keys...")

    try:
        client = BybitClient(api_key, api_secret)
        bal = client.get_balance()
        if bal is None:
            await status_msg.edit_text(
                "API keys are invalid or don't have correct permissions.\n"
                "Please check and try again.\n\nSend me your API Key:"
            )
            await state.set_state(ApiKeyStates.waiting_api_key)
            return

        user = await get_user(message.from_user.id)
        await save_api_keys(user["id"], api_key, api_secret)
        await update_user(message.from_user.id, is_registered=1)

        await status_msg.edit_text(
            f"API keys validated!\n"
            f"Balance: {bal['total']:.2f} USDT\n\n"
            f"Your account is ready. Choose your settings:",
            reply_markup=settings_kb(),
        )
    except Exception as e:
        await status_msg.edit_text(
            f"Error validating keys: {str(e)}\n\nSend me your API Key:"
        )
        await state.set_state(ApiKeyStates.waiting_api_key)

    await state.clear()


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Please /start first.")
        return

    text = (
        f"Main Menu\n\n"
        f"Mode: {'Paper' if user['trading_mode'] == 'paper' else 'LIVE'}\n"
        f"Preset: {user['trader_preset'].capitalize()}\n"
        f"Bot: {'Active' if user['is_bot_active'] else 'Stopped'}\n"
    )

    keys = await get_api_keys(user["id"])
    if keys:
        try:
            client = BybitClient(keys[0], keys[1])
            bal = client.get_balance()
            if bal:
                text += f"\nBybit Balance: {bal['total']:.2f} USDT"
        except Exception:
            pass

    if user["trading_mode"] == "paper":
        text += f"\nPaper Balance: {user['paper_balance']:.2f} USDT"

    await callback.message.edit_text(text, reply_markup=main_menu_kb())
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Commands:\n"
        "/start - Main menu\n"
        "/status - Current status\n"
        "/balance - Check balance\n"
        "/positions - Open positions\n"
        "/history - Trade history\n"
        "/pnl - Profit/Loss summary\n"
        "/settings - Bot settings\n"
        "/help - This message\n"
    )
