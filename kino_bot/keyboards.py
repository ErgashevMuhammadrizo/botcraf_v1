# ============================================================
# KINO BOT — KLAVIATURALAR MODULI
# ============================================================

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)


def _kb_btn(text: str, style: str | None = None) -> KeyboardButton:
    kwargs = {"text": text}
    if style:
        kwargs["style"] = style
    try:
        return KeyboardButton(**kwargs)
    except Exception:
        kwargs.pop("style", None)
        return KeyboardButton(**kwargs)


def _inline_btn(text: str, callback_data: str | None = None, url: str | None = None, style: str | None = None) -> InlineKeyboardButton:
    kwargs = {"text": text}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    if style:
        kwargs["style"] = style
    try:
        return InlineKeyboardButton(**kwargs)
    except Exception:
        kwargs.pop("style", None)
        return InlineKeyboardButton(**kwargs)


def user_main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [_kb_btn(text="🔍 Kino qidirish", style="primary")],
            [_kb_btn(text="👤 Profil"), _kb_btn(text="📞 Admin bilan bog'lanish", style="success")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Kino nomini yozing yoki kod kiriting..."
    )


def subscription_check_kb(channels: list) -> InlineKeyboardMarkup:
    buttons = []
    for ch_id, ch_name, ch_url, ch_type in channels:
        url = ch_url if ch_url else f"https://t.me/{ch_id.lstrip('@')}"
        buttons.append([_inline_btn(text=f"📢 {ch_name}", url=url, style="primary")])
    buttons.append([_inline_btn(text="✅ Obunani tekshirish", callback_data="check_sub", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def search_result_kb(results: list, result_type: str = "movie") -> InlineKeyboardMarkup:
    buttons = []
    for row in results:
        if result_type == "movie":
            kod = row[4]
            title = row[1]
            buttons.append([_inline_btn(text=f"🎬 {title}", callback_data=f"get_movie_{kod}", style="primary")])
        else:
            # Serial master: (id, title, season, master_kod)
            master_kod = row[3]
            title = row[1]
            season = row[2]
            buttons.append([_inline_btn(text=f"📺 {title} — Mavsum {season}", callback_data=f"serial_master_{master_kod}", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def watch_kb(kod: str, bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_inline_btn(text="▶️ Tomosha qilish", url=f"https://t.me/{bot_username}?start={kod}", style="success")]
    ])


def serial_episodes_kb(episodes: list, title: str, season: int) -> InlineKeyboardMarkup:
    """Serial qismlari tugmalari — har bir qism alohida tugma"""
    buttons = []
    row = []
    for kod, episode in episodes:
        btn = _inline_btn(text=f"{episode}-qism", callback_data=f"get_serial_{kod}")
        row.append(btn)
        if len(row) == 3:  # Qatorda 3 ta tugma
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def serial_seasons_kb(title: str, seasons: list) -> InlineKeyboardMarkup:
    """Serial mavsumlari tugmalari"""
    buttons = []
    for season in seasons:
        buttons.append([_inline_btn(text=f"📂 {season}-mavsum", callback_data=f"serial_season_{title}_{season}", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ════════════════════════════════════════════════════════════
# ADMIN PANELI
# ════════════════════════════════════════════════════════════
def admin_main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [_kb_btn(text="🎬 Kino qo'shish", style="primary"), _kb_btn(text="📺 Serial qo'shish", style="primary")],
            [_kb_btn(text="🗑 Kino o'chirish", style="danger"), _kb_btn(text="👥 Foydalanuvchilar")],
            [_kb_btn(text="📢 Majburiy obuna", style="success")],
            [_kb_btn(text="👮 Adminlar"), _kb_btn(text="📊 Statistika")],
            [_kb_btn(text="⚙️ Sozlamalar", style="success")],
            [_kb_btn(text="🔙 User rejimi")],
        ],
        resize_keyboard=True
    )


def admin_sub_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_inline_btn(text="➕ Kanal qo'shish", callback_data="addsub_start", style="success")],
        [_inline_btn(text="➖ Kanal o'chirish", callback_data="removesub_start", style="danger")],
        [_inline_btn(text="📋 Ro'yxat", callback_data="listsub")],
    ])


def admin_social_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_inline_btn(text="➕ Qo'shish", callback_data="addsocial_start", style="success")],
        [_inline_btn(text="➖ O'chirish", callback_data="removesocial_start", style="danger")],
        [_inline_btn(text="📋 Ro'yxat", callback_data="listsocial")],
    ])


def admin_admins_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_inline_btn(text="➕ Admin qo'shish", callback_data="addadmin_start", style="success")],
        [_inline_btn(text="➖ Admin o'chirish", callback_data="removeadmin_start", style="danger")],
        [_inline_btn(text="📋 Adminlar ro'yxati", callback_data="listadmins")],
    ])



def admin_settings_kb(settings: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_inline_btn(text=f"💳 Karta: {settings.get('payment_card', '—')[:18]}", callback_data="set_payment_card")],
        [_inline_btn(text=f"👤 Karta egasi: {settings.get('payment_card_owner', '—')[:24]}", callback_data="set_payment_card_owner")],
        [_inline_btn(text=f"📞 Admin username: {settings.get('admin_username', '—')[:24]}", callback_data="set_admin_username")],
        [_inline_btn(text="📝 Kontakt matni", callback_data="set_admin_contact_text")],
    ])
