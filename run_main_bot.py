# ============================================================
# ASOSIY BOT — ISHGA TUSHIRISH
# ============================================================

import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from main_bot.database import init_db
from main_bot.handlers import router
from main_bot.scheduler import run_scheduler
from main_bot.launcher import restart_active_bots

load_dotenv()
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        RotatingFileHandler("logs/main_bot.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


async def main():
    token = os.getenv("MAIN_BOT_TOKEN")
    if not token:
        raise ValueError("MAIN_BOT_TOKEN topilmadi!")

    await init_db()
    restarted = await restart_active_bots(os.path.dirname(os.path.abspath(__file__)))

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    asyncio.create_task(run_scheduler(bot))

    logger.info("✅ Asosiy bot ishga tushdi! Qayta tiklangan child botlar: %s", restarted)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
