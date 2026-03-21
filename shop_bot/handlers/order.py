import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import (
    get_cart, clear_cart, create_order, get_orders, get_order, get_order_items,
    get_setting, get_promo, use_promo, update_payment_screenshot
)
from keyboards.keyboards import (
    main_menu_kb, back_kb, contact_kb, delivery_type_kb,
    payment_type_kb, confirm_order_kb, order_list_kb, screenshot_kb
)
from utils.helpers import format_price, get_effective_price, cart_total, format_order_text
from utils.states import OrderState
from config import ADMIN_IDS, PAYMENT_TYPES, DELIVERY_TYPES

router = Router()


async def notify_admins(bot, text: str, order_id: int = None, kb=None):
    from keyboards.keyboards import admin_order_kb
    from database.db import get_admins, get_order
    admin_ids = list(ADMIN_IDS)
    db_admins = await get_admins()
    for a in db_admins:
        if a["id"] not in admin_ids:
            admin_ids.append(a["id"])
    order = await get_order(order_id) if order_id else None
    markup = admin_order_kb(order_id, order["status"]) if order and order_id else None
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass


@router.callback_query(F.data == "cart_checkout")
async def start_checkout(cq: CallbackQuery, state: FSMContext):
    cart = await get_cart(cq.from_user.id)
    if not cart:
        await cq.answer("Savatcha bo'sh!", show_alert=True)
        return
    orders_open = await get_setting("orders_open")
    if orders_open != "1":
        await cq.answer("😔 Hozirda buyurtmalar qabul qilinmayapti.", show_alert=True)
        return
    await cq.answer()
    await state.set_state(OrderState.full_name)
    await cq.message.answer("👤 Ismingizni kiriting:", reply_markup=back_kb())


@router.message(OrderState.full_name)
async def get_name(msg: Message, state: FSMContext):
    await state.update_data(full_name=msg.text.strip())
    await state.set_state(OrderState.phone)
    await msg.answer("📞 Telefon raqamingizni yuboring:", reply_markup=contact_kb())


@router.message(OrderState.phone, F.contact)
async def get_phone_contact(msg: Message, state: FSMContext):
    await state.update_data(phone=msg.contact.phone_number)
    await state.set_state(OrderState.address)
    await msg.answer("📍 Manzilingizni yozing:", reply_markup=back_kb())


@router.message(OrderState.phone, F.text)
async def get_phone_text(msg: Message, state: FSMContext):
    phone = msg.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(OrderState.address)
    await msg.answer("📍 Manzilingizni yozing:", reply_markup=back_kb())


@router.message(OrderState.address)
async def get_address(msg: Message, state: FSMContext):
    await state.update_data(address=msg.text.strip())
    await state.set_state(OrderState.delivery_type)
    await msg.answer("🚚 Yetkazib berish turini tanlang:", reply_markup=delivery_type_kb())


@router.message(OrderState.delivery_type)
async def get_delivery(msg: Message, state: FSMContext):
    delivery_map = {
        "🚚 Kuryer orqali": "courier",
        "🏪 Olib ketish": "pickup",
    }
    dtype = delivery_map.get(msg.text)
    if not dtype:
        await msg.answer("Iltimos, tugmadan tanlang.")
        return
    await state.update_data(delivery_type=msg.text)
    await state.set_state(OrderState.payment_type)
    await msg.answer("💳 To'lov usulini tanlang:", reply_markup=payment_type_kb())


@router.message(OrderState.payment_type)
async def get_payment(msg: Message, state: FSMContext):
    payment_opts = ["💵 Naqd", "💳 Karta o'tkazmasi", "📱 Click/Payme"]
    if msg.text not in payment_opts:
        await msg.answer("Iltimos, tugmadan tanlang.")
        return
    await state.update_data(payment_type=msg.text)
    await state.set_state(OrderState.promo_code)
    await msg.answer("🎁 Promo kodingiz bormi? (yo'q bo'lsa o'tkazib yuboring)", reply_markup=skip_promo_kb())


def skip_promo_kb():
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    kb.button(text="⏭ O'tkazib yuborish")
    kb.button(text="🔙 Orqaga")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


