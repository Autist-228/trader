from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from database.crud import get_user, update_user, get_user_settings, update_user_settings
from ai.presets import apply_preset, get_preset, PRESETS
from bot.keyboards import settings_kb, trader_preset_kb, mode_kb, confirm_live_kb, notifications_kb, main_menu_kb

router = Router()

RU_LABELS = {
    'conservative': 'Консервативный',
    'balanced': 'Сбалансированный',
    'aggressive': 'Агрессивный',
}



@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала нажмите /start")
        return

    settings = await get_user_settings(user["id"])
    preset = get_preset(user["trader_preset"])

    ru_name = RU_LABELS.get(user['trader_preset'], user['trader_preset'])
    text = (
        f"⚙️ Настройки\n\n"
        f"🤖 Трейдер: {ru_name}\n"
        f"📈 Режим: {'Демо' if user['trading_mode'] == 'paper' else 'РЕАЛЬНЫЙ'}\n\n"
        f"⚖️ Риск: {preset['risk']}\n"
        f"⚙️ Плечо: {settings['leverage_min']}-{settings['leverage_max']}x\n"
        f"📦 Размер позиции: {settings['position_size_min']}-{settings['position_size_max']}%\n"
        f"🛡 SL: {settings['sl_min']}-{settings['sl_max']}%\n"
        f"🎯 TP: {settings['tp_min']}-{settings['tp_max']}%\n"
        f"🚫 Макс. дневная просадка: {settings['max_daily_loss']}%\n"
        f"📊 Макс. позиций: {settings['max_positions']}\n"
        f"🤖 Мин. уверенность AI: {settings['min_confidence']}%\n"
        f"🪙 Монеты: {', '.join(settings['coins'])}\n"
        f"⏱ Таймфреймы: {', '.join(preset['timeframes'])}\n"
    )

    await callback.message.edit_text(text, reply_markup=settings_kb())
    await callback.answer()


