"""
Yuklab olish handleri.
BUTTON_DATA_INVALID muammosi hal qilindi:
  — URL callback_data'ga yozilmaydi, FSM state'da saqlanadi.
"""

import asyncio
import logging
import os

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.downloader import detect_platform, is_valid_url, download_media, cleanup_file, normalize_url
from utils.database import (add_or_update_user, is_banned, is_premium,
                             log_download, get_active_channels)
from utils.keyboards import quality_keyboard, cancel_keyboard, subscribe_keyboard
from utils.subscription import check_subscriptions
from utils.helpers import platform_emoji, success_caption
from config.settings import QUALITY_OPTIONS

router = Router()
logger = logging.getLogger(__name__)

# Bir vaqtda yuklab olayotgan userlar
_active: set = set()


class DLState(StatesGroup):
    choosing_quality = State()
    # waiting_receipt FSM'da premium.py'da
    waiting_receipt = State()


# ─── URL KELDI ───────────────────────────────────────────────────────────────

@router.message(F.text == "📥 Yuklab olish")
async def prompt_url(message: Message):
    await message.answer(
        "🔗 Havola yuboring (YouTube / Instagram / TikTok):",
        reply_markup=cancel_keyboard()
    )


@router.message(F.text.regexp(r'https?://\S+'))
async def handle_url(message: Message, state: FSMContext, bot: Bot):
    user = message.from_user
    url = normalize_url(message.text.strip().split()[0])

    if await is_banned(user.id):
        return await message.answer("🚫 Siz ban qilingansiz.")

    if not is_valid_url(url):
        return await message.answer("❌ Noto'g'ri havola.")

    platform = detect_platform(url)
    if not platform:
        return await message.answer(
            "❌ Qo'llab-quvvatlanmagan havola.\n"
            "Faqat YouTube, Instagram, TikTok ishlaydi."
        )

    # Majburiy obuna tekshirish
    ok, missing = await check_subscriptions(bot, user.id)
    if not ok:
        await state.update_data(pending_url=url)
        return await message.answer(
            "📢 <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>",
            parse_mode="HTML",
            reply_markup=subscribe_keyboard(missing)
        )

    if user.id in _active:
        return await message.answer("⏳ Avvalgi yuklab olish tugashini kuting.")

    prem = await is_premium(user.id)
    emoji = platform_emoji(platform)

    # URL ni state'da saqlaymiz — callback_data'ga yozmаymiz
    await state.update_data(download_url=url, platform=platform)
    await state.set_state(DLState.choosing_quality)

    await message.answer(
        f"{emoji} <b>{platform.capitalize()}</b> aniqlandi!\n\n"
        f"🎞 Sifatni tanlang:"
        + ("" if prem else "\n\n🔒 <i>1080p va yuqorisi — Premium uchun</i>"),
        parse_mode="HTML",
        reply_markup=quality_keyboard(url, user_is_premium=prem)
    )


# ─── OBUNANI TEKSHIRISH ───────────────────────────────────────────────────────

@router.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    user = callback.from_user
    ok, missing = await check_subscriptions(bot, user.id)

    if not ok:
        await callback.message.edit_text(
            "❌ Hali obuna bo'lmagan kanallar bor:",
            reply_markup=subscribe_keyboard(missing)
        )
        return

    data = await state.get_data()
    url = data.get("pending_url")
    if not url:
        await callback.message.edit_text("✅ Obuna tasdiqlandi! Havola yuboring.")
        return

    await callback.message.delete()

    platform = detect_platform(url) or "unknown"
    prem = await is_premium(user.id)
    await state.update_data(download_url=url, platform=platform)
    await state.set_state(DLState.choosing_quality)

    await bot.send_message(
        callback.message.chat.id,
        f"✅ Obuna tasdiqlandi!\n\n"
        f"{platform_emoji(platform)} Sifatni tanlang:",
        parse_mode="HTML",
        reply_markup=quality_keyboard(url, user_is_premium=prem)
    )


# ─── PREMIUM LOCK BOSILDI ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("q_locked:"))
async def locked_quality(callback: CallbackQuery):
    await callback.answer(
        "⭐ Bu sifat faqat Premium foydalanuvchilar uchun!\n"
        "Premium sotib olish uchun /premium yuboring.",
        show_alert=True
    )


