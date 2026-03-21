"""Majburiy obuna tekshiruvi"""

import logging
from aiogram import Bot
from aiogram.types import ChatMember
from utils.database import get_active_channels

logger = logging.getLogger(__name__)


async def check_subscriptions(bot: Bot, user_id: int) -> tuple[bool, list]:
    """
    Foydalanuvchi barcha kanallarga obuna bo'lganmi?
    Returns: (all_subscribed: bool, missing_channels: list)
    """
    channels = await get_active_channels()
    if not channels:
        return True, []

    missing = []
    for ch in channels:
        try:
            member: ChatMember = await bot.get_chat_member(
                chat_id=int(ch["channel_id"]), user_id=user_id
            )
            if member.status in ("left", "kicked", "banned"):
                missing.append(ch)
        except Exception as e:
            logger.warning(f"Kanal tekshirishda xato {ch['channel_id']}: {e}")
            # Xato bo'lsa skip qilamiz (kanal mavjud emas bo'lishi mumkin)

    return len(missing) == 0, missing
