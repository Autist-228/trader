from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⚠️ Принимаю риски, поехали!",
            callback_data="accept_terms")],
    ])


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статус", callback_data="status"),
         InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
        [InlineKeyboardButton(text="▶️ Запустить", callback_data="start_bot"),
         InlineKeyboardButton(text="⏹️ Остановить", callback_data="stop_bot")],
        [InlineKeyboardButton(text="📈 Позиции", callback_data="positions"),
         InlineKeyboardButton(text="📋 История", callback_data="history")],
        [InlineKeyboardButton(text="💵 Прибыль", callback_data="pnl"),
         InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="❌ Закрыть все позиции", callback_data="close_all")],
    ])


def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 AI Стратегия", callback_data="set_trader")],
        [InlineKeyboardButton(text="💱 Режим торговли", callback_data="set_mode")],
        [InlineKeyboardButton(text="🔑 API ключи Bybit", callback_data="set_api_keys")],
        [InlineKeyboardButton(text="🔔 Уведомления", callback_data="set_notifications")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
    ])


def trader_preset_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🟢 Консервативный",
            callback_data="preset_conservative")],
        [InlineKeyboardButton(
            text="🟡 Сбалансированный",
            callback_data="preset_balanced")],
        [InlineKeyboardButton(
            text="🔴 Агрессивный",
            callback_data="preset_aggressive")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings")],
    ])


def mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📝 Демо (виртуальные деньги)",
            callback_data="mode_paper")],
        [InlineKeyboardButton(
            text="💵 Реальная торговля",
            callback_data="mode_live")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings")],
    ])


def confirm_live_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Да, понимаю риски",
            callback_data="confirm_live")],
        [InlineKeyboardButton(
            text="❌ Нет, остаться на демо",
            callback_data="mode_paper")],
    ])


def notifications_kb(settings: dict) -> InlineKeyboardMarkup:
    def icon(val: int) -> str:
        return "✅" if val else "❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{icon(settings.get('notify_new_trade', 1))} Новые сделки",
            callback_data="toggle_notify_new_trade")],
        [InlineKeyboardButton(
            text=f"{icon(settings.get('notify_close_trade', 1))} Закрытие сделок",
            callback_data="toggle_notify_close_trade")],
        [InlineKeyboardButton(
            text=f"{icon(settings.get('notify_sl_hit', 1))} Стоп-лосс",
            callback_data="toggle_notify_sl_hit")],
        [InlineKeyboardButton(
            text=f"{icon(settings.get('notify_daily_report', 1))} Дневной отчёт",
            callback_data="toggle_notify_daily_report")],
        [InlineKeyboardButton(
            text=f"{icon(settings.get('notify_errors', 1))} Ошибки",
            callback_data="toggle_notify_errors")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="settings")],
    ])


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🤖 AI Модель", callback_data="admin_model"),
         InlineKeyboardButton(text="🔄 Переобучить", callback_data="admin_retrain")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
         InlineKeyboardButton(text="📄 Логи", callback_data="admin_logs")],
        [InlineKeyboardButton(text="🔑 Мои API ключи", callback_data="admin_set_api")],
        [InlineKeyboardButton(text="◀️ В меню", callback_data="main_menu")],
    ])


def back_kb(callback: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data=callback)],
    ])