@router.message(OrderState.promo_code)
async def get_promo_code(msg: Message, state: FSMContext):
    from database.db import get_cart
    currency = await get_setting("currency")
    if msg.text == "⏭ O'tkazib yuborish":
        await state.update_data(promo_code=None, promo_id=None, discount_amount=0)
    else:
        code = msg.text.strip().upper()
        promo = await get_promo(code)
        if not promo:
            await msg.answer("❌ Promo kod topilmadi yoki muddati o'tgan.")
            return
        cart = await get_cart(msg.from_user.id)
        total = cart_total(cart)
        min_order = float(promo.get("min_order_amount", 0) or 0)
        if total < min_order:
            await msg.answer(f"❌ Minimal buyurtma: {format_price(min_order, currency)}")
            return
        if promo["discount_type"] == "percent":
            discount = total * float(promo["discount_value"]) / 100
        else:
            discount = float(promo["discount_value"])
        await state.update_data(
            promo_code=code,
            promo_id=promo["id"],
            discount_amount=discount
        )
        await msg.answer(f"✅ Promo kod qo'llanildi! Chegirma: -{format_price(discount, currency)}")
    await state.set_state(OrderState.comment)
    await msg.answer("💬 Izoh qoldiring (ixtiyoriy):", reply_markup=skip_kb_comment())


def skip_kb_comment():
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    kb.button(text="⏭ Izohsiz")
    kb.button(text="🔙 Orqaga")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


@router.message(OrderState.comment)
async def get_comment(msg: Message, state: FSMContext):
    comment = "" if msg.text == "⏭ Izohsiz" else msg.text.strip()
    await state.update_data(comment=comment)
    data = await state.get_data()
    cart = await get_cart(msg.from_user.id)
    currency = await get_setting("currency")
    delivery_price = float(await get_setting("delivery_price") or 0)
    free_from = float(await get_setting("free_delivery_from") or 0)
    total = cart_total(cart)
    discount = float(data.get("discount_amount", 0))
    delivery_cost = 0
    if data.get("delivery_type") == "🚚 Kuryer orqali":
        delivery_cost = 0 if total >= free_from else delivery_price

    final_total = total - discount + delivery_cost
    lines = ["📋 <b>Buyurtmangiz:</b>\n"]
    for item in cart:
        price = get_effective_price(item)
        lines.append(f"• {item['name']} x{item['quantity']} = {format_price(price * item['quantity'], currency)}")
    lines.append(f"\n👤 {data.get('full_name')}")
    lines.append(f"📞 {data.get('phone')}")
    lines.append(f"📍 {data.get('address')}")
    lines.append(f"🚚 {data.get('delivery_type')}")
    lines.append(f"💳 {data.get('payment_type')}")
    if discount > 0:
        lines.append(f"🎁 Chegirma: -{format_price(discount, currency)}")
    if delivery_cost > 0:
        lines.append(f"🚚 Yetkazib berish: {format_price(delivery_cost, currency)}")
    else:
        lines.append("🎁 Yetkazib berish: Bepul")
    lines.append(f"\n💰 <b>Jami: {format_price(final_total, currency)}</b>")
    if comment:
        lines.append(f"💬 {comment}")
    await state.update_data(final_total=final_total, delivery_cost=delivery_cost)
    await state.set_state(OrderState.confirm)
    await msg.answer("\n".join(lines), reply_markup=confirm_order_kb(), parse_mode="HTML")


