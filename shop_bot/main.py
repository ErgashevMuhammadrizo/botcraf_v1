import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, BASE_DIR
from database.db import init_db
from middlewares.middlewares import BanCheckMiddleware
from handlers import user, order, admin

os.makedirs(BASE_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN .env faylida ko'rsatilmagan!")

    await init_db()
    logger.info("✅ Ma'lumotlar bazasi tayyor")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares
    dp.message.middleware(BanCheckMiddleware())

    # Routers — order matters!
    dp.include_router(admin.router)
    dp.include_router(order.router)
    dp.include_router(user.router)

    logger.info("🤖 Bot ishga tushyapti...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
