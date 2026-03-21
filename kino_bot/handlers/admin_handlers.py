# ============================================================
# KINO BOT — ADMIN HANDLERLARI (serial master tizimi)
# ============================================================

import logging
import os

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..database import (
    is_admin, add_movie, add_serial, delete_movie, delete_serial,
    get_all_movies, get_all_users, ban_user, unban_user,
    add_required_channel, remove_required_channel, get_required_channels,
    add_social, get_socials, remove_social,
    add_admin, remove_admin, get_all_admins,
    get_movie_by_kod, get_serial_by_kod,
    get_or_create_serial_master, update_serial_master_channel,
    get_serial_episodes, get_serial_master_by_kod, search_serials,
    get_all_settings, set_setting
)
from ..keyboards import (
    admin_main_kb, admin_sub_kb, admin_social_kb, admin_admins_kb,
    user_main_kb, watch_kb, serial_episodes_kb, admin_settings_kb
)
from ..utils import generate_unique_kod, send_post_to_channel, send_video_to_channel, delete_from_channel

logger = logging.getLogger(__name__)
router = Router()


# ============================================================
# FSM HOLATLARI
# ============================================================
class AdminStates(StatesGroup):
    # ── Kino qo'shish ─────────────────────────────────────
    movie_title   = State()
    movie_desc    = State()
    movie_year    = State()
    movie_genre   = State()
    movie_poster  = State()
    movie_video   = State()

    # ── Serial qo'shish (yangi tizim) ─────────────────────
    serial_title   = State()   # Serial nomi (mavjud yoki yangi)
    serial_season  = State()   # Mavsum
    serial_episode = State()   # Qism
    serial_desc    = State()   # Tafsif (faqat yangi serialda so'raladi)
    serial_poster  = State()   # Poster (faqat yangi serialda)
    serial_video   = State()   # Video (har doim)

    # ── O'chirish ──────────────────────────────────────────
    delete_kod = State()

    # ── Majburiy obuna ─────────────────────────────────────
    sub_id    = State()
    sub_name  = State()
    sub_url   = State()
    sub_type  = State()
    rem_sub   = State()

    # ── Ijtimoiy tarmoq ────────────────────────────────────
    social_name = State()
    social_url  = State()
    rem_social  = State()

    # ── Admin boshqaruv ────────────────────────────────────
    add_adm_id = State()
    rem_adm_id = State()

    setting_value = State()


async def admin_check(message: Message) -> bool:
    if not await is_admin(message.from_user.id):
        await message.answer("🚫 Sizda admin huquqi yo'q!")
        return False
    return True


# ════════════════════════════════════════════════════════════
# ADMIN PANEL
# ════════════════════════════════════════════════════════════
@router.message(Command("admin"))
async def open_admin(message: Message):
    if not await admin_check(message):
        return
    await message.answer("👮 <b>Admin panel</b>", reply_markup=admin_main_kb(), parse_mode="HTML")


