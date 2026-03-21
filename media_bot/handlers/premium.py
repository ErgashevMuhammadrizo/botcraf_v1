"""Premium sotib olish va to'lov handlerlari"""

import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.database import (is_premium, get_user, create_payment,
                             update_payment_receipt, get_pending_payments, get_setting)
from utils.keyboards import premium_plans_keyboard, cancel_keyboard
from utils.helpers import fmt_date
from config.settings import PREMIUM_PRICES, ADMIN_IDS

router = Router()
logger = logging.getLogger(__name__)


class PayState(StatesGroup):
    waiting_receipt = State()
    waiting_plan = State()


PREMIUM_INFO = """
⭐ <b>MediaBot Premium</b>

<b>Nimalar qo'shiladi:</b>
✅ 1080p Full HD yuklab olish
✅ Eng yuqori sifat
✅ Tezkor navbat

<b>Narxlar:</b>
"""


@router.message(Command("premium"))
@router.message(F.text == "⭐ Premium")
async def cmd_premium(message: Message):
    user_id = message.from_user.id
    prem = await is_premium(user_id)

    if prem:
        u = await get_user(user_id)
        until = fmt_date(u.get("premium_until", ""))
        await message.answer(
            f"⭐ <b>Sizda Premium bor!</b>\n\n"
            f"📅 Muddati: <b>{until}</b>\n\n"
            f"Muddatni uzaytirish uchun quyidagi tarif tanlang:",
            parse_mode="HTML",
            reply_markup=premium_plans_keyboard()
        )
    else:
        text = PREMIUM_INFO
        for plan in PREMIUM_PRICES.values():
            text += f"  • {plan['label']}\n"
        text += "\nQuyidagi tarifdan birini tanlang 👇"
        await message.answer(text, parse_mode="HTML", reply_markup=premium_plans_keyboard())


@router.callback_query(F.data.startswith("buy_plan:"))
async def buy_plan(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    plan_key = callback.data.split(":", 1)[1]
    plan = PREMIUM_PRICES.get(plan_key)
    if not plan:
        await callback.message.edit_text("❌ Noto'g'ri tarif.")
        return

    await state.update_data(selected_plan=plan_key, plan_amount=plan["amount"])
    await state.set_state(PayState.waiting_receipt)

    payment_card = await get_setting('payment_card', '8600 0000 0000 0000')
    payment_owner = await get_setting('payment_card_owner', 'Ism Familiya')
    await callback.message.edit_text(
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"📦 Tarif: <b>{plan['label']}</b>\n"
        f"💰 Summa: <b>{plan['amount']:,} so'm</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Karta: <code>{payment_card}</code>\n"
        f"Egasi: <b>{payment_owner}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ To'lovni amalga oshirgach, <b>chek rasmini</b> (screenshot) yuboring.\n"
        f"Admin tekshirib, Premium faollashtiriladi.\n\n"
        f"⏱ Tekshirish vaqti: 5–30 daqiqa",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )


@router.message(PayState.waiting_receipt, F.photo)
async def receipt_received(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    plan_key = data.get("selected_plan")
    amount = data.get("plan_amount", 0)
    plan = PREMIUM_PRICES.get(plan_key, {})
    user = message.from_user

    # Eng yuqori sifatli fotodan file_id olamiz
    photo = message.photo[-1]
    file_id = photo.file_id

    # To'lovni bazaga yozamiz
    payment_id = await create_payment(user.id, plan_key, amount)
    await update_payment_receipt(payment_id, file_id)

    await message.answer(
        f"✅ <b>Chek qabul qilindi!</b>\n\n"
        f"🆔 To'lov ID: <code>#{payment_id}</code>\n"
        f"📦 Tarif: {plan.get('label', plan_key)}\n\n"
        f"⏳ Admin tekshirmoqda. Tasdiqlangach xabar keladi.\n"
        f"Odatda 5–30 daqiqa ketadi.",
        parse_mode="HTML"
    )

    # Adminlarga xabar yuborish
    username = f"@{user.username}" if user.username else user.full_name
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id,
                photo=file_id,
                caption=(
                    f"💳 <b>Yangi to'lov!</b>\n\n"
                    f"👤 {username} (<code>{user.id}</code>)\n"
                    f"📦 Tarif: {plan.get('label', plan_key)}\n"
                    f"💰 Summa: {amount:,} so'm\n"
                    f"🆔 To'lov #{payment_id}"
                ),
                parse_mode="HTML",
                reply_markup=_payment_admin_keyboard(payment_id)
            )
        except Exception as e:
            logger.warning(f"Admin {admin_id} ga xabar yuborilmadi: {e}")

    await state.clear()


@router.message(PayState.waiting_receipt)
async def receipt_not_photo(message: Message):
    await message.answer(
        "📸 Iltimos, to'lov chekining <b>rasmini (screenshot)</b> yuboring.",
        parse_mode="HTML"
    )


def _payment_admin_keyboard(payment_id: int):
    from utils.keyboards import payment_confirm_keyboard
    return payment_confirm_keyboard(payment_id)