@router.message(OrderState.confirm, F.text == "✅ Tasdiqlash")
async def confirm_order(msg: Message, state: FSMContext):
    data = await state.get_data()
    cart = await get_cart(msg.from_user.id)
    currency = await get_setting("currency")
    if not cart:
        await msg.answer("Savatcha bo'sh!", reply_markup=main_menu_kb())
        await state.clear()
        return
    items = []
    for item in cart:
        items.append({
            "product_id": item["product_id"],
            "product_name": item["name"],
            "quantity": item["quantity"],
            "price": get_effective_price(item),
            "size": item.get("size"),
            "color": item.get("color"),
        })
    order_data = {
        "user_id": msg.from_user.id,
        "full_name": data.get("full_name"),
        "phone": data.get("phone"),
        "address": data.get("address"),
        "delivery_type": data.get("delivery_type"),
        "payment_type": data.get("payment_type"),
        "comment": data.get("comment"),
        "promo_code": data.get("promo_code"),
        "discount_amount": data.get("discount_amount", 0),
        "total_amount": data.get("final_total"),
    }
    order_id = await create_order(order_data, items)
    if data.get("promo_id"):
        await use_promo(data["promo_id"], msg.from_user.id, order_id)
    await clear_cart(msg.from_user.id)
    await state.clear()
    success_text = (
        f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n"
        f"📦 Buyurtma ID: <code>#{order_id}</code>\n\n"
        f"Tez orada siz bilan bog'lanamiz."
    )
    payment_type = data.get("payment_type", "")
    if "Karta" in payment_type or "Click" in payment_type:
        card_numbers = await get_setting("card_numbers")
        success_text += f"\n\n💳 <b>To'lov rekvizitlari:</b>\n<code>{card_numbers}</code>"
        await state.set_state(OrderState.payment_screenshot)
        await state.update_data(pending_order_id=order_id)
        await msg.answer(success_text, parse_mode="HTML", reply_markup=screenshot_kb())
        await msg.answer("📸 To'lov chekini (screenshot) yuboring:")
    else:
        await msg.answer(success_text, reply_markup=main_menu_kb(), parse_mode="HTML")
    # Notify admins
    order = await get_order(order_id)
    order_items = await get_order_items(order_id)
    notif_text = "🛍 <b>Yangi buyurtma!</b>\n\n" + format_order_text(order, order_items, currency)
    await notify_admins(msg.bot, notif_text, order_id)


@router.message(OrderState.payment_screenshot, F.photo)
async def receive_screenshot(msg: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("pending_order_id")
    file_id = msg.photo[-1].file_id
    await update_payment_screenshot(order_id, file_id)
    await state.clear()
    await msg.answer("✅ Chek yuborildi! Admin ko'rib chiqadi.", reply_markup=main_menu_kb())
    # Notify admins about screenshot
    from keyboards.keyboards import admin_payment_kb
    for admin_id in list(ADMIN_IDS):
        try:
            await msg.bot.send_photo(
                admin_id, photo=file_id,
                caption=f"💳 <b>Buyurtma #{order_id} uchun to'lov cheki</b>",
                reply_markup=admin_payment_kb(order_id),
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.message(OrderState.confirm, F.text == "❌ Bekor qilish")
async def cancel_order(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("❌ Buyurtma bekor qilindi.", reply_markup=main_menu_kb())


# ─── MY ORDERS ───────────────────────────────────────────────────────────────

@router.message(F.text == "📦 Buyurtmalarim")
async def my_orders(msg: Message):
    orders = await get_orders(user_id=msg.from_user.id)
    if not orders:
        await msg.answer("📦 Sizda hali buyurtmalar yo'q.")
        return
    from config import ORDER_STATUSES
    currency = await get_setting("currency")
    await msg.answer("📦 <b>Buyurtmalaringiz:</b>", parse_mode="HTML")
    for o in orders[:10]:
        status = ORDER_STATUSES.get(o["status"], o["status"])
        text = (
            f"#{o['id']} — {status}\n"
            f"💰 {format_price(o['total_amount'], currency)}\n"
            f"📅 {o['created_at'][:10]}"
        )
        await msg.answer(text, reply_markup=order_list_kb(o["id"]))


@router.callback_query(F.data.startswith("order_detail:"))
async def order_detail(cq: CallbackQuery):
    order_id = int(cq.data.split(":")[1])
    order = await get_order(order_id)
    items = await get_order_items(order_id)
    if not order or order["user_id"] != cq.from_user.id:
        await cq.answer("Buyurtma topilmadi.", show_alert=True)
        return
    currency = await get_setting("currency")
    await cq.message.answer(format_order_text(order, items, currency), parse_mode="HTML")
    await cq.answer()