@router.message(F.text == "🔙 User rejimi")
async def back_to_user(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👤 User rejim", reply_markup=user_main_kb())



@router.message(F.text == "⚙️ Sozlamalar")
async def open_settings(message: Message, state: FSMContext):
    if not await admin_check(message):
        return
    await state.clear()
    settings = await get_all_settings()
    await message.answer("⚙️ <b>Kino bot sozlamalari</b>", reply_markup=admin_settings_kb(settings), parse_mode="HTML")


@router.callback_query(F.data.in_(["set_payment_card", "set_payment_card_owner", "set_admin_username", "set_admin_contact_text"]))
async def settings_edit(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        return
    key_map = {
        "set_payment_card": "payment_card",
        "set_payment_card_owner": "payment_card_owner",
        "set_admin_username": "admin_username",
        "set_admin_contact_text": "admin_contact_text",
    }
    prompts = {
        "payment_card": "💳 Yangi karta raqamini yuboring.",
        "payment_card_owner": "👤 Yangi karta egasini yuboring.",
        "admin_username": "📞 Yangi admin username yuboring. Masalan: <code>@username</code>",
        "admin_contact_text": "📝 Admin bilan bog'lanish bo'limi uchun matn yuboring.",
    }
    setting_key = key_map[callback.data]
    await state.set_state(AdminStates.setting_value)
    await state.update_data(setting_key=setting_key)
    await callback.message.answer(prompts[setting_key], parse_mode='HTML')
    await callback.answer()


@router.message(StateFilter(AdminStates.setting_value))
async def settings_save(message: Message, state: FSMContext):
    if not await admin_check(message):
        return
    data = await state.get_data()
    await state.clear()
    setting_key = data['setting_key']
    value = (message.text or '').strip()
    if not value:
        await message.answer("❌ Bo'sh qiymat yubormang.")
        return
    if setting_key == 'admin_username' and not value.startswith('@'):
        value = '@' + value.lstrip('@')
    await set_setting(setting_key, value)
    settings = await get_all_settings()
    await message.answer("✅ Sozlama saqlandi.", reply_markup=admin_settings_kb(settings))


# ════════════════════════════════════════════════════════════
# KINO QO'SHISH
# ════════════════════════════════════════════════════════════
@router.message(F.text == "🎬 Kino qo'shish")
async def add_movie_start(message: Message, state: FSMContext):
    if not await admin_check(message):
        return
    await state.set_state(AdminStates.movie_title)
    await message.answer("🎬 <b>Kino nomini kiriting:</b>", parse_mode="HTML")


@router.message(StateFilter(AdminStates.movie_title))
async def movie_title_rcv(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminStates.movie_desc)
    await message.answer("📝 <b>Tafsif kiriting</b> (yoki /skip):", parse_mode="HTML")


@router.message(StateFilter(AdminStates.movie_desc))
async def movie_desc_rcv(message: Message, state: FSMContext):
    await state.update_data(desc="" if message.text == "/skip" else message.text.strip())
    await state.set_state(AdminStates.movie_year)
    await message.answer("📅 <b>Yil</b> (masalan: 2024, yoki /skip):", parse_mode="HTML")


@router.message(StateFilter(AdminStates.movie_year))
async def movie_year_rcv(message: Message, state: FSMContext):
    year = 0
    if message.text != "/skip":
        try:
            year = int(message.text.strip())
        except ValueError:
            pass
    await state.update_data(year=year)
    await state.set_state(AdminStates.movie_genre)
    await message.answer("🎭 <b>Janr</b> (masalan: Drama, yoki /skip):", parse_mode="HTML")


@router.message(StateFilter(AdminStates.movie_genre))
async def movie_genre_rcv(message: Message, state: FSMContext):
    await state.update_data(genre="" if message.text == "/skip" else message.text.strip())
    await state.set_state(AdminStates.movie_poster)
    await message.answer(
        "🖼 <b>Poster rasmi yuboring</b> (yoki /skip):\n\nBu rasm kanal postida ko'rinadi.",
        parse_mode="HTML"
    )


@router.message(StateFilter(AdminStates.movie_poster))
async def movie_poster_rcv(message: Message, state: FSMContext):
    poster_id = message.photo[-1].file_id if message.photo else ""
    await state.update_data(poster_id=poster_id)
    await state.set_state(AdminStates.movie_video)
    await message.answer("🎥 <b>Video faylini yuboring:</b>", parse_mode="HTML")


@router.message(StateFilter(AdminStates.movie_video), F.video)
async def movie_video_rcv(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()

    file_id  = message.video.file_id
    kod      = await generate_unique_kod()
    bot_info = await bot.get_me()

    caption = (
        f"🎬 <b>{data['title']}</b>\n"
        f"📅 {data.get('year') or '—'}  🎭 {data.get('genre') or '—'}\n\n"
        f"{data.get('desc') or ''}\n\n"
        f"🔢 Kod: <b>{kod}</b>"
    )

    kb = watch_kb(kod, bot_info.username)
    channel_msg_id = await send_post_to_channel(
        bot, data.get("poster_id", ""), caption, kb, data["title"]
    )
    archive_msg = await send_video_to_channel(bot, file_id)

    await add_movie(
        title=data["title"], description=data.get("desc", ""),
        year=data.get("year", 0), genre=data.get("genre", ""),
        file_id=file_id, channel_msg_id=channel_msg_id or 0,
        kod=kod, added_by=message.from_user.id,
        poster_file_id=data.get("poster_id", ""),
        archive_chat_id=str(getattr(archive_msg.chat, "id", os.getenv("KINO_CHANNEL_ID", ""))) if archive_msg else os.getenv("KINO_CHANNEL_ID", ""),
        archive_msg_id=getattr(archive_msg, "message_id", 0) if archive_msg else 0
    )

    await message.answer(
        f"✅ <b>Kino qo'shildi!</b>\n\n"
        f"🎬 {data['title']}\n"
        f"🔢 Kod: <b>{kod}</b>\n\n"
        f"Kanal postida 'Tomosha qilish' tugmasi ko'rinadi 🎉",
        reply_markup=admin_main_kb(), parse_mode="HTML"
    )


# ════════════════════════════════════════════════════════════
# SERIAL QO'SHISH — yangi tizim:
# Bir serialga bitta kanal posti, qismlar tugma sifatida chiqadi
# ════════════════════════════════════════════════════════════
@router.message(F.text == "📺 Serial qo'shish")
async def add_serial_start(message: Message, state: FSMContext):
    if not await admin_check(message):
        return
    await state.set_state(AdminStates.serial_title)
    await message.answer(
        "📺 <b>Serial nomini kiriting:</b>\n\n"
        "💡 Agar bu serial allaqachon bazada bo'lsa,\n"
        "yangi qism shu serialga biriktiriladi.",
        parse_mode="HTML"
    )


@router.message(StateFilter(AdminStates.serial_title))
async def serial_title_rcv(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminStates.serial_season)
    await message.answer("📂 <b>Mavsum raqami:</b> (masalan: 1)", parse_mode="HTML")


@router.message(StateFilter(AdminStates.serial_season))
async def serial_season_rcv(message: Message, state: FSMContext):
    try:
        s = int(message.text.strip())
    except ValueError:
        s = 1
    await state.update_data(season=s)
    await state.set_state(AdminStates.serial_episode)
    await message.answer("🔢 <b>Qism raqami:</b> (masalan: 3)", parse_mode="HTML")


@router.message(StateFilter(AdminStates.serial_episode))
async def serial_episode_rcv(message: Message, state: FSMContext):
    try:
        e = int(message.text.strip())
    except ValueError:
        e = 1
    data = await state.get_data()
    await state.update_data(episode=e)

    # Bu serial allaqachon bazada bormi?
    existing = await get_or_create_serial_master(
        data["title"], data["season"], message.from_user.id
    )
    master_kod, is_new = existing

    if is_new:
        # Yangi serial — tafsif va poster so'rash
        await state.update_data(master_kod=master_kod, is_new_serial=True)
        await state.set_state(AdminStates.serial_desc)
        await message.answer(
            f"📝 <b>Serial tafsifi</b> (yoki /skip):\n\n"
            f"Bu tafsif kanal postida ko'rinadi.",
            parse_mode="HTML"
        )
    else:
        # Mavjud serial — tafsif va posterni o'tkazib yuborish
        await state.update_data(master_kod=master_kod, is_new_serial=False, desc="", poster_id="")
        await state.set_state(AdminStates.serial_video)
        master = await get_serial_master_by_kod(master_kod)
        await message.answer(
            f"✅ <b>{data['title']}</b> Mavsum {data['season']} topildi!\n\n"
            f"🎥 Endi {e}-qism videosini yuboring:",
            parse_mode="HTML"
        )


@router.message(StateFilter(AdminStates.serial_desc))
async def serial_desc_rcv(message: Message, state: FSMContext):
    await state.update_data(desc="" if message.text == "/skip" else message.text.strip())
    await state.set_state(AdminStates.serial_poster)
    await message.answer(
        "🖼 <b>Poster rasmi yuboring</b> (yoki /skip):\n\nBu rasm kanal postida ko'rinadi.",
        parse_mode="HTML"
    )


@router.message(StateFilter(AdminStates.serial_poster))
async def serial_poster_rcv(message: Message, state: FSMContext):
    poster_id = message.photo[-1].file_id if message.photo else ""
    await state.update_data(poster_id=poster_id)
    await state.set_state(AdminStates.serial_video)
    data = await state.get_data()
    await message.answer(
        f"🎥 <b>{data['episode']}-qism videosini yuboring:</b>",
        parse_mode="HTML"
    )


@router.message(StateFilter(AdminStates.serial_video), F.video)
async def serial_video_rcv(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()

    file_id   = message.video.file_id
    kod       = await generate_unique_kod()
    bot_info  = await bot.get_me()
    master_kod = data["master_kod"]
    is_new    = data.get("is_new_serial", False)
    title     = data["title"]
    season    = data["season"]
    episode   = data["episode"]

    archive_msg = await send_video_to_channel(bot, file_id)

    # Qismni bazaga qo'shish
    await add_serial(
        title=title, season=season, episode=episode,
        description=data.get("desc", ""),
        file_id=file_id, channel_msg_id=0,
        kod=kod, added_by=message.from_user.id,
        poster_file_id=data.get("poster_id", ""),
        archive_chat_id=str(getattr(archive_msg.chat, "id", os.getenv("KINO_CHANNEL_ID", ""))) if archive_msg else os.getenv("KINO_CHANNEL_ID", ""),
        archive_msg_id=getattr(archive_msg, "message_id", 0) if archive_msg else 0
    )

    if is_new:
        # Yangi serial — kanal postini yaratish
        episodes = await get_serial_episodes(title, season)
        caption = (
            f"📺 <b>{title}</b>\n"
            f"📂 Mavsum {season}\n\n"
            f"{data.get('desc') or ''}\n\n"
            f"🔢 Kod: <b>{master_kod}</b>"
        )
        ep_kb = serial_episodes_kb(episodes, title, season)
        channel_msg_id = await send_post_to_channel(
            bot, data.get("poster_id", ""), caption, ep_kb, title
        )
        await update_serial_master_channel(master_kod, channel_msg_id or 0)
        poster_note = "📢 Kanal postida qismlar tugmasi bilan chiqdi!\n"
    else:
        # Mavjud serial — kanal postini yangilash
        master = await get_serial_master_by_kod(master_kod)
        poster_note = "🔄 Kanal postiga yangi qism tugmasi qo'shildi!\n"

        if master and master[6]:  # channel_msg_id
            try:
                episodes = await get_serial_episodes(title, season)
                ep_kb = serial_episodes_kb(episodes, title, season)
                await bot.edit_message_reply_markup(
                    chat_id=os.getenv("KINO_CHANNEL_ID"),
                    message_id=master[6],
                    reply_markup=ep_kb
                )
            except Exception as e:
                logger.warning("Kanal postini yangilashda xato: %s", e)

    await message.answer(
        f"✅ <b>Serial qo'shildi!</b>\n\n"
        f"📺 {title} S{season}E{episode}\n"
        f"🔢 Qism kodi: <b>{kod}</b>\n"
        f"🗂 Master kod: <b>{master_kod}</b>\n\n"
        f"{poster_note}",
        reply_markup=admin_main_kb(), parse_mode="HTML"
    )


# ════════════════════════════════════════════════════════════
# KINO/SERIAL O'CHIRISH
# ════════════════════════════════════════════════════════════
@router.message(F.text == "🗑 Kino o'chirish")
async def delete_start(message: Message, state: FSMContext):
    if not await admin_check(message):
        return
    await state.set_state(AdminStates.delete_kod)
    await message.answer(
        "🗑 <b>O'chirmoqchi bo'lgan kino/serial kodini kiriting:</b>\n\n"
        "Kino kodi yoki qism kodini kiriting.",
        parse_mode="HTML"
    )


@router.message(StateFilter(AdminStates.delete_kod))
async def delete_by_kod(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    kod = message.text.strip()

    movie = await get_movie_by_kod(kod)
    if movie:
        await delete_from_channel(bot, movie[6])
        await delete_movie(kod)
        await message.answer(f"✅ <b>{movie[1]}</b> o'chirildi.", reply_markup=admin_main_kb(), parse_mode="HTML")
        return

    serial = await get_serial_by_kod(kod)
    if serial:
        await delete_serial(kod)
        await message.answer(
            f"✅ <b>{serial[1]}</b> S{serial[2]}E{serial[3]} o'chirildi.",
            reply_markup=admin_main_kb(), parse_mode="HTML"
        )
        return

    await message.answer(f"❌ <code>{kod}</code> topilmadi.", parse_mode="HTML")


# ════════════════════════════════════════════════════════════
# FOYDALANUVCHILAR + BAN
# ════════════════════════════════════════════════════════════
@router.message(F.text == "👥 Foydalanuvchilar")
async def show_users(message: Message):
    if not await admin_check(message):
        return
    users = await get_all_users()
    total  = len(users)
    banned = sum(1 for u in users if u[4])
    await message.answer(
        f"👥 <b>Foydalanuvchilar</b>\n\n"
        f"📊 Jami: {total} | 🚫 Banned: {banned}\n\n"
        f"/ban [ID] — ban berish\n"
        f"/unban [ID] — banni olib tashlash\n\n"
        f"<b>So'nggi 20 ta:</b>\n" +
        "\n".join(f"{'🚫' if u[4] else '✅'} <code>{u[0]}</code> {u[2]}" for u in users[:20]),
        parse_mode="HTML"
    )


@router.message(F.text.startswith("/ban "))
async def ban_cmd(message: Message):
    if not await admin_check(message):
        return
    try:
        uid = int(message.text.split()[1])
        await ban_user(uid)
        await message.answer(f"✅ <code>{uid}</code> bloklandi.", parse_mode="HTML")
    except (IndexError, ValueError):
        await message.answer("❌ Noto'g'ri. Namuna: /ban 123456")


@router.message(F.text.startswith("/unban "))
async def unban_cmd(message: Message):
    if not await admin_check(message):
        return
    try:
        uid = int(message.text.split()[1])
        await unban_user(uid)
        await message.answer(f"✅ <code>{uid}</code> unban qilindi.", parse_mode="HTML")
    except (IndexError, ValueError):
        await message.answer("❌ Noto'g'ri. Namuna: /unban 123456")


# ════════════════════════════════════════════════════════════
# MAJBURIY OBUNA
# ════════════════════════════════════════════════════════════
@router.message(F.text == "📢 Majburiy obuna")
async def manage_subs(message: Message):
    if not await admin_check(message):
        return
    await message.answer("📢 <b>Majburiy obuna:</b>", reply_markup=admin_sub_kb(), parse_mode="HTML")


@router.callback_query(F.data == "listsub")
async def listsub_cb(callback: CallbackQuery):
    chs = await get_required_channels()
    lines = ["📋 <b>Majburiy kanallar:</b>\n"] if chs else ["📋 Bo'sh."]
    for ch_id, ch_name, ch_url, ch_type in chs:
        lines.append(f"• {ch_name} — <code>{ch_id}</code>")
    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "addsub_start")
async def addsub_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.sub_id)
    await callback.message.answer("📢 Kanal ID:", parse_mode="HTML")
    await callback.answer()


@router.message(StateFilter(AdminStates.sub_id))
async def sub_id_rcv(message: Message, state: FSMContext):
    await state.update_data(sub_id=message.text.strip())
    await state.set_state(AdminStates.sub_name)
    await message.answer("✏️ Kanal nomi:")


@router.message(StateFilter(AdminStates.sub_name))
async def sub_name_rcv(message: Message, state: FSMContext):
    await state.update_data(sub_name=message.text.strip())
    await state.set_state(AdminStates.sub_url)
    await message.answer("🔗 Kanal havolasi (yoki /skip):")


@router.message(StateFilter(AdminStates.sub_url))
async def sub_url_rcv(message: Message, state: FSMContext):
    await state.update_data(sub_url="" if message.text == "/skip" else message.text.strip())
    await state.set_state(AdminStates.sub_type)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌐 Ochiq", callback_data="subtype_public"),
        InlineKeyboardButton(text="🔒 Yopiq", callback_data="subtype_private"),
    ]])
    await message.answer("🔐 Kanal turi:", reply_markup=kb)