@router.callback_query(F.data == "set_trader")
async def set_trader(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    current = user["trader_preset"]

    text = "Выберите AI трейдера:\n\n"
    for key, p in PRESETS.items():
        marker = " ← текущая" if key == current else ""
        dot = "🟢" if key == "conservative" else ("🟡" if key == "balanced" else "🔴")
        ru = RU_LABELS.get(key, p['name'])
        text += (
            f"{dot} {ru}{marker}\n"
            f"• Риск: {p['risk']}\n"
            f"• Плечо: {p['leverage_min']}-{p['leverage_max']}x\n"
            f"• Размер позиции: {p['position_size_min']}-{p['position_size_max']}%\n"
            f"• SL/TP: {p['sl_min']}-{p['sl_max']}% / {p['tp_min']}-{p['tp_max']}%\n"
            f"• Мин. уверенность: {p['min_confidence']}%+\n"
            f"• Монеты: {', '.join(p['coins'])}\n"
            f"• Таймфреймы: {', '.join(p['timeframes'])}\n\n"
        )

    await callback.message.edit_text(text, reply_markup=trader_preset_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("preset_"))
async def select_preset(callback: CallbackQuery):
    preset_name = callback.data.replace("preset_", "")
    if preset_name not in PRESETS:
        await callback.answer("Неверный пресет")
        return

    user = await get_user(callback.from_user.id)
    preset_settings = apply_preset(preset_name)

    await update_user(callback.from_user.id, trader_preset=preset_name)
    await update_user_settings(user["id"], **preset_settings)

    preset = get_preset(preset_name)
    await callback.message.edit_text(
        f"AI трейдер установлен: {preset['name']}!\n\n"
        f"Плечо: {preset['leverage_min']}-{preset['leverage_max']}x\n"
        f"Размер позиции: {preset['position_size_min']}-{preset['position_size_max']}%\n"
        f"SL: {preset['sl_min']}-{preset['sl_max']}%\n"
        f"TP: {preset['tp_min']}-{preset['tp_max']}%\n"
        f"Макс. дневная просадка: {preset['max_daily_loss']}%\n"
        f"Макс. позиций: {preset['max_positions']}\n"
        f"Мин. уверенность: {preset['min_confidence']}%\n"
        f"Монеты: {', '.join(preset['coins'])}",
        reply_markup=settings_kb(),
    )
    await callback.answer("Пресет применён!")


@router.callback_query(F.data == "about_strategies")
async def about_strategies(callback: CallbackQuery):
    lines = []
    def card(key: str, p: dict) -> str:
        dot = "🟢" if key == "conservative" else ("🟡" if key == "balanced" else "🔴")
        ru = RU_LABELS.get(key, p['name'])
        tips = {
            'conservative': "• Минимальные просадки, ночной/фоновый режим, тест рынка",
            'balanced': "• Ежедневная торговля, средний риск/доходность",
            'aggressive': "• Быстрые движения/волатильность, раскрутка депозита (высокий риск)",
        }
        return (
            f"{dot} {ru}\n"
            f"• Риск: {p['risk']}\n"
            f"• Плечо: {p['leverage_min']}-{p['leverage_max']}x\n"
            f"• Размер позиции: {p['position_size_min']}-{p['position_size_max']}%\n"
            f"• SL/TP: {p['sl_min']}-{p['sl_max']}% / {p['tp_min']}-{p['tp_max']}%\n"
            f"• Мин. уверенность: {p['min_confidence']}%+\n"
            f"• Монеты: {', '.join(p['coins'])}\n"
            f"• Таймфреймы: {', '.join(p['timeframes'])}\n"
            f"• Когда включать: {tips.get(key, '')}\n"
        )

    lines.append("ℹ️ О стратегиях\n")
    for k, p in PRESETS.items():
        lines.append(card(k, p) + "\n")

    await callback.message.edit_text("\n".join(lines), reply_markup=settings_kb())
    await callback.answer()


@router.callback_query(F.data == "set_mode")
async def set_mode(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    current = user["trading_mode"]

    await callback.message.edit_text(
        f"Текущий режим: {'Демо' if current == 'paper' else 'РЕАЛЬНЫЙ'}\n\n"
        f"Демо: реальные цены, без реальных денег\n"
        f"Реальный: реальные ордера на вашем аккаунте Bybit\n\n"
        f"Выберите режим:",
        reply_markup=mode_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "mode_paper")
async def mode_paper(callback: CallbackQuery):
    await update_user(callback.from_user.id, trading_mode="paper")
    await callback.message.edit_text(
        "Режим установлен: Демо\n\n"
        "Бот будет симулировать сделки по реальным ценам.\n"
        "Реальные деньги использоваться не будут.",
        reply_markup=settings_kb(),
    )
    await callback.answer("Демо-режим активирован")


@router.callback_query(F.data == "mode_live")
async def mode_live(callback: CallbackQuery):
    await callback.message.edit_text(
        "ВНИМАНИЕ: РЕАЛЬНЫЙ РЕЖИМ\n\n"
        "Будут использованы РЕАЛЬНЫЕ деньги с вашего аккаунта Bybit.\n"
        "Вы можете потерять весь депозит.\n\n"
        "Вы уверены?",
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
            "Сначала настройте API ключи, прежде чем переходить в реальный режим.",
            reply_markup=settings_kb(),
        )
        await callback.answer("Сначала настройте API ключи")
        return

    await update_user(callback.from_user.id, trading_mode="live")
    await callback.message.edit_text(
        "РЕАЛЬНЫЙ РЕЖИМ АКТИВИРОВАН\n\n"
        "Бот теперь будет совершать реальные сделки на вашем аккаунте Bybit.\n"
        "Будьте осторожны и контролируйте позиции.",
        reply_markup=settings_kb(),
    )
    await callback.answer("Реальный режим активирован")


@router.callback_query(F.data == "set_notifications")
async def set_notifications(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    settings = await get_user_settings(user["id"])

    await callback.message.edit_text(
        "Уведомления:\n\nПереключайте нужные уведомления:",
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
        "Уведомления:\n\nПереключайте нужные уведомления:",
        reply_markup=notifications_kb(settings),
    )
    await callback.answer(f"{'Включено' if new_val else 'Выключено'}")
