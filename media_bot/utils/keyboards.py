"""Barcha klaviaturalar"""

from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config.settings import QUALITY_OPTIONS, PREMIUM_PRICES


def main_menu(is_premium_user: bool = False) -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    b.button(text="📥 Yuklab olish")
    b.button(text="⭐ Premium")
    b.button(text="📊 Statistika")
    b.button(text="ℹ️ Yordam")
    b.adjust(2)
    return b.as_markup(resize_keyboard=True)


def quality_keyboard(url: str, user_is_premium: bool = False) -> InlineKeyboardMarkup:
    """Sifat tanlash — premium tugmalar lock ko'rsatadi"""
    # URL ni qisqartirish (Telegram 64 bayt limit uchun)
    # callback_data hajmi 64 baytdan oshmasligi kerak!
    # Shu sababli URL ni ID ga almashtiramiz — URL ni state'da saqlaymiz
    b = InlineKeyboardBuilder()
    for key, val in QUALITY_OPTIONS.items():
        if val["premium"] and not user_is_premium:
            label = f"🔒 {val['label']}"
            cb = f"q_locked:{key}"
        else:
            label = val["label"]
            cb = f"q:{key}"
        b.button(text=label, callback_data=cb)
    b.button(text="❌ Bekor", callback_data="cancel")
    b.adjust(1)
    return b.as_markup()


def premium_plans_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for plan_key, plan in PREMIUM_PRICES.items():
        b.button(text=plan["label"], callback_data=f"buy_plan:{plan_key}")
    b.button(text="❌ Yopish", callback_data="cancel")
    b.adjust(1)
    return b.as_markup()


def payment_confirm_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_approve:{payment_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject:{payment_id}"),
    ]])


def admin_keyboard() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📊 Statistika", callback_data="adm:stats")
    b.button(text="💳 Kutayotgan to'lovlar", callback_data="adm:payments")
    b.button(text="📢 Xabar yuborish", callback_data="adm:broadcast")
    b.button(text="📡 Kanallar", callback_data="adm:channels")
    b.button(text="👑 Premium berish", callback_data="adm:give_premium")
    b.button(text="🚫 Ban/Unban", callback_data="adm:ban_menu")
    b.button(text="⚙️ Sozlamalar", callback_data="adm:settings")
    b.adjust(2)
    return b.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")
    ]])


def back_to_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Admin panel", callback_data="adm:main")
    ]])


def subscribe_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Majburiy obuna klaviaturasi"""
    b = InlineKeyboardBuilder()
    for ch in channels:
        username = ch.get("username", "")
        title = ch.get("title", "Kanal")
        if username:
            b.button(text=f"📢 {title}", url=f"https://t.me/{username}")
    b.button(text="✅ Obuna bo'ldim", callback_data="check_sub")
    b.adjust(1)
    return b.as_markup()
