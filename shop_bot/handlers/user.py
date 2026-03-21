import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from database.db import (
    get_setting, get_categories, get_products, get_product,
    add_to_cart, get_cart, update_cart_quantity, remove_from_cart,
    clear_cart, toggle_favorite, get_favorites, is_favorite, upsert_user
)
from keyboards.keyboards import (
    main_menu_kb, categories_kb, product_list_kb, product_detail_kb,
    cart_item_kb, cart_bottom_kb, back_kb
)
from utils.helpers import format_price, get_effective_price, parse_json_field, cart_total
from utils.states import SearchState

router = Router()

ITEMS_PER_PAGE = 5


# ─── START ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await upsert_user(msg.from_user.id, msg.from_user.username or "", msg.from_user.full_name or "")
    shop_name = await get_setting("shop_name")
    welcome_text = await get_setting("welcome_text")
    text = f"<b>{shop_name}</b>\n\n{welcome_text}"
    await msg.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")


@router.message(F.text == "🔙 Orqaga")
async def go_back(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("🏠 Asosiy menyu", reply_markup=main_menu_kb())


# ─── PRODUCTS LIST ───────────────────────────────────────────────────────────

@router.message(F.text == "🛍 Mahsulotlar")
async def show_products(msg: Message):
    products = await get_products()
    if not products:
        await msg.answer("😔 Hozircha mahsulotlar mavjud emas.")
        return
    currency = await get_setting("currency")
    for p in products[:10]:
        await _send_product_card(msg, p, currency)


async def _send_product_card(msg: Message, p: dict, currency: str):
    images = parse_json_field(p.get("images"))
    price = get_effective_price(p)
    old_price_str = ""
    if p.get("discount_price") and float(p.get("discount_price", 0)) > 0:
        old_price_str = f"\n<s>{format_price(p['price'], currency)}</s>"
    stock_str = "✅ Mavjud" if p.get("stock", 0) > 0 else "❌ Mavjud emas"
    text = (
        f"<b>{p['name']}</b>\n"
        f"💰 {format_price(price, currency)}{old_price_str}\n"
        f"{stock_str}"
    )
    kb = product_list_kb(p["id"])
    if images:
        try:
            await msg.answer_photo(photo=images[0], caption=text, reply_markup=kb, parse_mode="HTML")
            return
        except Exception:
            pass
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")


# ─── CATEGORIES ──────────────────────────────────────────────────────────────

@router.message(F.text == "📂 Kategoriyalar")
async def show_categories(msg: Message):
    cats = await get_categories()
    if not cats:
        await msg.answer("Kategoriyalar mavjud emas.")
        return
    await msg.answer("📂 Kategoriyani tanlang:", reply_markup=categories_kb(cats))


@router.callback_query(F.data.startswith("cat_products:"))
async def show_cat_products(cq: CallbackQuery):
    cat_id = int(cq.data.split(":")[1])
    products = await get_products(category_id=cat_id)
    currency = await get_setting("currency")
    await cq.message.delete()
    if not products:
        await cq.message.answer("😔 Bu kategoriyada mahsulot yo'q.")
        return
    for p in products[:10]:
        await _send_product_card(cq.message, p, currency)
    await cq.answer()


# ─── PRODUCT DETAIL ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("product_detail:"))
async def product_detail(cq: CallbackQuery):
    product_id = int(cq.data.split(":")[1])
    p = await get_product(product_id)
    if not p:
        await cq.answer("Mahsulot topilmadi.", show_alert=True)
        return
    currency = await get_setting("currency")
    images = parse_json_field(p.get("images"))
    sizes = parse_json_field(p.get("sizes"))
    colors = parse_json_field(p.get("colors"))
    price = get_effective_price(p)
    is_fav = await is_favorite(cq.from_user.id, product_id)
    lines = [f"<b>{p['name']}</b>"]
    if p.get("description"):
        lines.append(f"\n📝 {p['description']}")
    lines.append(f"\n💰 {format_price(price, currency)}")
    if p.get("discount_price") and float(p.get("discount_price", 0)) > 0:
        lines.append(f"<s>{format_price(p['price'], currency)}</s>")
    if p.get("cat_name"):
        lines.append(f"📂 {p['cat_name']}")
    if sizes:
        lines.append(f"📏 O'lchamlar: {', '.join(sizes)}")
    if colors:
        lines.append(f"🎨 Ranglar: {', '.join(colors)}")
    stock = p.get("stock", 0)
    lines.append(f"{'✅ Mavjud' if stock > 0 else '❌ Mavjud emas'} ({stock} dona)")
    text = "\n".join(lines)
    kb = product_detail_kb(product_id, is_fav)
    if images:
        media = [InputMediaPhoto(media=img) for img in images[:5]]
        try:
            if len(media) > 1:
                await cq.message.answer_media_group(media=media)
                await cq.message.answer(text, reply_markup=kb, parse_mode="HTML")
            else:
                await cq.message.answer_photo(photo=images[0], caption=text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await cq.message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        await cq.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await cq.answer()


# ─── CART ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cart_add:"))
async def cart_add(cq: CallbackQuery):
    product_id = int(cq.data.split(":")[1])
    p = await get_product(product_id)
    if not p:
        await cq.answer("Mahsulot topilmadi.", show_alert=True)
        return
    if p.get("stock", 0) <= 0:
        await cq.answer("😔 Mahsulot tugagan.", show_alert=True)
        return
    await add_to_cart(cq.from_user.id, product_id)
    await cq.answer("✅ Savatchaga qo'shildi!", show_alert=False)


@router.message(F.text == "🛒 Savatcha")
async def show_cart(msg: Message):
    cart = await get_cart(msg.from_user.id)
    if not cart:
        await msg.answer("🛒 Savatchangiz bo'sh.")
        return
    currency = await get_setting("currency")
    total = cart_total(cart)
    await msg.answer("🛒 <b>Savatchangiz:</b>", parse_mode="HTML")
    for item in cart:
        price = get_effective_price(item)
        text = (
            f"<b>{item['name']}</b>\n"
            f"💰 {format_price(price, currency)} x {item['quantity']} = "
            f"{format_price(price * item['quantity'], currency)}"
        )
        if item.get("size"):
            text += f"\n📏 {item['size']}"
        if item.get("color"):
            text += f"\n🎨 {item['color']}"
        await msg.answer(text, reply_markup=cart_item_kb(item["id"], item["quantity"]), parse_mode="HTML")
    await msg.answer(
        f"💰 <b>Jami: {format_price(total, currency)}</b>",
        reply_markup=cart_bottom_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("cart_inc:"))
async def cart_inc(cq: CallbackQuery):
    cart_id = int(cq.data.split(":")[1])
    cart = await get_cart(cq.from_user.id)
    item = next((i for i in cart if i["id"] == cart_id), None)
    if item:
        await update_cart_quantity(cart_id, item["quantity"] + 1)
        await cq.answer("➕ Ko'paytirildi")
        await cq.message.edit_reply_markup(
            reply_markup=cart_item_kb(cart_id, item["quantity"] + 1)
        )


@router.callback_query(F.data.startswith("cart_dec:"))
async def cart_dec(cq: CallbackQuery):
    cart_id = int(cq.data.split(":")[1])
    cart = await get_cart(cq.from_user.id)
    item = next((i for i in cart if i["id"] == cart_id), None)
    if item:
        new_qty = item["quantity"] - 1
        await update_cart_quantity(cart_id, new_qty)
        if new_qty <= 0:
            await cq.message.delete()
            await cq.answer("❌ O'chirildi")
        else:
            await cq.answer("➖ Kamaytirildi")
            await cq.message.edit_reply_markup(reply_markup=cart_item_kb(cart_id, new_qty))


@router.callback_query(F.data.startswith("cart_remove:"))
async def cart_remove(cq: CallbackQuery):
    cart_id = int(cq.data.split(":")[1])
    await remove_from_cart(cart_id)
    await cq.message.delete()
    await cq.answer("❌ O'chirildi")


@router.callback_query(F.data == "cart_clear")
async def cart_clear(cq: CallbackQuery):
    await clear_cart(cq.from_user.id)
    await cq.message.edit_text("🧹 Savatcha tozalandi.")
    await cq.answer()


# ─── FAVORITES ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("fav_toggle:"))
async def fav_toggle(cq: CallbackQuery):
    product_id = int(cq.data.split(":")[1])
    is_added = await toggle_favorite(cq.from_user.id, product_id)
    if is_added:
        await cq.answer("❤️ Saralanganlarga qo'shildi!", show_alert=False)
    else:
        await cq.answer("💔 Saralanganlarden o'chirildi", show_alert=False)
    # Refresh detail button
    try:
        kb = product_detail_kb(product_id, is_added)
        await cq.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass


@router.message(F.text == "❤️ Saralanganlar")
async def show_favorites(msg: Message):
    favs = await get_favorites(msg.from_user.id)
    if not favs:
        await msg.answer("❤️ Saralanganlar ro'yxatingiz bo'sh.")
        return
    currency = await get_setting("currency")
    for item in favs:
        p = await get_product(item["product_id"])
        if p:
            await _send_product_card(msg, p, currency)


# ─── SEARCH ──────────────────────────────────────────────────────────────────

@router.message(F.text == "🔎 Qidirish")
async def start_search(msg: Message, state: FSMContext):
    await state.set_state(SearchState.query)
    await msg.answer("🔎 Mahsulot nomini kiriting:", reply_markup=back_kb())


@router.message(SearchState.query)
async def do_search(msg: Message, state: FSMContext):
    await state.clear()
    query = msg.text.strip()
    products = await get_products(search=query)
    currency = await get_setting("currency")
    if not products:
        await msg.answer(f"😔 '{query}' bo'yicha hech narsa topilmadi.", reply_markup=main_menu_kb())
        return
    await msg.answer(f"🔎 <b>{len(products)} ta natija:</b>", parse_mode="HTML", reply_markup=main_menu_kb())
    for p in products[:10]:
        await _send_product_card(msg, p, currency)


# ─── INFO PAGES ──────────────────────────────────────────────────────────────

@router.message(F.text == "☎️ Aloqa")
async def show_contact(msg: Message):
    phone = await get_setting("shop_phone")
    address = await get_setting("shop_address")
    hours = await get_setting("shop_hours")
    text = (
        "☎️ <b>Aloqa</b>\n\n"
        f"📞 {phone}\n"
        f"📍 {address}\n"
        f"🕐 Ish vaqti: {hours}"
    )
    await msg.answer(text, parse_mode="HTML")


@router.message(F.text == "ℹ️ Do'kon haqida")
async def show_about(msg: Message):
    about = await get_setting("shop_about")
    delivery = await get_setting("delivery_terms")
    payment = await get_setting("payment_terms")
    returns = await get_setting("return_policy")
    text = (
        f"ℹ️ <b>Do'kon haqida</b>\n\n{about}\n\n"
        f"🚚 <b>Yetkazib berish:</b>\n{delivery}\n\n"
        f"💳 <b>To'lov:</b>\n{payment}\n\n"
        f"🔄 <b>Qaytarish:</b>\n{returns}"
    )
    await msg.answer(text, parse_mode="HTML")


@router.message(F.text == "🎁 Aksiyalar")
async def show_promos(msg: Message):
    from database.db import get_all_promos
    promos = await get_all_promos()
    active = [p for p in promos if p.get("is_active")]
    if not active:
        await msg.answer("😔 Hozircha aksiyalar mavjud emas.")
        return
    lines = ["🎁 <b>Joriy aksiyalar:</b>\n"]
    for p in active:
        if p["discount_type"] == "percent":
            disc = f"{p['discount_value']:.0f}%"
        else:
            disc = await _fmt(p["discount_value"])
        lines.append(f"🏷 <code>{p['code']}</code> — {disc} chegirma")
        if p.get("min_order_amount") and float(p["min_order_amount"]) > 0:
            lines.append(f"   Minimal: {await _fmt(p['min_order_amount'])}")
    await msg.answer("\n".join(lines), parse_mode="HTML")


async def _fmt(val):
    currency = await get_setting("currency")
    return format_price(float(val), currency)
