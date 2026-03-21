# ============================================================
# ASOSIY BOT — SCHEDULER (muddat tekshirish taymer)
# Har kecha 00:00 da ishlaydi
# ============================================================

import asyncio
import logging
import os
from aiogram import Bot

from .database import (
    deactivate_expired_bots, get_expiring_bots,
    deduct_balance, extend_bot_subscription, get_balance,
    choose_available_server, get_pending_waitlist, mark_waitlist_notified
)

logger = logging.getLogger(__name__)

BOT_MONTHLY_PRICE = 49_000


async def auto_renew_bots(bot: Bot):
    """
    Muddati tugayotgan botlarni tekshirish:
    - Balans yetarli bo'lsa — avtomatik uzaytirish
    - Yetarli bo'lmasa — ogohlantirish yuborish
    """
    # 1. Muddati tugagan botlarni o'chirish
    expired = await deactivate_expired_bots()
    for bot_id, owner_id, bot_username in expired:
        logger.info("Bot muddati tugadi: @%s (owner: %s)", bot_username, owner_id)
        try:
            await bot.send_message(
                owner_id,
                f"⛔ <b>@{bot_username} to'xtatildi!</b>\n\n"
                f"Botingiz muddati tugadi.\n"
                f"Balans to'ldirib, muddat uzaytiring.",
                parse_mode="HTML"
            )
        except Exception:
            pass

    # 2. 3 kundan kam qolganlarga ogohlantirish
    expiring = await get_expiring_bots(days=3)
    for bot_id, owner_id, bot_username, expires_at in expiring:
        balance = await get_balance(owner_id)

        if balance >= BOT_MONTHLY_PRICE:
            # Avtomatik yangilash
            ok = await deduct_balance(owner_id, BOT_MONTHLY_PRICE)
            if ok:
                new_exp = await extend_bot_subscription(bot_id, 1)
                try:
                    await bot.send_message(
                        owner_id,
                        f"✅ <b>@{bot_username} avtomatik yangilandi!</b>\n\n"
                        f"💵 {BOT_MONTHLY_PRICE:,} so'm balansingizdan yechildi.\n"
                        f"⏰ Yangi muddat: {str(new_exp)[:10]}\n\n"
                        f"Balans to'ldirish uchun asosiy botga o'ting.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
                logger.info("Bot avtomatik yangilandi: @%s", bot_username)
        else:
            # Ogohlantirish
            try:
                await bot.send_message(
                    owner_id,
                    f"⚠️ <b>@{bot_username} muddati yaqin tugaydi!</b>\n\n"
                    f"⏰ Tugash sanasi: {str(expires_at)[:10]}\n"
                    f"💰 Balans: {balance:,} so'm\n"
                    f"💵 Kerak: {BOT_MONTHLY_PRICE:,} so'm\n\n"
                    f"Iltimos, balansni to'ldiring!",
                    parse_mode="HTML"
                )
            except Exception:
                pass




async def notify_waitlist_if_capacity_available(bot: Bot):
    server_code = await choose_available_server()
    if not server_code:
        return
    pending = await get_pending_waitlist()
    for wait_id, user_id, bot_type, plan_code, created_at in pending:
        try:
            await bot.send_message(
                user_id,
                f"✅ Yangi server bo'shadi: <b>{server_code}</b>\n\nEndi bot yaratishni qayta urinib ko'rishingiz mumkin.",
                parse_mode='HTML',
            )
            await mark_waitlist_notified(wait_id)
        except Exception:
            logger.exception('Waitlist userga xabar yuborilmadi')
            continue
        # bitta bo'sh slot uchun bitta xabar
        break

async def run_scheduler(bot: Bot):
    """Har 24 soatda bir marta ishlaydi"""
    logger.info("✅ Scheduler ishga tushdi")
    while True:
        try:
            await auto_renew_bots(bot)
            await notify_waitlist_if_capacity_available(bot)
        except Exception as e:
            logger.error("Scheduler xatosi: %s", e)
        await asyncio.sleep(86400)  # 24 soat
