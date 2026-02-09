import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_ID
from database.models import init_db
from database.crud import create_user, get_user, log_event
from ai.model import AIModel
from trading.engine import TradingEngine
from bot.handlers import start, settings, trading, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def notify_user(telegram_id: int, message: str):
    bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
    try:
        await bot.send_message(telegram_id, message)
    finally:
        await bot.session.close()


async def auto_retrain(engine: TradingEngine, interval: int = 86400):
    while True:
        try:
            logger.info("Starting auto-retrain...")
            success = await engine.train_model()
            if success:
                logger.info("Auto-retrain completed")
                await log_event("INFO", "retrain", "Auto-retrain completed")
            else:
                logger.warning("Auto-retrain failed")
                await log_event("WARNING", "retrain", "Auto-retrain failed")
        except Exception as e:
            logger.error(f"Auto-retrain error: {e}")
        await asyncio.sleep(interval)


async def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    await init_db()
    logger.info("Database initialized")

    if ADMIN_TELEGRAM_ID:
        existing = await get_user(ADMIN_TELEGRAM_ID)
        if not existing:
            await create_user(
                telegram_id=ADMIN_TELEGRAM_ID,
                username="admin",
                first_name="Admin",
                is_admin=True,
            )
            logger.info(f"Admin user created: {ADMIN_TELEGRAM_ID}")

    ai_model = AIModel()
    engine = TradingEngine(ai_model, notify_callback=notify_user)

    logger.info("Training AI model on initial data...")
    await engine.train_model()

    bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(settings.router)
    dp.include_router(trading.router)
    dp.include_router(admin.router)

    trading_task = asyncio.create_task(engine.start(interval=60))
    retrain_task = asyncio.create_task(auto_retrain(engine, interval=86400))

    logger.info("Bot starting...")
    await log_event("INFO", "main", "Bot started")

    try:
        await dp.start_polling(bot)
    finally:
        engine.stop()
        trading_task.cancel()
        retrain_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