@router.callback_query(F.data.in_(["subtype_public", "subtype_private"]))
async def sub_type_rcv(callback: CallbackQuery, state: FSMContext):
    ctype = "public" if callback.data == "subtype_public" else "private"
    data = await state.get_data()
    await state.clear()
    await add_required_channel(data["sub_id"], data["sub_name"], data.get("sub_url", ""), ctype)
    await callback.message.answer(f"✅ {data['sub_name']} qo'shildi!", reply_markup=admin_main_kb())
    await callback.answer()


@router.callback_query(F.data == "removesub_start")
async def removesub_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.rem_sub)
    await callback.message.answer("🗑 O'chirmoqchi bo'lgan kanal ID:")
    await callback.answer()


@router.message(StateFilter(AdminStates.rem_sub))
async def rem_sub_rcv(message: Message, state: FSMContext):
    await state.clear()
    await remove_required_channel(message.text.strip())
    await message.answer("✅ O'chirildi.", reply_markup=admin_main_kb())


# ════════════════════════════════════════════════════════════
# IJTIMOIY TARMOQLAR
# ════════════════════════════════════════════════════════════
@router.message(F.text == "🌐 Ijtimoiy tarmoqlar")
async def manage_socials(message: Message):
    if not await admin_check(message):
        return
    await message.answer("🌐 <b>Ijtimoiy tarmoqlar:</b>", reply_markup=admin_social_kb(), parse_mode="HTML")


