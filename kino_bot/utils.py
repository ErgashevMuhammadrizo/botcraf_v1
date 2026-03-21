# ============================================================
# KINO BOT — YORDAMCHI FUNKSIYALAR
# ============================================================

import os
import random
import string
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from .database import get_db_path
import aiosqlite

logger = logging.getLogger(__name__)


async def generate_unique_kod(length: int = 4) -> str:
    chars = string.digits
    db_path = get_db_path()
    while True:
        kod = ''.join(random.choices(chars, k=length))
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                'SELECT 1 FROM movies WHERE kod=? UNION SELECT 1 FROM serials WHERE kod=? UNION SELECT 1 FROM serial_masters WHERE master_kod=?',
                (kod, kod, kod)
            ) as cur:
                if not await cur.fetchone():
                    return kod


async def send_post_to_channel(bot: Bot, poster_file_id: str, caption: str, keyboard: InlineKeyboardMarkup, title: str) -> int | None:
    channel_id = os.getenv('KINO_CHANNEL_ID', '')
    if not channel_id:
        logger.warning('KINO_CHANNEL_ID sozlanmagan!')
        return None
    try:
        if poster_file_id:
            msg = await bot.send_photo(chat_id=channel_id, photo=poster_file_id, caption=caption, reply_markup=keyboard, parse_mode='HTML')
        else:
            msg = await bot.send_message(chat_id=channel_id, text=caption, reply_markup=keyboard, parse_mode='HTML')
        return msg.message_id
    except Exception as e:
        logger.error('Kanalga post yuborishda xato: %s', e)
        return None


async def send_video_to_channel(bot: Bot, file_id: str):
    archive_id = os.getenv('KINO_ARCHIVE_CHANNEL_ID', os.getenv('KINO_CHANNEL_ID', ''))
    if not archive_id:
        return None
    try:
        msg = await bot.send_video(chat_id=archive_id, video=file_id)
        return msg
    except Exception as e:
        logger.error('Arxiv kanalga video yuborishda xato: %s', e)
        return None


async def delete_from_channel(bot: Bot, msg_id: int) -> None:
    if not msg_id:
        return
    channel_id = os.getenv('KINO_CHANNEL_ID', '')
    if not channel_id:
        return
    try:
        await bot.delete_message(chat_id=channel_id, message_id=msg_id)
    except Exception as e:
        logger.warning("Kanal postini o'chirishda xato: %s", e)


async def update_channel_post_keyboard(bot: Bot, msg_id: int, keyboard: InlineKeyboardMarkup) -> bool:
    if not msg_id:
        return False
    channel_id = os.getenv('KINO_CHANNEL_ID', '')
    if not channel_id:
        return False
    try:
        await bot.edit_message_reply_markup(chat_id=channel_id, message_id=msg_id, reply_markup=keyboard)
        return True
    except Exception as e:
        logger.warning('Kanal post tugmalarini yangilashda xato: %s', e)
        return False