# ─── SIFAT TANLANDI ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("q:"), DLState.choosing_quality)
async def quality_chosen(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    quality_key = callback.data.split(":", 1)[1]
    user = callback.from_user

    data = await state.get_data()
    url = data.get("download_url")
    platform = data.get("platform", "unknown")

    if not url:
        await callback.message.edit_text("❌ URL topilmadi. Qaytadan yuboring.")
        await state.clear()
        return

    # Premium tekshirish (qayta)
    q_info = QUALITY_OPTIONS.get(quality_key, {})
    if q_info.get("premium") and not await is_premium(user.id):
        await callback.answer("⭐ Bu sifat Premium uchun!", show_alert=True)
        return

    if user.id in _active:
        await callback.answer("⏳ Kuting...", show_alert=True)
        return

    quality_label = q_info.get("label", quality_key)
    emoji = platform_emoji(platform)

    status_msg = await callback.message.edit_text(
        f"⬇️ <b>Yuklab olinmoqda...</b>\n\n"
        f"{emoji} {platform.capitalize()} · {quality_label}\n\n"
        f"<i>⏳ Iltimos kuting...</i>",
        parse_mode="HTML"
    )

    _active.add(user.id)
    await state.clear()

    try:
        result = await asyncio.wait_for(
            download_media(url, quality_key),
            timeout=180
        )

        if not result["success"]:
            await status_msg.edit_text(
                f"⚠️ <b>Xato:</b>\n{result['error']}",
                parse_mode="HTML"
            )
            await log_download(user.id, platform, url, quality_key, "failed")
            return

        await status_msg.edit_text(
            f"📤 Fayl yuborilmoqda... ({result['file_size']} MB)",
            parse_mode="HTML"
        )

        file_path = result["file_path"]
        caption = success_caption(result)
        ext = os.path.splitext(file_path)[1].lower()
        input_file = FSInputFile(file_path, filename=os.path.basename(file_path))

        if result["is_audio"]:
            await bot.send_audio(
                callback.message.chat.id, audio=input_file,
                caption=caption, parse_mode="HTML",
                title=result.get("title", "Audio")
            )
        elif ext in {".jpg", ".jpeg", ".png"}:
            await bot.send_photo(
                callback.message.chat.id, photo=input_file,
                caption=caption, parse_mode="HTML"
            )
        else:
            await bot.send_video(
                callback.message.chat.id, video=input_file,
                caption=caption, parse_mode="HTML",
                supports_streaming=True
            )

        await status_msg.delete()
        await log_download(user.id, platform, url, quality_key, "success",
                           result.get("file_size", 0))
        cleanup_file(file_path)

    except asyncio.TimeoutError:
        await status_msg.edit_text(
            "⏱ <b>Vaqt tugadi.</b> Video katta, manba sekin yoki platforma cheklov qo'ygan. 480p/720p yoki audio tanlab qayta urinib ko'ring.",
            parse_mode="HTML"
        )
        await log_download(user.id, platform, url, quality_key, "timeout")

    except Exception as e:
        logger.exception(f"Yuborish xatosi [{user.id}]: {e}")
        await status_msg.edit_text("❌ Fayl yuborishda xato.", parse_mode="HTML")

    finally:
        _active.discard(user.id)


# ─── STATISTIKA ──────────────────────────────────────────────────────────────

@router.message(F.text == "📊 Statistika")
async def user_stats(message: Message):
    from utils.database import get_stats
    s = await get_stats()
    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{s['total_users']}</b>\n"
        f"⭐ Premium: <b>{s['premium_users']}</b>\n"
        f"📥 Yuklab olishlar: <b>{s['total_downloads']}</b>\n\n"
        f"▶️ YouTube: {s['youtube']}\n"
        f"📸 Instagram: {s['instagram']}\n"
        f"🎵 TikTok: {s['tiktok']}",
        parse_mode="HTML"
    )


# ─── BEKOR QILISH ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel")
async def cancel_cb(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Bekor qilindi")
    await state.clear()
    try:
        await callback.message.edit_text("❌ Bekor qilindi.")
    except Exception:
        pass