@router.callback_query(F.data == "listsocial")
async def listsocial_cb(callback: CallbackQuery):
    socials = await get_socials()
    lines = ["📋 <b>Ijtimoiy tarmoqlar:</b>\n"] if socials else ["📋 Bo'sh."]
    for sid, name, url in socials:
        lines.append(f"[{sid}] {name} — {url}")
    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "addsocial_start")
async def addsocial_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.social_name)
    await callback.message.answer("✏️ Tarmoq nomi (masalan: Instagram):")
    await callback.answer()


@router.message(StateFilter(AdminStates.social_name))
async def social_name_rcv(message: Message, state: FSMContext):
    await state.update_data(social_name=message.text.strip())
    await state.set_state(AdminStates.social_url)
    await message.answer("🔗 Havolasi:")


@router.message(StateFilter(AdminStates.social_url))
async def social_url_rcv(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await add_social(data["social_name"], message.text.strip())
    await message.answer(f"✅ {data['social_name']} qo'shildi!", reply_markup=admin_main_kb())


@router.callback_query(F.data == "removesocial_start")
async def removesocial_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.rem_social)
    await callback.message.answer("🗑 O'chirish ID si (ro'yxatdan):")
    await callback.answer()


@router.message(StateFilter(AdminStates.rem_social))
async def rem_social_rcv(message: Message, state: FSMContext):
    await state.clear()
    try:
        await remove_social(int(message.text.strip()))
        await message.answer("✅ O'chirildi.", reply_markup=admin_main_kb())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID.")


