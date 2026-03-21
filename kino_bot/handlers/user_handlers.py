# ============================================================
# KINO BOT — USER HANDLERLARI (serial master tizimi)
# ============================================================

import logging
import os
import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..database import (
    register_kino_user, get_user, get_required_channels,
    search_movies, search_serial_masters, get_movie_by_kod,
    get_serial_by_kod, increment_movie_views, increment_serial_views,
    get_socials, get_serial_episodes, get_serial_seasons,
    get_serial_master_by_kod, get_setting
)
from ..keyboards import (
    user_main_kb, subscription_check_kb, search_result_kb,
    serial_episodes_kb, serial_seasons_kb
)

logger = logging.getLogger(__name__)
router = Router()

# Aiofiles o'rniga oddiy cache
_sub_cache: dict = {}   # user_id: timestamp
SUB_CACHE_TTL = 300     # 5 daqiqa


class UserStates(StatesGroup):
    searching = State()


# ════════════════════════════════════════════════════════════
# OBUNA TEKSHIRISH (tezlashtirilgan cache bilan)
# ════════════════════════════════════════════════════════════
async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Foydalanuvchi obunasini tekshirish — cache bilan tezlashtirilgan"""
    import time
    # Cache tekshirish
    if user_id in _sub_cache:
        if time.time() - _sub_cache[user_id] < SUB_CACHE_TTL:
            return True

    channels = await get_required_channels()
    if not channels:
        return True

    for ch_id, ch_name, ch_url, ch_type in channels:
        try:
            member = await bot.get_chat_member(ch_id, user_id)
            if member.status in ("left", "kicked"):
                _sub_cache.pop(user_id, None)
                return False
        except Exception:
            return False

    _sub_cache[user_id] = time.time()
    return True


async def require_subscription(bot: Bot, user_id: int, message_or_callback) -> bool:
    """Obuna yo'q bo'lsa xabar yuboradi va False qaytaradi"""
    if await check_subscription(bot, user_id):
        return True

    channels = await get_required_channels()
    text = "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>"

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(
            text,
            reply_markup=subscription_check_kb(channels),
            parse_mode="HTML"
        )
    else:  # CallbackQuery
        await message_or_callback.message.answer(
            text,
            reply_markup=subscription_check_kb(channels),
            parse_mode="HTML"
        )
        await message_or_callback.answer()
    return False


# ════════════════════════════════════════════════════════════
# /START
# ════════════════════════════════════════════════════════════
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await register_kino_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or ""
    )

    user = await get_user(message.from_user.id)
    if user and user[5]:  # is_banned
        await message.answer("🚫 Siz bloklangansiz!")
        return

    # deep_link orqali kelgan bo'lsa (kanal postidagi tugma)
    args = message.text.split()
    if len(args) > 1:
        kod = args[1]
        await handle_kod(message, kod, bot, state)
        return

    if not await require_subscription(bot, message.from_user.id, message):
        return

    socials = await get_socials()
    social_text = ""
    if socials:
        links = " | ".join(f"<a href='{url}'>{name}</a>" for _, name, url in socials)
        social_text = f"\n\n🌐 {links}"

    await message.answer(
        f"🎬 <b>Kino Botga xush kelibsiz!</b>\n\n"
        f"Kino yoki serial qidirish uchun:\n"
        f"• Kanal postidagi <b>'Tomosha qilish'</b> tugmasini bosing\n"
        f"• Yoki qidiruv tugmasini bosing"
        f"{social_text}",
        reply_markup=user_main_kb(),
        parse_mode="HTML"
    )



async def _send_from_archive(message: Message, chat_id, msg_id: int, fallback_file_id: str, caption: str, reply_markup=None):
    if chat_id and msg_id:
        try:
            copied = await message.bot.copy_message(
                chat_id=message.chat.id,
                from_chat_id=chat_id,
                message_id=msg_id,
                reply_markup=reply_markup,
            )
            if caption or reply_markup:
                try:
                    await message.bot.edit_message_caption(
                        chat_id=message.chat.id,
                        message_id=copied.message_id,
                        caption=caption or None,
                        reply_markup=reply_markup,
                        parse_mode='HTML',
                    )
                except Exception:
                    if reply_markup:
                        try:
                            await message.bot.edit_message_reply_markup(
                                chat_id=message.chat.id,
                                message_id=copied.message_id,
                                reply_markup=reply_markup,
                            )
                        except Exception:
                            pass
            return copied
        except Exception:
            pass
    if fallback_file_id:
        try:
            return await message.answer_video(video=fallback_file_id, caption=caption, reply_markup=reply_markup, parse_mode='HTML')
        except Exception:
            pass
    return await message.answer(caption, reply_markup=reply_markup, parse_mode='HTML')

async def handle_kod(message: Message, kod: str, bot: Bot, state: FSMContext):
    """Kod orqali kino/serial topish"""
    user = await get_user(message.from_user.id)
    if user and user[5]:
        await message.answer("🚫 Siz bloklangansiz!")
        return

    if not await require_subscription(bot, message.from_user.id, message):
        # Obuna kerak — ammo kodni eslab qolish
        await state.update_data(pending_kod=kod)
        return

    # Serial master kodi?
    master = await get_serial_master_by_kod(kod)
    if master:
        if master:
            title = master[1]
            season = master[2]
            episodes = await get_serial_episodes(title, season)
            if episodes:
                first_kod, first_ep = episodes[0]
                first_serial = await get_serial_by_kod(first_kod)
                ep_kb = serial_episodes_kb(episodes, title, season)
                text = (
                    f"📺 <b>{title}</b>\n"
                    f"📂 Mavsum {season}\n\n"
                    f"{master[4] or ''}\n\n"
                    f"▶️ Avval {first_ep}-qism yuborildi. Qolgan qismlarni pastdagi tugmalardan tanlang."
                )
                if first_serial:
                    await _send_from_archive(message, first_serial[6], int(first_serial[7] or 0), first_serial[5], text, ep_kb)
                else:
                    await message.answer(text, reply_markup=ep_kb, parse_mode="HTML")
            return

    # Kino kodi?
    movie = await get_movie_by_kod(kod)
    if movie:
        await increment_movie_views(kod)
        caption = (
            f"🎬 <b>{movie[1]}</b>\n"
            f"📅 {movie[3] or '—'}  🎭 {movie[4] or '—'}\n\n"
            f"{movie[2] or ''}"
        )
        await _send_from_archive(message, movie[6], int(movie[7] or 0), movie[5], caption)
        return

    # Serial qism kodi?
    serial = await get_serial_by_kod(kod)
    if serial:
        await increment_serial_views(kod)
        caption = (
            f"📺 <b>{serial[1]}</b>\n"
            f"📂 Mavsum {serial[2]}, {serial[3]}-qism\n\n"
            f"{serial[4] or ''}"
        )
        await _send_from_archive(message, serial[6], int(serial[7] or 0), serial[5], caption)
        return

    await message.answer(f"❌ <code>{kod}</code> kodi topilmadi.", parse_mode="HTML")


# ════════════════════════════════════════════════════════════
# OBUNA TEKSHIRISH TUGMASI
# ════════════════════════════════════════════════════════════
@router.callback_query(F.data == "check_sub")
async def check_sub_cb(callback: CallbackQuery, bot: Bot, state: FSMContext):
    _sub_cache.pop(callback.from_user.id, None)  # Cache tozalash
    if not await check_subscription(bot, callback.from_user.id):
        await callback.answer("❌ Hali obuna bo'lmadingiz!", show_alert=True)
        return

    await callback.message.delete()

    # Kutayotgan kod bormi?
    data = await state.get_data()
    pending_kod = data.get("pending_kod")
    await state.clear()

    if pending_kod:
        await handle_kod(callback.message, pending_kod, bot, state)
    else:
        await callback.message.answer(
            "✅ <b>Obuna tasdiqlandi!</b>\n\nBotdan foydalanishingiz mumkin 🎬",
            reply_markup=user_main_kb(),
            parse_mode="HTML"
        )
    await callback.answer()


# ════════════════════════════════════════════════════════════
# QIDIRUV
# ════════════════════════════════════════════════════════════
@router.message(F.text == "🔍 Kino qidirish")
async def search_start(message: Message, state: FSMContext, bot: Bot):
    if not await require_subscription(bot, message.from_user.id, message):
        return
    await state.set_state(UserStates.searching)
    await message.answer(
        "🔍 <b>Kino yoki serial nomini yozing:</b>\n\n"
        "Yoki to'g'ridan-to'g'ri kodni yuboring.",
        parse_mode="HTML"
    )


@router.message(StateFilter(UserStates.searching))
async def search_query(message: Message, state: FSMContext, bot: Bot):
    if not await require_subscription(bot, message.from_user.id, message):
        await state.clear()
        return
    await state.clear()

    query = message.text.strip()

    # Kod formatida bo'lsa to'g'ridan yuborish
    if len(query) <= 8 and (query.isalnum() or query.startswith("S")):
        await handle_kod(message, query, bot, state)
        return

    movies  = await search_movies(query)
    serials = await search_serial_masters(query)

    if not movies and not serials:
        await message.answer(
            f"❌ <b>'{query}'</b> bo'yicha hech narsa topilmadi.\n\n"
            f"To'g'ri nom yoki kodni kiriting.",
            parse_mode="HTML"
        )
        return

    if movies:
        await message.answer(
            f"🎬 <b>Kinolar ({len(movies)} ta):</b>",
            reply_markup=search_result_kb(movies, "movie"),
            parse_mode="HTML"
        )

    if serials:
        await message.answer(
            f"📺 <b>Seriallar ({len(serials)} ta):</b>",
            reply_markup=search_result_kb(serials, "serial"),
            parse_mode="HTML"
        )


@router.message(F.text & ~F.text.startswith("/") & ~F.text.in_({
    "🔍 Kino qidirish", "👤 Profil", "📞 Admin bilan bog'lanish",
    "🎬 Kino qo'shish", "📺 Serial qo'shish", "🗑 Kino o'chirish",
    "👥 Foydalanuvchilar", "📢 Majburiy obuna", "🌐 Ijtimoiy tarmoqlar",
    "👮 Adminlar", "📊 Statistika", "🔙 User rejimi"
}))
async def text_search(message: Message, bot: Bot, state: FSMContext):
    """Har qanday matn — qidiruv yoki kod"""
    user = await get_user(message.from_user.id)
    if user and user[5]:
        return

    if not await check_subscription(bot, message.from_user.id):
        channels = await get_required_channels()
        await message.answer(
            "⚠️ Avval kanalga obuna bo'ling!",
            reply_markup=subscription_check_kb(channels)
        )
        return

    query = message.text.strip()

    # Kod bo'lishi mumkin
    if len(query) <= 10 and query.replace("-", "").isalnum():
        await handle_kod(message, query, bot, state)
        return

    movies  = await search_movies(query)
    serials = await search_serial_masters(query)

    if not movies and not serials:
        return  # Jim qolish — spam oldini olish

    if movies:
        await message.answer(
            f"🎬 <b>Kinolar:</b>",
            reply_markup=search_result_kb(movies, "movie"),
            parse_mode="HTML"
        )
    if serials:
        await message.answer(
            f"📺 <b>Seriallar:</b>",
            reply_markup=search_result_kb(serials, "serial"),
            parse_mode="HTML"
        )


# ════════════════════════════════════════════════════════════
# INLINE TUGMA CALLBACKLAR
# ════════════════════════════════════════════════════════════
@router.callback_query(F.data.startswith("get_movie_"))
async def get_movie_cb(callback: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, callback.from_user.id):
        channels = await get_required_channels()
        await callback.message.answer("⚠️ Avval obuna bo'ling!", reply_markup=subscription_check_kb(channels))
        await callback.answer()
        return

    kod = callback.data.replace("get_movie_", "")
    movie = await get_movie_by_kod(kod)
    if not movie:
        await callback.answer("❌ Kino topilmadi!", show_alert=True)
        return

    await increment_movie_views(kod)
    caption = (
        f"🎬 <b>{movie[1]}</b>\n"
        f"📅 {movie[3] or '—'}  🎭 {movie[4] or '—'}\n\n"
        f"{movie[2] or ''}"
    )
    await _send_from_archive(callback.message, movie[6], int(movie[7] or 0), movie[5], caption)
    await callback.answer()


@router.callback_query(F.data.startswith("get_serial_"))
async def get_serial_cb(callback: CallbackQuery, bot: Bot):
    if not await check_subscription(bot, callback.from_user.id):
        channels = await get_required_channels()
        await callback.message.answer("⚠️ Avval obuna bo'ling!", reply_markup=subscription_check_kb(channels))
        await callback.answer()
        return

    kod = callback.data.replace("get_serial_", "")
    serial = await get_serial_by_kod(kod)
    if not serial:
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return

    await increment_serial_views(kod)
    caption = (
        f"📺 <b>{serial[1]}</b>\n"
        f"📂 Mavsum {serial[2]}, {serial[3]}-qism\n\n"
        f"{serial[4] or ''}"
    )
    await _send_from_archive(callback.message, serial[6], int(serial[7] or 0), serial[5], caption)
    await callback.answer()


@router.callback_query(F.data.startswith("serial_master_"))
async def serial_master_cb(callback: CallbackQuery, bot: Bot):
    """Serial master bosildi — qismlar ko'rsatish"""
    if not await check_subscription(bot, callback.from_user.id):
        channels = await get_required_channels()
        await callback.message.answer("⚠️ Avval obuna bo'ling!", reply_markup=subscription_check_kb(channels))
        await callback.answer()
        return

    master_kod = callback.data.replace("serial_master_", "")
    master = await get_serial_master_by_kod(master_kod)
    if not master:
        await callback.answer("❌ Topilmadi!", show_alert=True)
        return

    title = master[1]
    season = master[2]
    episodes = await get_serial_episodes(title, season)

    if not episodes:
        await callback.answer("❌ Qism topilmadi!", show_alert=True)
        return

    ep_kb = serial_episodes_kb(episodes, title, season)
    text = (
        f"📺 <b>{title}</b>\n"
        f"📂 Mavsum {season} — {len(episodes)} ta qism\n\n"
        f"Qismni tanlang 👇"
    )
    await callback.message.answer(text, reply_markup=ep_kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("serial_season_"))
