from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from database.crud import get_user, update_user, get_user_settings, update_user_settings
from ai.presets import apply_preset, get_preset, PRESETS
from bot.keyboards import settings_kb, trader_preset_kb, mode_kb, confirm_live_kb, notifications_kb, main_menu_kb

router = Router()


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Please /start first")
        return

    settings = await get_user_settings(user["id"])
    preset = get_preset(user["trader_preset"])

    text = (
        f"Settings\n\n"
        f"AI Trader: {preset['emoji']} {preset['name']}\n"
        f"Mode: {'Paper' if user['trading_mode'] == 'paper' else 'LIVE'}\n"
        f"Leverage: {settings['leverage_min']}-{settings['leverage_max']}x\n"
        f"Position: {settings['position_size_min']}-{settings['position_size_max']}%\n"
        f"SL: {settings['sl_min']}-{settings['sl_max']}%\n"
        f"TP: {settings['tp_min']}-{settings['tp_max']}%\n"
        f"Max Daily Loss: {settings['max_daily_loss']}%\n"
        f"Max Positions: {settings['max_positions']}\n"
        f"Min Confidence: {settings['min_confidence']}%\n"
        f"Coins: {', '.join(settings['coins'])}\n"
    )

    await callback.message.edit_text(text, reply_markup=settings_kb())
    await callback.answer()


@router.callback_query(F.data == "set_trader")
async def set_trader(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    current = user["trader_preset"]

    text = "Select AI Trader:\n\n"
    for key, p in PRESETS.items():
        marker = " <- current" if key == current else ""
        text += (
            f"{p['emoji']} {p['name']}{marker}\n"
            f"  Leverage: {p['leverage_min']}-{p['leverage_max']}x\n"
            f"  Position: {p['position_size_min']}-{p['position_size_max']}%\n"
            f"  Confidence: {p['min_confidence']}%+\n"
            f"  Coins: {len(p['coins'])}\n\n"
        )

    await callback.message.edit_text(text, reply_markup=trader_preset_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("preset_"))
async def select_preset(callback: CallbackQuery):
    preset_name = callback.data.replace("preset_", "")
    if preset_name not in PRESETS:
        await callback.answer("Invalid preset")
        return

    user = await get_user(callback.from_user.id)
    preset_settings = apply_preset(preset_name)

    await update_user(callback.from_user.id, trader_preset=preset_name)
    await update_user_settings(user["id"], **preset_settings)

    preset = get_preset(preset_name)
    await callback.message.edit_text(
        f"AI Trader set to {preset['emoji']} {preset['name']}!\n\n"
        f"Leverage: {preset['leverage_min']}-{preset['leverage_max']}x\n"
        f"Position: {preset['position_size_min']}-{preset['position_size_max']}%\n"
        f"SL: {preset['sl_min']}-{preset['sl_max']}%\n"
        f"TP: {preset['tp_min']}-{preset['tp_max']}%\n"
        f"Max Daily Loss: {preset['max_daily_loss']}%\n"
        f"Max Positions: {preset['max_positions']}\n"
        f"Min Confidence: {preset['min_confidence']}%\n"
        f"Coins: {', '.join(preset['coins'])}",
        reply_markup=settings_kb(),
    )
    await callback.answer("Preset applied!")


@router.callback_query(F.data == "set_mode")
async def set_mode(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    current = user["trading_mode"]

    await callback.message.edit_text(
        f"Current mode: {'Paper Trading' if current == 'paper' else 'LIVE Trading'}\n\n"
        f"Paper Trading: Uses real prices but no real money\n"
        f"Live Trading: Real orders on your Bybit account\n\n"
        f"Select mode:",
        reply_markup=mode_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "mode_paper")
async def mode_paper(callback: CallbackQuery):
    await update_user(callback.from_user.id, trading_mode="paper")
    await callback.message.edit_text(
        "Mode set to Paper Trading\n\n"
        "The bot will simulate trades using real market prices.\n"
        "No real money will be used.",
        reply_markup=settings_kb(),
    )
    await callback.answer("Paper mode activated")


@router.callback_query(F.data == "mode_live")
async def mode_live(callback: CallbackQuery):
    await callback.message.edit_text(
        "WARNING: LIVE TRADING MODE\n\n"
        "This will use REAL money from your Bybit account.\n"
        "You can lose your entire deposit.\n\n"
        "Are you sure?",
        reply_markup=confirm_live_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_live")
async def confirm_live(callback: CallbackQuery):
    from database.crud import get_api_keys
    user = await get_user(callback.from_user.id)
    keys = await get_api_keys(user["id"])

    if not keys:
        await callback.message.edit_text(
            "You need to set up API keys first before switching to Live mode.",
            reply_markup=settings_kb(),
        )
        await callback.answer("Set up API keys first")
        return

    await update_user(callback.from_user.id, trading_mode="live")
    await callback.message.edit_text(
        "LIVE MODE ACTIVATED\n\n"
        "The bot will now execute real trades on your Bybit account.\n"
        "Be careful and monitor your positions.",
        reply_markup=settings_kb(),
    )
    await callback.answer("Live mode activated!")


@router.callback_query(F.data == "set_notifications")
async def set_notifications(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    settings = await get_user_settings(user["id"])

    await callback.message.edit_text(
        "Notification Settings:\n\nToggle notifications on/off:",
        reply_markup=notifications_kb(settings),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_"))
async def toggle_notification(callback: CallbackQuery):
    field = callback.data.replace("toggle_", "")
    user = await get_user(callback.from_user.id)
    settings = await get_user_settings(user["id"])

    current = settings.get(field, 1)
    new_val = 0 if current else 1
    await update_user_settings(user["id"], **{field: new_val})

    settings[field] = new_val
    await callback.message.edit_text(
        "Notification Settings:\n\nToggle notifications on/off:",
        reply_markup=notifications_kb(settings),
    )
    await callback.answer(f"{'Enabled' if new_val else 'Disabled'}")