# ════════════════════════════════════════════════════════════
# ADMINLAR BOSHQARUVI
# ════════════════════════════════════════════════════════════
@router.message(F.text == "👮 Adminlar")
async def manage_admins(message: Message):
    if not await admin_check(message):
        return
    await message.answer("👮 <b>Adminlar:</b>", reply_markup=admin_admins_kb(), parse_mode="HTML")


@router.callback_query(F.data == "listadmins")
async def listadmins_cb(callback: CallbackQuery):
    admins = await get_all_admins()
    lines = ["👮 <b>Adminlar:</b>\n"] if admins else ["📋 Bo'sh."]
    for uid, uname, added in admins:
        lines.append(f"• <code>{uid}</code> @{uname or '—'}")
    await callback.message.answer("\n".join(lines), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "addadmin_start")
async def addadmin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.add_adm_id)
    await callback.message.answer("👤 Yangi admin ID:")
    await callback.answer()


@router.message(StateFilter(AdminStates.add_adm_id))
async def addadmin_rcv(message: Message, state: FSMContext):
    await state.clear()
    try:
        uid = int(message.text.strip())
        await add_admin(uid)
        await message.answer(f"✅ <code>{uid}</code> admin qilindi.", reply_markup=admin_main_kb(), parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID.")


@router.callback_query(F.data == "removeadmin_start")
async def removeadmin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.rem_adm_id)
    await callback.message.answer("🗑 O'chirmoqchi admin ID:")
    await callback.answer()


@router.message(StateFilter(AdminStates.rem_adm_id))
async def removeadmin_rcv(message: Message, state: FSMContext):
    await state.clear()
    try:
        uid = int(message.text.strip())
        await remove_admin(uid)
        await message.answer(f"✅ <code>{uid}</code> admindan o'chirildi.", reply_markup=admin_main_kb(), parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID.")


# ════════════════════════════════════════════════════════════
# STATISTIKA
# ════════════════════════════════════════════════════════════
@router.message(F.text == "📊 Statistika")
async def show_stats(message: Message):
    if not await admin_check(message):
        return
    users   = await get_all_users()
    movies  = await get_all_movies()
    serials = await search_serials("")
    await message.answer(
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{len(users)}</b>\n"
        f"🚫 Banned: <b>{sum(1 for u in users if u[4])}</b>\n"
        f"🎬 Kinolar: <b>{len(movies)}</b>\n"
        f"📺 Serial sarlavhalar: <b>{len(serials)}</b>",
        reply_markup=admin_main_kb(), parse_mode="HTML"
    )