async def serial_season_cb(callback: CallbackQuery, bot: Bot):
    """Mavsum bosildi — qismlar ko'rsatish"""
    parts = callback.data.replace("serial_season_", "").rsplit("_", 1)
    if len(parts) != 2:
        await callback.answer("❌ Xato!", show_alert=True)
        return
    title, season_str = parts
    season = int(season_str)

    episodes = await get_serial_episodes(title, season)
    if not episodes:
        await callback.answer("❌ Qism topilmadi!", show_alert=True)
        return

    ep_kb = serial_episodes_kb(episodes, title, season)
    await callback.message.edit_reply_markup(reply_markup=ep_kb)
    await callback.answer()


# ════════════════════════════════════════════════════════════
# PROFIL
# ════════════════════════════════════════════════════════════
@router.message(F.text == "👤 Profil")
async def profile_cmd(message: Message, bot: Bot):
    if not await require_subscription(bot, message.from_user.id, message):
        return
    user = await get_user(message.from_user.id)
    await message.answer(
        f"👤 <b>Profilingiz</b>\n\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n"
        f"👤 Ism: {message.from_user.full_name}\n"
        f"📧 Username: @{message.from_user.username or '—'}",
        parse_mode="HTML"
    )


@router.message(F.text == "📞 Admin bilan bog'lanish")
async def contact_admin(message: Message):
    admin_username = await get_setting('admin_username', '@admin')
    contact_text = await get_setting('admin_contact_text', "Muammo yoki savollaringiz bo'lsa adminga yozing.")
    await message.answer(
        f"📞 <b>Admin bilan bog'lanish</b>\n\n{contact_text}\n{admin_username}",
        parse_mode="HTML"
    )
