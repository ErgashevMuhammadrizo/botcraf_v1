"""To'liq admin panel"""

import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.database import (
    get_stats, ban_user, unban_user, get_all_user_ids,
    get_pending_payments, approve_payment, reject_payment,
    set_premium, revoke_premium, add_channel, remove_channel,
    get_active_channels, get_setting, set_setting
)
from utils.keyboards import admin_keyboard, back_to_admin, payment_confirm_keyboard
from utils.helpers import fmt_date
from config.settings import ADMIN_IDS, PREMIUM_PRICES

router = Router()
logger = logging.getLogger(__name__)


def admin_only(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AdminState(StatesGroup):
    broadcast_msg = State()
    give_premium_id = State()
    give_premium_plan = State()
    ban_id = State()
    unban_id = State()
    add_channel_data = State()
    remove_channel_id = State()
    setting_key = State()


# ─── ASOSIY PANEL ─────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not admin_only(message.from_user.id): return
    await _show_admin_panel(message)


async def _show_admin_panel(message: Message):
    await message.answer(
        "⚙️ <b>Admin Panel</b>",
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


@router.callback_query(F.data == "adm:main")
async def adm_main(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return await callback.answer("🚫 Ruxsat yo'q", show_alert=True)
    await callback.message.edit_text("⚙️ <b>Admin Panel</b>",
                                      parse_mode="HTML", reply_markup=admin_keyboard())
    await callback.answer()


# ─── STATISTIKA ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:stats")
async def adm_stats(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return await callback.answer("🚫", show_alert=True)
    s = await get_stats()
    await callback.message.edit_text(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{s['total_users']}</b>\n"
        f"⭐ Premium: <b>{s['premium_users']}</b>\n"
        f"📥 Yuklab olishlar: <b>{s['total_downloads']}</b>\n"
        f"💳 Kutayotgan to'lovlar: <b>{s['pending_payments']}</b>\n\n"
        f"▶️ YouTube: {s['youtube']}\n"
        f"📸 Instagram: {s['instagram']}\n"
        f"🎵 TikTok: {s['tiktok']}",
        parse_mode="HTML", reply_markup=back_to_admin()
    )
    await callback.answer()


# ─── TO'LOVLAR ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:payments")
async def adm_payments(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return await callback.answer("🚫", show_alert=True)
    await callback.answer()

    payments = await get_pending_payments()
    if not payments:
        await callback.message.edit_text(
            "💳 Kutayotgan to'lovlar yo'q.",
            reply_markup=back_to_admin()
        )
        return

    await callback.message.edit_text(
        f"💳 <b>Kutayotgan to'lovlar: {len(payments)} ta</b>\n\nQuyida har biri alohida ko'rsatiladi.",
        parse_mode="HTML", reply_markup=back_to_admin()
    )

    for p in payments:
        plan = PREMIUM_PRICES.get(p["plan"], {}).get("label", p["plan"])
        username = f"@{p['username']}" if p.get("username") else p.get("full_name", "—")
        caption = (
            f"💳 <b>To'lov #{p['id']}</b>\n\n"
            f"👤 {username} (<code>{p['user_id']}</code>)\n"
            f"📦 Tarif: {plan}\n"
            f"💰 Summa: {p['amount']:,} so'm\n"
            f"📅 Sana: {fmt_date(p['created_at'])}"
        )
        try:
            if p.get("receipt_file"):
                await callback.message.answer_photo(
                    photo=p["receipt_file"],
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=payment_confirm_keyboard(p["id"])
                )
            else:
                await callback.message.answer(caption, parse_mode="HTML",
                                               reply_markup=payment_confirm_keyboard(p["id"]))
        except Exception as e:
            logger.warning(f"To'lov ko'rsatishda xato: {e}")


@router.callback_query(F.data.startswith("pay_approve:"))
async def pay_approve(callback: CallbackQuery, bot: Bot):
    if not admin_only(callback.from_user.id):
        return await callback.answer("🚫", show_alert=True)

    payment_id = int(callback.data.split(":", 1)[1])
    result = await approve_payment(payment_id, callback.from_user.id)

    if not result:
        await callback.answer("❌ To'lov topilmadi", show_alert=True)
        return

    plan = PREMIUM_PRICES.get(result["plan"], {}).get("label", result["plan"])
    until_str = result["until"].strftime("%d.%m.%Y")

    note = f"\n\n✅ <b>TASDIQLANDI</b> ({callback.from_user.full_name})"
    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=callback.message.caption + note, parse_mode="HTML")
        else:
            await callback.message.edit_text((callback.message.text or '') + note, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("✅ Premium berildi!")

    # Foydalanuvchiga xabar
    try:
        await bot.send_message(
            result["user_id"],
            f"🎉 <b>Premium faollashtirildi!</b>\n\n"
            f"⭐ Tarif: {plan}\n"
            f"📅 Muddati: <b>{until_str}</b> gacha\n\n"
            f"Endi 1080p va eng yuqori sifatda yuklab olishingiz mumkin!",
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("pay_reject:"))
async def pay_reject(callback: CallbackQuery, bot: Bot):
    if not admin_only(callback.from_user.id):
        return await callback.answer("🚫", show_alert=True)

    payment_id = int(callback.data.split(":", 1)[1])
    user_id = await reject_payment(payment_id, callback.from_user.id)

    note = f"\n\n❌ <b>RAD ETILDI</b> ({callback.from_user.full_name})"
    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=callback.message.caption + note, parse_mode="HTML")
        else:
            await callback.message.edit_text((callback.message.text or '') + note, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("❌ Rad etildi")

    if user_id:
        try:
            await bot.send_message(
                user_id,
                "❌ <b>To'lovingiz tasdiqlanmadi.</b>\n\n"
                "Muammo bo'lsa admin bilan bog'laning.",
                parse_mode="HTML"
            )
        except Exception:
            pass


# ─── PREMIUM BERISH (qo'lda) ──────────────────────────────────────────────────

@router.callback_query(F.data == "adm:give_premium")
async def adm_give_premium(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id):
        return await callback.answer("🚫", show_alert=True)
    await callback.answer()
    await callback.message.answer(
        "👑 <b>Premium berish</b>\n\nFoydalanuvchi ID sini yuboring:",
        parse_mode="HTML"
    )
    await state.set_state(AdminState.give_premium_id)


@router.message(AdminState.give_premium_id)
async def adm_give_premium_id(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id): return
    if not message.text.isdigit():
        return await message.answer("❌ Faqat raqam yuboring.")
    await state.update_data(target_id=int(message.text))
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for k, v in PREMIUM_PRICES.items():
        b.button(text=v["label"], callback_data=f"adm_plan:{k}")
    await message.answer("Tarifni tanlang:", reply_markup=b.as_markup())
    await state.set_state(AdminState.give_premium_plan)


@router.callback_query(F.data.startswith("adm_plan:"), AdminState.give_premium_plan)
async def adm_give_premium_plan(callback: CallbackQuery, state: FSMContext, bot: Bot):
    plan_key = callback.data.split(":", 1)[1]
    data = await state.get_data()
    target_id = data.get("target_id")
    until = await set_premium(target_id, plan_key)
    plan_label = PREMIUM_PRICES.get(plan_key, {}).get("label", plan_key)
    until_str = until.strftime("%d.%m.%Y")

    await callback.message.edit_text(
        f"✅ <code>{target_id}</code> ga Premium berildi!\n"
        f"📦 {plan_label}\n📅 {until_str} gacha"
    )
    await callback.answer()
    try:
        await bot.send_message(
            target_id,
            f"🎉 <b>Admindan Premium sovg'a!</b>\n\n"
            f"⭐ Tarif: {plan_label}\n📅 {until_str} gacha",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await state.clear()


# ─── BAN/UNBAN ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:ban_menu")
async def adm_ban_menu(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return await callback.answer("🚫", show_alert=True)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="🚫 Ban qilish", callback_data="adm:do_ban")
    b.button(text="✅ Unban qilish", callback_data="adm:do_unban")
    b.button(text="⬅️ Orqaga", callback_data="adm:main")
    b.adjust(2)
    await callback.message.edit_text("Ban/Unban:", reply_markup=b.as_markup())
    await callback.answer()


@router.callback_query(F.data == "adm:do_ban")
async def adm_do_ban(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id): return
    await callback.message.answer("🚫 Ban qilish uchun user_id yuboring:")
    await state.set_state(AdminState.ban_id)
    await callback.answer()


@router.message(AdminState.ban_id)
async def adm_ban_exec(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id): return
    if not message.text.isdigit():
        return await message.answer("Raqam yuboring.")
    uid = int(message.text)
    await ban_user(uid)
    await message.answer(f"🚫 {uid} ban qilindi.")
    await state.clear()


@router.callback_query(F.data == "adm:do_unban")
async def adm_do_unban(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id): return
    await callback.message.answer("✅ Unban uchun user_id yuboring:")
    await state.set_state(AdminState.unban_id)
    await callback.answer()


@router.message(AdminState.unban_id)
async def adm_unban_exec(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id): return
    if not message.text.isdigit():
        return await message.answer("Raqam yuboring.")
    uid = int(message.text)
    await unban_user(uid)
    await message.answer(f"✅ {uid} unban qilindi.")
    await state.clear()


# ─── BROADCAST ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:broadcast")
async def adm_broadcast(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id):
        return await callback.answer("🚫", show_alert=True)
    await callback.message.answer(
        "📢 Barcha foydalanuvchilarga xabar yuboring\n"
        "(HTML format qo'llab-quvvatlanadi):"
    )
    await state.set_state(AdminState.broadcast_msg)
    await callback.answer()


@router.message(AdminState.broadcast_msg)
async def adm_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not admin_only(message.from_user.id):
        await state.clear(); return

    user_ids = await get_all_user_ids()
    total = len(user_ids)
    success = failed = 0
    status = await message.answer(f"📤 Yuborilmoqda 0/{total}...")

    for i, uid in enumerate(user_ids, 1):
        try:
            await bot.send_message(uid, message.html_text, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1
        if i % 25 == 0:
            try:
                await status.edit_text(f"📤 {i}/{total}...")
            except Exception:
                pass
        await asyncio.sleep(0.05)

    await status.edit_text(
        f"✅ Tugadi!\n📤 {total} ta\n✅ {success} muvaffaqiyatli\n❌ {failed} xato"
    )
    await state.clear()


# ─── KANALLAR ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:channels")
async def adm_channels(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return await callback.answer("🚫", show_alert=True)
    await callback.answer()

    channels = await get_active_channels()
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    b.button(text="➕ Kanal qo'shish", callback_data="adm:add_channel")
    b.button(text="➖ Kanal o'chirish", callback_data="adm:del_channel")
    b.button(text="⬅️ Orqaga", callback_data="adm:main")
    b.adjust(2)

    if channels:
        ch_list = "\n".join(f"• {c['title']} (@{c['username']}) — ID: {c['channel_id']}"
                            for c in channels)
        text = f"📡 <b>Aktiv kanallar ({len(channels)}):</b>\n\n{ch_list}"
    else:
        text = "📡 <b>Majburiy obuna kanallari yo'q.</b>\nQo'shish uchun tugmani bosing."

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=b.as_markup())


@router.callback_query(F.data == "adm:add_channel")
async def adm_add_channel(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id): return
    await callback.message.answer(
        "➕ Kanal qo'shish uchun quyidagi formatda yuboring:\n\n"
        "<code>kanal_id|username|Kanal nomi</code>\n\n"
        "Misol:\n<code>-1001234567890|my_channel|Mening kanalim</code>\n\n"
        "Kanal ID sini @username_to_id_bot orqali bilib oling.",
        parse_mode="HTML"
    )
    await state.set_state(AdminState.add_channel_data)
    await callback.answer()


@router.message(AdminState.add_channel_data)
async def adm_add_channel_exec(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id): return
    try:
        parts = message.text.strip().split("|")
        if len(parts) != 3:
            raise ValueError("Format xato")
        ch_id, username, title = [p.strip() for p in parts]
        username = username.lstrip("@")
        await add_channel(ch_id, username, title)
        await message.answer(f"✅ Kanal qo'shildi: {title} (@{username})")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}\nFormat: kanal_id|username|nomi")
    await state.clear()


@router.callback_query(F.data == "adm:del_channel")
async def adm_del_channel(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id): return
    await callback.message.answer("➖ O'chirish uchun kanal_id yuboring:")
    await state.set_state(AdminState.remove_channel_id)
    await callback.answer()


@router.message(AdminState.remove_channel_id)
async def adm_del_channel_exec(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id): return
    await remove_channel(message.text.strip())
    await message.answer("✅ Kanal o'chirildi.")
    await state.clear()


# ─── SOZLAMALAR ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:settings")
async def adm_settings(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        return await callback.answer("🚫", show_alert=True)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    payment_card = await get_setting('payment_card', '8600 0000 0000 0000')
    payment_owner = await get_setting('payment_card_owner', 'Ism Familiya')
    b = InlineKeyboardBuilder()
    b.button(text="💳 Karta raqami", callback_data="adm:set_card")
    b.button(text="👤 Karta egasi", callback_data="adm:set_owner")
    b.button(text="⬅️ Orqaga", callback_data="adm:main")
    b.adjust(1)
    await callback.message.edit_text(
        f"⚙️ <b>Sozlamalar</b>\n\n💳 Karta: <code>{payment_card}</code>\n👤 Egasi: <b>{payment_owner}</b>",
        parse_mode="HTML", reply_markup=b.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.in_(["adm:set_card", "adm:set_owner"]))
async def adm_set_setting(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id):
        return await callback.answer("🚫", show_alert=True)
    key = 'payment_card' if callback.data == 'adm:set_card' else 'payment_card_owner'
    await state.set_state(AdminState.setting_key)
    await state.update_data(setting_key=key)
    prompt = '💳 Yangi karta raqamini yuboring:' if key == 'payment_card' else '👤 Yangi karta egasini yuboring:'
    await callback.message.answer(prompt)
    await callback.answer()


@router.message(AdminState.setting_key)
async def adm_save_setting(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    data = await state.get_data()
    key = data.get('setting_key')
    value = (message.text or '').strip()
    if not key or not value:
        await message.answer("❌ Qiymat bo'sh bo'lmasin.")
        return
    await set_setting(key, value)
    await state.clear()
    await message.answer('✅ Saqlandi.')


# ─── SHORTCUT BUYRUQLAR ───────────────────────────────────────────────────────

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not admin_only(message.from_user.id): return
    s = await get_stats()
    await message.answer(
        f"📊 Users: {s['total_users']} | Premium: {s['premium_users']}\n"
        f"📥 Downloads: {s['total_downloads']}\n"
        f"💳 Pending: {s['pending_payments']}"
    )


@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not admin_only(message.from_user.id): return
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        return await message.answer("Format: /ban <user_id>")
    await ban_user(int(args[1]))
    await message.answer(f"🚫 {args[1]} ban qilindi.")


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not admin_only(message.from_user.id): return
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        return await message.answer("Format: /unban <user_id>")
    await unban_user(int(args[1]))
    await message.answer(f"✅ {args[1]} unban qilindi.")


@router.message(Command("premium"))
async def cmd_give_premium(message: Message):
    """Admin /premium <user_id> <plan> — qo'lda premium berish"""
    if not admin_only(message.from_user.id): return
    args = message.text.split()
    if len(args) == 3 and args[1].isdigit() and args[2] in PREMIUM_PRICES:
        uid = int(args[1])
        until = await set_premium(uid, args[2])
        await message.answer(
            f"✅ {uid} ga premium berildi. {until.strftime('%d.%m.%Y')} gacha."
        )
    else:
        plans = ", ".join(PREMIUM_PRICES.keys())
        await message.answer(f"Format: /premium <user_id> <plan>\nPlanlar: {plans}")
