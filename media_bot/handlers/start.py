import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from utils.database import add_or_update_user, is_banned, is_premium, get_user
from utils.keyboards import main_menu
from utils.helpers import fmt_date

router = Router()
logger = logging.getLogger(__name__)

WELCOME = """
🎬 <b>MediaBot'ga xush kelibsiz!</b>

Men sizga quyidagi platformalardan media yuklab olishga yordam beraman:

▶️ <b>YouTube</b> — video, shorts
📸 <b>Instagram</b> — post, reels
🎵 <b>TikTok</b> — video

━━━━━━━━━━━━━━━━━━
<b>Bepul:</b> 480p · 720p · Audio
<b>⭐ Premium:</b> 1080p · Eng yaxshi sifat

Havola yuboring — yuklab beraman! 👇
"""

HELP_TEXT = """
ℹ️ <b>Yordam</b>

<b>Qanday ishlatish:</b>
Shunchaki YouTube, Instagram yoki TikTok havolasini yuboring.

<b>Sifatlar:</b>
• 📱 480p — bepul
• 📺 720p — bepul
• 🎵 Audio MP3 — bepul
• 📹 1080p — ⭐ Premium
• 🔥 Eng yaxshi — ⭐ Premium

<b>⭐ Premium afzalliklari:</b>
• 1080p va eng yuqori sifat
• Tezkor yuklab olish
• Ustunlik navbati

<b>Cheklovlar:</b>
• Max fayl: 50 MB
• Xususiy postlar yuklanmaydi

❓ Muammo bo'lsa admin bilan bog'laning.
"""


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    await add_or_update_user(user.id, user.username or "", user.full_name)

    if await is_banned(user.id):
        await message.answer("🚫 Siz botdan foydalanish huquqiga ega emassiz.")
        return

    prem = await is_premium(user.id)
    await message.answer(WELCOME, parse_mode="HTML", reply_markup=main_menu(prem))
    logger.info(f"Start: {user.id} | @{user.username}")


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Yordam")
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("me"))
async def cmd_me(message: Message):
    u = await get_user(message.from_user.id)
    if not u:
        await message.answer("Siz hali ro'yxatdan o'tmagansiz. /start bosing.")
        return
    prem = await is_premium(message.from_user.id)
    prem_until = fmt_date(u.get("premium_until") or "") if prem else "Yo'q"
    await message.answer(
        f"👤 <b>Profil</b>\n\n"
        f"🆔 ID: <code>{u['user_id']}</code>\n"
        f"👤 Ism: {u['full_name']}\n"
        f"⭐ Premium: {'Ha ✅' if prem else 'Yo\'q'}\n"
        f"📅 Premium muddati: {prem_until}\n"
        f"📅 Qo'shilgan: {fmt_date(u.get('joined_at', ''))}",
        parse_mode="HTML"
    )
