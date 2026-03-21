# ============================================================
# KINO BOT — ISHGA TUSHIRISH
# ============================================================

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from kino_bot.database import init_kino_db
from kino_bot.handlers.user_handlers import router as user_router
from kino_bot.handlers.admin_handlers import router as admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    token = os.getenv("KINO_BOT_TOKEN")
    if not token:
        raise ValueError("KINO_BOT_TOKEN topilmadi!")

    await init_kino_db()

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    me = await bot.get_me()
    logger.info("✅ Kino bot ishga tushmoqda: @%s", me.username)

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(admin_router)
    dp.include_router(user_router)

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
