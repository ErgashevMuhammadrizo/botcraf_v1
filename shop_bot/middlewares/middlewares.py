from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from typing import Callable, Any, Awaitable
from config import ADMIN_IDS
from database.db import get_admins


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict], Awaitable[Any]],
        event: TelegramObject,
        data: dict,
    ) -> Any:
        from database.db import get_user, upsert_user
        if isinstance(event, Message):
            user = event.from_user
            if user:
                await upsert_user(user.id, user.username or "", user.full_name or "")
                db_user = await get_user(user.id)
                if db_user and db_user.get("is_banned"):
                    await event.answer("🚫 Siz bloklangansiz.")
                    return
        return await handler(event, data)


async def is_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    admins = await get_admins()
    return any(a["id"] == user_id for a in admins)
