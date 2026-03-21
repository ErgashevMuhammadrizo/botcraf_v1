#!/usr/bin/env python3
"""🎬 MediaBot v3.0 — YouTube · Instagram · TikTok Downloader"""

import os
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config.settings import BOT_TOKEN, FFMPEG_AVAILABLE, LOGS_DIR
from handlers.start import router as start_router
from handlers.download import router as download_router
from handlers.premium import router as premium_router
from handlers.admin import router as admin_router
from utils.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "bot.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(download_router)
    dp.include_router(premium_router)
    dp.include_router(admin_router)

    logger.info(f"🚀 MediaBot v3.0 ishga tushdi!")
    logger.info(f"🎬 ffmpeg: {'✅ bor' if FFMPEG_AVAILABLE else '❌ yo`q (past sifatlar ishlaydi)'}")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    asyncio.run(main())
