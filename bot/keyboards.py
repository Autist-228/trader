from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="I accept the risks", callback_data="accept_terms")],
    ])


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Status", callback_data="status"),
         InlineKeyboardButton(text="Balance", callback_data="balance")],
        [InlineKeyboardButton(text="Start Bot", callback_data="start_bot"),
         InlineKeyboardButton(text="Stop Bot", callback_data="stop_bot")],
        [InlineKeyboardButton(text="Positions", callback_data="positions"),
         InlineKeyboardButton(text="History", callback_data="history")],
        [InlineKeyboardButton(text="PnL", callback_data="pnl"),
         InlineKeyboardButton(text="Settings", callback_data="settings")],
        [InlineKeyboardButton(text="Close All", callback_data="close_all")],
    ])


def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="AI Trader Preset", callback_data="set_trader")],
        [InlineKeyboardButton(text="Trading Mode", callback_data="set_mode")],
        [InlineKeyboardButton(text="API Keys", callback_data="set_api_keys")],
        [InlineKeyboardButton(text="Notifications", callback_data="set_notifications")],
        [InlineKeyboardButton(text="Back", callback_data="main_menu")],
    ])


def trader_preset_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Conservative (Low Risk)", callback_data="preset_conservative")],
        [InlineKeyboardButton(text="Balanced (Medium Risk)", callback_data="preset_balanced")],
        [InlineKeyboardButton(text="Aggressive (High Risk)", callback_data="preset_aggressive")],
        [InlineKeyboardButton(text="Back", callback_data="settings")],
    ])


def mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Paper Trading (Simulator)", callback_data="mode_paper")],
        [InlineKeyboardButton(text="Live Trading (Real Money)", callback_data="mode_live")],
        [InlineKeyboardButton(text="Back", callback_data="settings")],
    ])


def confirm_live_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Yes, I understand the risks", callback_data="confirm_live")],
        [InlineKeyboardButton(text="No, stay on Paper", callback_data="mode_paper")],
    ])


def notifications_kb(settings: dict) -> InlineKeyboardMarkup:
    def icon(val: int) -> str:
        return "ON" if val else "OFF"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"New Trades: {icon(settings.get('notify_new_trade', 1))}",
            callback_data="toggle_notify_new_trade")],
        [InlineKeyboardButton(
            text=f"Close Trades: {icon(settings.get('notify_close_trade', 1))}",
            callback_data="toggle_notify_close_trade")],
        [InlineKeyboardButton(
            text=f"SL Hit: {icon(settings.get('notify_sl_hit', 1))}",
            callback_data="toggle_notify_sl_hit")],
        [InlineKeyboardButton(
            text=f"Daily Report: {icon(settings.get('notify_daily_report', 1))}",
            callback_data="toggle_notify_daily_report")],
        [InlineKeyboardButton(
            text=f"Errors: {icon(settings.get('notify_errors', 1))}",
            callback_data="toggle_notify_errors")],
        [InlineKeyboardButton(text="Back", callback_data="settings")],
    ])


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Users", callback_data="admin_users"),
         InlineKeyboardButton(text="Stats", callback_data="admin_stats")],
        [InlineKeyboardButton(text="Model Status", callback_data="admin_model"),
         InlineKeyboardButton(text="Retrain", callback_data="admin_retrain")],
        [InlineKeyboardButton(text="Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton(text="Logs", callback_data="admin_logs")],
        [InlineKeyboardButton(text="Set My API Keys", callback_data="admin_set_api")],
        [InlineKeyboardButton(text="Back to Menu", callback_data="main_menu")],
    ])


def back_kb(callback: str = "main_menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Back", callback_data=callback)],
    ])
