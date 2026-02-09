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
        preset_names = {'conservative': 'Консервативный', 'balanced': 'Сбалансированный', 'aggressive': 'Агрессивный'}
        text = (
            f"С возвращением, {message.from_user.first_name}!\n\n"
            f"Режим: {'Демо' if user['trading_mode'] == 'paper' else 'РЕАЛЬНЫЙ'}\n"
            f"Стратегия: {preset_names.get(user['trader_preset'], user['trader_preset'])}\n"
            f"Бот: {'Работает' if user['is_bot_active'] else 'Остановлен'}\n"
        )

        keys = await get_api_keys(user["id"])
        if keys:
            try:
                client = BybitClient(keys[0], keys[1])
                bal = client.get_balance()
                if bal:
                    text += f"\nБаланс: {bal['total']:.2f} USDT"
            except Exception:
                pass

        if user["trading_mode"] == "paper":
            text += f"\nДемо-баланс: {user['paper_balance']:.2f} USDT"

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
            "Добро пожаловать, Админ!\n\n"
            "Ты зарегистрирован как администратор платформы.\n"
            "Нажми /admin для админ-панели.\n\n"
            "Настрой API ключи Bybit чтобы начать торговлю.",
            reply_markup=main_menu_kb(),
        )
        return

    await message.answer(
        "AI Trading Bot\n\n"
        "Этот бот использует AI (LightGBM) для торговли крипто-фьючерсами на Bybit.\n\n"
        "ВНИМАНИЕ:\n"
        "Торговля связана с риском. Вы можете потерять все деньги. "
        "Бот НЕ гарантирует прибыль. Прошлые результаты не "
        "гарантируют будущую прибыль. Торгуйте только теми средствами, "
        "которые можете позволить себе потерять.\n\n"
        "Нажмите кнопку ниже, если принимаете риски.",
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
        "Отлично! Теперь настроим API ключи Bybit.\n\n"
        "1. Зайди на bybit.com -> Управление API\n"
        "2. Создай новый API ключ с разрешением на фьючерсы\n"
        "3. НЕ включай разрешение на вывод средств\n\n"
        "Отправь мне свой API Key:"
    )
    await state.set_state(ApiKeyStates.waiting_api_key)
    await callback.answer()


@router.message(ApiKeyStates.waiting_api_key)
async def receive_api_key(message: Message, state: FSMContext):
    api_key = message.text.strip()
    if len(api_key) < 10:
        await message.answer("Неверный API ключ. Попробуй ещё:")
        return

    await state.update_data(api_key=api_key)
    await message.delete()
    await message.answer("API Key получен. Теперь отправь API Secret:")
    await state.set_state(ApiKeyStates.waiting_api_secret)


@router.message(ApiKeyStates.waiting_api_secret)
async def receive_api_secret(message: Message, state: FSMContext):
    api_secret = message.text.strip()
    if len(api_secret) < 10:
        await message.answer("Неверный API secret. Попробуй ещё:")
        return

    data = await state.get_data()
    api_key = data["api_key"]

    await message.delete()
    status_msg = await message.answer("Проверяю ключи...")

    try:
        client = BybitClient(api_key, api_secret)
        bal = client.get_balance()
        if bal is None:
            await status_msg.edit_text(
                "API ключи неверные или нет нужных разрешений.\n"
                "Проверь и попробуй снова.\n\nОтправь API Key:"
            )
            await state.set_state(ApiKeyStates.waiting_api_key)
            return

        user = await get_user(message.from_user.id)
        await save_api_keys(user["id"], api_key, api_secret)
        await update_user(message.from_user.id, is_registered=1)

        await status_msg.edit_text(
            f"API ключи проверены!\n"
            f"Баланс: {bal['total']:.2f} USDT\n\n"
            f"Аккаунт готов. Выбери настройки:",
            reply_markup=settings_kb(),
        )
    except Exception as e:
        await status_msg.edit_text(
            f"Ошибка проверки ключей: {str(e)}\n\nОтправь API Key:"
        )
        await state.set_state(ApiKeyStates.waiting_api_key)

    await state.clear()


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("Нажми /start для начала.")
        return

    preset_names = {'conservative': 'Консервативный', 'balanced': 'Сбалансированный', 'aggressive': 'Агрессивный'}
    text = (
        f"Главное меню\n\n"
        f"Режим: {'Демо' if user['trading_mode'] == 'paper' else 'РЕАЛЬНЫЙ'}\n"
        f"Стратегия: {preset_names.get(user['trader_preset'], user['trader_preset'])}\n"
        f"Бот: {'Работает' if user['is_bot_active'] else 'Остановлен'}\n"
    )

    keys = await get_api_keys(user["id"])
    if keys:
        try:
            client = BybitClient(keys[0], keys[1])
            bal = client.get_balance()
            if bal:
                text += f"\nБаланс Bybit: {bal['total']:.2f} USDT"
        except Exception:
            pass

    if user["trading_mode"] == "paper":
        text += f"\nPaper Balance: {user['paper_balance']:.2f} USDT"

    await callback.message.edit_text(text, reply_markup=main_menu_kb())
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/start - Главное меню\n"
        "/status - Текущий статус\n"
        "/balance - Проверить баланс\n"
        "/positions - Открытые позиции\n"
        "/history - История сделок\n"
        "/pnl - Прибыль/убыток\n"
        "/settings - Настройки бота\n"
        "/help - Это сообщение\n"
    )
