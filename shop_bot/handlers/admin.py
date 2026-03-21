import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from database.db import (
    get_products, get_product, add_product, update_product, delete_product,
    get_categories, get_category, add_category, update_category, delete_category,
    get_orders, get_order, get_order_items, update_order_status,
    get_all_users, ban_user, get_statistics, get_setting, set_setting,
    get_all_promos, add_promo, get_admins, add_admin, remove_admin,
    confirm_payment
)
from keyboards.keyboards import (
    admin_main_kb, admin_products_kb, admin_categories_kb,
    admin_product_item_kb, admin_category_item_kb, admin_order_kb,
    admin_orders_filter_kb, admin_payment_kb, admin_user_kb,
    admin_promo_kb, broadcast_target_kb, settings_kb, back_kb
)
from utils.helpers import format_price, parse_json_field, format_order_text
from utils.states import (
    ProductState, CategoryState, PromoState, BroadcastState, SettingsState, AdminState
)
from middlewares.middlewares import is_admin
from config import ADMIN_IDS

router = Router()


def admin_filter():
    from aiogram.filters import Filter
    class AdminFilter(Filter):
        async def __call__(self, msg) -> bool:
            uid = msg.from_user.id if hasattr(msg, 'from_user') else msg.message.from_user.id
            return await is_admin(uid)
    return AdminFilter()


# ─── ADMIN ENTRY ─────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        await msg.answer("❌ Ruxsat yo'q.")
        return
    await state.clear()
    await msg.answer("👨‍💼 <b>Admin panel</b>", reply_markup=admin_main_kb(), parse_mode="HTML")


@router.message(F.text == "🔙 Admin panel")
async def back_admin(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.clear()
    await msg.answer("👨‍💼 Admin panel", reply_markup=admin_main_kb())


@router.message(F.text == "🔙 User panel")
async def back_user(msg: Message, state: FSMContext):
    await state.clear()
    from keyboards.keyboards import main_menu_kb
    await msg.answer("🏠 Asosiy menyu", reply_markup=main_menu_kb())


# ─── PRODUCTS MANAGEMENT ─────────────────────────────────────────────────────

@router.message(F.text == "📦 Mahsulotlar")
async def admin_products(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    await msg.answer("📦 Mahsulotlar", reply_markup=admin_products_kb())


@router.message(F.text == "📋 Mahsulotlar ro'yxati")
async def list_products(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    products = await get_products(active_only=False)
    currency = await get_setting("currency")
    if not products:
        await msg.answer("Mahsulotlar yo'q.")
        return
    for p in products:
        status = "✅" if p["is_active"] else "❌"
        text = (
            f"{status} <b>{p['name']}</b>\n"
            f"💰 {format_price(p['price'], currency)}"
            + (f" → {format_price(p['discount_price'], currency)}" if p.get('discount_price') else "") +
            f"\n📦 Qoldiq: {p.get('stock', 0)}"
        )
        await msg.answer(text, reply_markup=admin_product_item_kb(p["id"]), parse_mode="HTML")


@router.message(F.text == "➕ Mahsulot qo'shish")
async def start_add_product(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.set_state(ProductState.name)
    await msg.answer("📝 Mahsulot nomini kiriting:", reply_markup=back_kb())


@router.message(ProductState.name)
async def product_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await state.set_state(ProductState.description)
    await msg.answer("📄 Tavsifini kiriting (o'tkazib yuborish uchun '-' yozing):")


@router.message(ProductState.description)
async def product_desc(msg: Message, state: FSMContext):
    desc = "" if msg.text.strip() == "-" else msg.text.strip()
    await state.update_data(description=desc)
    await state.set_state(ProductState.price)
    await msg.answer("💰 Narxini kiriting (faqat raqam):")


@router.message(ProductState.price)
async def product_price(msg: Message, state: FSMContext):
    try:
        price = float(msg.text.replace(" ", "").replace(",", "."))
    except ValueError:
        await msg.answer("❌ Raqam kiriting.")
        return
    await state.update_data(price=price)
    await state.set_state(ProductState.discount_price)
    await msg.answer("💸 Chegirma narxini kiriting (yo'q bo'lsa '-'):")


@router.message(ProductState.discount_price)
async def product_discount(msg: Message, state: FSMContext):
    disc = None
    if msg.text.strip() != "-":
        try:
            disc = float(msg.text.replace(" ", "").replace(",", "."))
        except ValueError:
            await msg.answer("❌ Raqam kiriting.")
            return
    await state.update_data(discount_price=disc)
    cats = await get_categories()
    if not cats:
        await state.update_data(category_id=None)
        await state.set_state(ProductState.images)
        await msg.answer("🖼 Rasmlarini yuboring (bir yoki bir nechta). Tugatish uchun 'Tayyor' yozing:")
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for c in cats:
        builder.button(text=f"{c['emoji']} {c['name']}", callback_data=f"pcat:{c['id']}")
    builder.adjust(2)
    await state.set_state(ProductState.category)
    await msg.answer("📂 Kategoriyani tanlang:", reply_markup=builder.as_markup())


@router.callback_query(ProductState.category, F.data.startswith("pcat:"))
async def product_category(cq: CallbackQuery, state: FSMContext):
    cat_id = int(cq.data.split(":")[1])
    await state.update_data(category_id=cat_id)
    await state.set_state(ProductState.images)
    await cq.message.answer("🖼 Rasmlarini yuboring. Tugatish uchun 'Tayyor' yozing:")
    await cq.answer()


@router.message(ProductState.images, F.photo)
async def product_images_photo(msg: Message, state: FSMContext):
    data = await state.get_data()
    images = data.get("images_list", [])
    images.append(msg.photo[-1].file_id)
    await state.update_data(images_list=images)
    await msg.answer(f"✅ Rasm {len(images)} ta qo'shildi. Yana yuborishingiz mumkin yoki 'Tayyor' yozing.")


@router.message(ProductState.images, F.text.casefold() == "tayyor")
async def product_images_done(msg: Message, state: FSMContext):
    await state.set_state(ProductState.sizes)
    await msg.answer("📏 O'lchamlarini kiriting vergul bilan (masalan: S,M,L,XL) yoki '-':")


@router.message(ProductState.images, F.text)
async def product_images_skip(msg: Message, state: FSMContext):
    await state.set_state(ProductState.sizes)
    await msg.answer("📏 O'lchamlarini kiriting vergul bilan yoki '-':")


@router.message(ProductState.sizes)
async def product_sizes(msg: Message, state: FSMContext):
    sizes = [] if msg.text.strip() == "-" else [s.strip() for s in msg.text.split(",")]
    await state.update_data(sizes=sizes)
    await state.set_state(ProductState.colors)
    await msg.answer("🎨 Ranglarini kiriting vergul bilan yoki '-':")


@router.message(ProductState.colors)
async def product_colors(msg: Message, state: FSMContext):
    colors = [] if msg.text.strip() == "-" else [c.strip() for c in msg.text.split(",")]
    await state.update_data(colors=colors)
    await state.set_state(ProductState.stock)
    await msg.answer("📦 Sklad qoldig'ini kiriting (raqam):")


@router.message(ProductState.stock)
async def product_stock(msg: Message, state: FSMContext):
    try:
        stock = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ Raqam kiriting.")
        return
    await state.update_data(stock=stock)
    await state.set_state(ProductState.sku)
    await msg.answer("🔑 SKU/Kod kiriting yoki '-':")


@router.message(ProductState.sku)
async def product_sku(msg: Message, state: FSMContext):
    sku = "" if msg.text.strip() == "-" else msg.text.strip()
    data = await state.get_data()
    product_data = {
        "name": data.get("name"),
        "description": data.get("description", ""),
        "price": data.get("price"),
        "discount_price": data.get("discount_price"),
        "category_id": data.get("category_id"),
        "images": json.dumps(data.get("images_list", [])),
        "sizes": json.dumps(data.get("sizes", [])),
        "colors": json.dumps(data.get("colors", [])),
        "stock": data.get("stock", 0),
        "sku": sku,
        "is_active": 1,
    }
    product_id = await add_product(product_data)
    await state.clear()
    await msg.answer(f"✅ Mahsulot qo'shildi! ID: {product_id}", reply_markup=admin_products_kb())


@router.callback_query(F.data.startswith("ap_toggle:"))
async def toggle_product(cq: CallbackQuery):
    product_id = int(cq.data.split(":")[1])
    p = await get_product(product_id)
    if p:
        await update_product(product_id, {"is_active": 0 if p["is_active"] else 1})
        status = "aktivlashtirildi ✅" if not p["is_active"] else "o'chirildi ❌"
        await cq.answer(f"Mahsulot {status}")
        await cq.message.edit_reply_markup(reply_markup=admin_product_item_kb(product_id))


@router.callback_query(F.data.startswith("ap_stock:"))
async def ask_stock(cq: CallbackQuery, state: FSMContext):
    product_id = int(cq.data.split(":")[1])
    await state.update_data(edit_product_id=product_id)
    await state.set_state(ProductState.stock)
    await cq.message.answer("📦 Yangi qoldiq sonini kiriting:")
    await cq.answer()


@router.callback_query(F.data.startswith("ap_delete:"))
async def delete_product_cb(cq: CallbackQuery):
    product_id = int(cq.data.split(":")[1])
    await delete_product(product_id)
    await cq.message.delete()
    await cq.answer("✅ O'chirildi")


# ─── CATEGORIES MANAGEMENT ───────────────────────────────────────────────────

@router.message(F.text == "📂 Kategoriyalar")
async def admin_categories(msg: Message):
    if not await is_admin(msg.from_user.id):
        from handlers.user import show_categories
        await show_categories(msg)
        return
    await msg.answer("📂 Kategoriyalar", reply_markup=admin_categories_kb())


@router.message(F.text == "➕ Kategoriya qo'shish")
async def start_add_cat(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.set_state(CategoryState.name)
    await msg.answer("📝 Kategoriya nomini kiriting:")


@router.message(CategoryState.name)
async def cat_name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text.strip())
    await state.set_state(CategoryState.emoji)
    await msg.answer("😀 Emoji kiriting (masalan: 👗):")


@router.message(CategoryState.emoji)
async def cat_emoji(msg: Message, state: FSMContext):
    data = await state.get_data()
    cat_id = await add_category(data["name"], msg.text.strip())
    await state.clear()
    await msg.answer(f"✅ Kategoriya qo'shildi! ID: {cat_id}", reply_markup=admin_categories_kb())


@router.message(F.text == "📋 Kategoriyalar ro'yxati")
async def list_categories(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    cats = await get_categories(active_only=False)
    if not cats:
        await msg.answer("Kategoriyalar yo'q.")
        return
    for c in cats:
        text = f"{c['emoji']} <b>{c['name']}</b>"
        await msg.answer(text, reply_markup=admin_category_item_kb(c["id"]), parse_mode="HTML")


@router.callback_query(F.data.startswith("ac_delete:"))
async def delete_cat(cq: CallbackQuery):
    cat_id = int(cq.data.split(":")[1])
    await delete_category(cat_id)
    await cq.message.delete()
    await cq.answer("✅ O'chirildi")


# ─── ORDERS MANAGEMENT ───────────────────────────────────────────────────────

@router.message(F.text == "🧾 Buyurtmalar")
async def admin_orders(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    await msg.answer("🧾 Buyurtmalarni filterlang:", reply_markup=admin_orders_filter_kb())


@router.callback_query(F.data.startswith("af_"))
async def filter_orders(cq: CallbackQuery):
    filter_map = {
        "af_new": "new",
        "af_confirmed": "confirmed",
        "af_delivering": "delivering",
        "af_closed": "closed",
        "af_cancelled": "cancelled",
        "af_all": None,
    }
    status = filter_map.get(cq.data)
    orders = await get_orders(status=status)
    currency = await get_setting("currency")
    await cq.answer()
    if not orders:
        await cq.message.answer("📭 Buyurtmalar yo'q.")
        return
    from config import ORDER_STATUSES
    for o in orders[:15]:
        st = ORDER_STATUSES.get(o["status"], o["status"])
        text = (
            f"<b>#{o['id']}</b> {st}\n"
            f"👤 {o.get('user_name') or o.get('full_name', '—')}\n"
            f"📞 {o.get('phone', '—')}\n"
            f"💰 {format_price(o['total_amount'], currency)}\n"
            f"📅 {o['created_at'][:16]}"
        )
        await cq.message.answer(
            text,
            reply_markup=admin_order_kb(o["id"], o["status"]),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("ao_confirm:"))
async def order_confirm(cq: CallbackQuery):
    order_id = int(cq.data.split(":")[1])
    await update_order_status(order_id, "confirmed")
    order = await get_order(order_id)
    if order:
        try:
            await cq.bot.send_message(
                order["user_id"],
                f"✅ Buyurtmangiz <b>#{order_id}</b> tasdiqlandi!",
                parse_mode="HTML"
            )
        except Exception:
            pass
    await cq.answer("✅ Tasdiqlandi")
    await cq.message.edit_reply_markup(reply_markup=admin_order_kb(order_id, "confirmed"))


@router.callback_query(F.data.startswith("ao_deliver:"))
async def order_deliver(cq: CallbackQuery):
    order_id = int(cq.data.split(":")[1])
    await update_order_status(order_id, "delivering")
    order = await get_order(order_id)
    if order:
        try:
            await cq.bot.send_message(
                order["user_id"],
                f"🚚 Buyurtmangiz <b>#{order_id}</b> yetkazib berishga topshirildi!",
                parse_mode="HTML"
            )
        except Exception:
            pass
    await cq.answer("🚚 Yetkazishga berildi")
    await cq.message.edit_reply_markup(reply_markup=admin_order_kb(order_id, "delivering"))


@router.callback_query(F.data.startswith("ao_close:"))
async def order_close(cq: CallbackQuery):
    order_id = int(cq.data.split(":")[1])
    await update_order_status(order_id, "closed")
    order = await get_order(order_id)
    if order:
        try:
            await cq.bot.send_message(
                order["user_id"],
                f"🎉 Buyurtmangiz <b>#{order_id}</b> yetkazib berildi! Rahmat!",
                parse_mode="HTML"
            )
        except Exception:
            pass
    await cq.answer("🎉 Yakunlandi")
    await cq.message.edit_reply_markup(reply_markup=admin_order_kb(order_id, "closed"))


@router.callback_query(F.data.startswith("ao_cancel:"))
async def order_cancel(cq: CallbackQuery):
    order_id = int(cq.data.split(":")[1])
    await update_order_status(order_id, "cancelled")
    order = await get_order(order_id)
    if order:
        try:
            await cq.bot.send_message(
                order["user_id"],
                f"❌ Buyurtmangiz <b>#{order_id}</b> bekor qilindi.",
                parse_mode="HTML"
            )
        except Exception:
            pass
    await cq.answer("❌ Bekor qilindi")
    await cq.message.delete()


@router.callback_query(F.data.startswith("ao_contact:"))
async def order_contact(cq: CallbackQuery):
    order_id = int(cq.data.split(":")[1])
    order = await get_order(order_id)
    if order:
        username = order.get("username")
        if username:
            await cq.message.answer(f"👤 Mijoz: @{username}")
        else:
            await cq.message.answer(f"👤 Mijoz ID: {order['user_id']}\nTo'g'ridan to'g'ri yozing.")
    await cq.answer()


# ─── PAYMENTS ────────────────────────────────────────────────────────────────

@router.message(F.text == "💳 To'lovlar")
async def admin_payments(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    orders = await get_orders()
    pending = [o for o in orders if o.get("payment_status") == "submitted"]
    if not pending:
        await msg.answer("💳 Tasdiqlanmagan to'lovlar yo'q.")
        return
    currency = await get_setting("currency")
    for o in pending:
        text = (
            f"💳 <b>Buyurtma #{o['id']}</b>\n"
            f"👤 {o.get('user_name', '—')}\n"
            f"💰 {format_price(o['total_amount'], currency)}"
        )
        if o.get("payment_screenshot"):
            await msg.answer_photo(
                o["payment_screenshot"], caption=text,
                reply_markup=admin_payment_kb(o["id"]), parse_mode="HTML"
            )
        else:
            await msg.answer(text, reply_markup=admin_payment_kb(o["id"]), parse_mode="HTML")


@router.callback_query(F.data.startswith("pay_confirm:"))
async def pay_confirm(cq: CallbackQuery):
    order_id = int(cq.data.split(":")[1])
    await confirm_payment(order_id, True)
    await update_order_status(order_id, "confirmed")
    order = await get_order(order_id)
    if order:
        try:
            await cq.bot.send_message(
                order["user_id"],
                f"✅ Buyurtmangiz #{order_id} uchun to'lov tasdiqlandi!",
            )
        except Exception:
            pass
    await cq.answer("✅ Tasdiqlandi")
    await cq.message.delete()


@router.callback_query(F.data.startswith("pay_reject:"))
async def pay_reject(cq: CallbackQuery):
    order_id = int(cq.data.split(":")[1])
    await confirm_payment(order_id, False)
    order = await get_order(order_id)
    if order:
        try:
            await cq.bot.send_message(
                order["user_id"],
                f"❌ Buyurtmangiz #{order_id} uchun to'lov rad etildi. Iltimos, qayta urinib ko'ring.",
            )
        except Exception:
            pass
    await cq.answer("❌ Rad etildi")
    await cq.message.delete()


# ─── CUSTOMERS ───────────────────────────────────────────────────────────────

@router.message(F.text == "👥 Mijozlar")
async def admin_users(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    users = await get_all_users()
    await msg.answer(f"👥 <b>Mijozlar: {len(users)} ta</b>", parse_mode="HTML")
    for u in users[:15]:
        banned = "🚫" if u.get("is_banned") else "✅"
        text = (
            f"{banned} {u.get('full_name', '—')}\n"
            f"@{u.get('username', '—')} | ID: {u['id']}\n"
            f"📅 {u['created_at'][:10]}"
        )
        await msg.answer(text, reply_markup=admin_user_kb(u["id"], u.get("is_banned", False)))


@router.callback_query(F.data.startswith("user_ban:"))
async def user_ban(cq: CallbackQuery):
    user_id = int(cq.data.split(":")[1])
    await ban_user(user_id, True)
    await cq.answer("🚫 Bloklandi")
    await cq.message.edit_reply_markup(reply_markup=admin_user_kb(user_id, True))


@router.callback_query(F.data.startswith("user_unban:"))
async def user_unban(cq: CallbackQuery):
    user_id = int(cq.data.split(":")[1])
    await ban_user(user_id, False)
    await cq.answer("✅ Blok olib tashlandi")
    await cq.message.edit_reply_markup(reply_markup=admin_user_kb(user_id, False))


# ─── PROMO CODES ─────────────────────────────────────────────────────────────

@router.message(F.text == "🎁 Promo kodlar")
async def admin_promos(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Promo kod qo'shish")
    kb.button(text="📋 Promo kodlar ro'yxati")
    kb.button(text="🔙 Admin panel")
    kb.adjust(2, 1)
    await msg.answer("🎁 Promo kodlar", reply_markup=kb.as_markup(resize_keyboard=True))


@router.message(F.text == "➕ Promo kod qo'shish")
async def start_add_promo(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.set_state(PromoState.code)
    await msg.answer("🔤 Promo kod kiriting (masalan: SALE20):", reply_markup=back_kb())


@router.message(PromoState.code)
async def promo_code_input(msg: Message, state: FSMContext):
    await state.update_data(code=msg.text.strip().upper())
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Foiz (%)", callback_data="promo_percent")
    builder.button(text="💰 Summa", callback_data="promo_sum")
    builder.adjust(2)
    await state.set_state(PromoState.discount_type)
    await msg.answer("Chegirma turini tanlang:", reply_markup=builder.as_markup())


@router.callback_query(PromoState.discount_type)
async def promo_type(cq: CallbackQuery, state: FSMContext):
    dtype = "percent" if cq.data == "promo_percent" else "sum"
    await state.update_data(discount_type=dtype)
    await state.set_state(PromoState.discount_value)
    hint = "foiz (masalan: 15)" if dtype == "percent" else "summa (masalan: 50000)"
    await cq.message.answer(f"💰 Chegirma miqdorini kiriting ({hint}):")
    await cq.answer()


@router.message(PromoState.discount_value)
async def promo_value(msg: Message, state: FSMContext):
    try:
        val = float(msg.text.replace(" ", "").replace(",", "."))
    except ValueError:
        await msg.answer("❌ Raqam kiriting.")
        return
    await state.update_data(discount_value=val)
    await state.set_state(PromoState.min_order)
    await msg.answer("💰 Minimal buyurtma summasi (yo'q bo'lsa 0):")


@router.message(PromoState.min_order)
async def promo_min(msg: Message, state: FSMContext):
    try:
        min_order = float(msg.text.replace(" ", "") or "0")
    except ValueError:
        min_order = 0
    await state.update_data(min_order_amount=min_order)
    await state.set_state(PromoState.max_uses)
    await msg.answer("🔢 Necha marta ishlatilsin (0 = cheksiz):")


@router.message(PromoState.max_uses)
async def promo_max_uses(msg: Message, state: FSMContext):
    try:
        max_uses = int(msg.text.strip() or "0")
    except ValueError:
        max_uses = 0
    data = await state.get_data()
    promo_data = {
        "code": data["code"],
        "discount_type": data["discount_type"],
        "discount_value": data["discount_value"],
        "min_order_amount": data.get("min_order_amount", 0),
        "max_uses": max_uses,
        "expires_at": None,
    }
    await add_promo(promo_data)
    await state.clear()
    await msg.answer(f"✅ Promo kod yaratildi: <code>{data['code']}</code>", parse_mode="HTML")


@router.message(F.text == "📋 Promo kodlar ro'yxati")
async def list_promos(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    promos = await get_all_promos()
    if not promos:
        await msg.answer("Promo kodlar yo'q.")
        return
    for p in promos:
        status = "✅" if p["is_active"] else "❌"
        dtype = "%" if p["discount_type"] == "percent" else "so'm"
        text = (
            f"{status} <code>{p['code']}</code>\n"
            f"Chegirma: {p['discount_value']}{dtype}\n"
            f"Ishlatildi: {p['used_count']}/{p['max_uses'] or '∞'}"
        )
        await msg.answer(text, reply_markup=admin_promo_kb(p["id"]), parse_mode="HTML")


# ─── BROADCAST ───────────────────────────────────────────────────────────────

@router.message(F.text == "📣 Reklama")
async def admin_broadcast(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    await state.set_state(BroadcastState.message)
    await msg.answer("📣 Reklama xabarini yuboring (matn, rasm yoki video):", reply_markup=back_kb())


@router.message(BroadcastState.message)
async def broadcast_msg(msg: Message, state: FSMContext):
    # Store message id and chat id for forwarding
    await state.update_data(bc_msg_id=msg.message_id, bc_chat_id=msg.chat.id)
    await state.set_state(BroadcastState.target)
    await msg.answer("Kimga yuborish?", reply_markup=broadcast_target_kb())


@router.callback_query(BroadcastState.target)
async def broadcast_target(cq: CallbackQuery, state: FSMContext):
    await state.update_data(target=cq.data)
    await state.set_state(BroadcastState.confirm)
    await cq.message.answer("✅ Yuborishni tasdiqlaysizmi?", reply_markup=confirm_broadcast_kb())
    await cq.answer()


def confirm_broadcast_kb():
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    kb.button(text="✅ Ha, yuborish")
    kb.button(text="❌ Bekor")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


@router.message(BroadcastState.confirm, F.text == "✅ Ha, yuborish")
async def do_broadcast(msg: Message, state: FSMContext):
    data = await state.get_data()
    users = await get_all_users()
    target = data.get("target", "bc_all")
    if target == "bc_buyers":
        from database.db import get_orders
        orders = await get_orders()
        buyer_ids = {o["user_id"] for o in orders}
        users = [u for u in users if u["id"] in buyer_ids]
    bc_msg_id = data.get("bc_msg_id")
    bc_chat_id = data.get("bc_chat_id")
    sent, failed = 0, 0
    for u in users:
        if u.get("is_banned"):
            continue
        try:
            await msg.bot.forward_message(u["id"], bc_chat_id, bc_msg_id)
            sent += 1
        except Exception:
            failed += 1
    await state.clear()
    await msg.answer(
        f"📣 Reklama yuborildi!\n✅ {sent} ta | ❌ {failed} ta",
        reply_markup=admin_main_kb()
    )


@router.message(BroadcastState.confirm, F.text == "❌ Bekor")
async def cancel_broadcast(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("❌ Bekor qilindi.", reply_markup=admin_main_kb())


# ─── STATISTICS ──────────────────────────────────────────────────────────────

@router.message(F.text == "📊 Statistika")
async def admin_stats(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    stats = await get_statistics()
    currency = await get_setting("currency")
    top = "\n".join(
        f"  {i+1}. {r[0]} — {r[1]} ta"
        for i, r in enumerate(stats.get("top_products", []))
    ) or "  Ma'lumot yo'q"
    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: {stats['total_users']}\n"
        f"📦 Jami buyurtmalar: {stats['total_orders']}\n"
        f"🆕 Bugungi buyurtmalar: {stats['today_orders']}\n"
        f"📅 Haftalik buyurtmalar: {stats['week_orders']}\n\n"
        f"💰 Bugungi daromad: {format_price(stats['today_revenue'], currency)}\n"
        f"💎 Jami daromad: {format_price(stats['total_revenue'], currency)}\n\n"
        f"🏆 <b>Top mahsulotlar:</b>\n{top}"
    )
    await msg.answer(text, parse_mode="HTML")


# ─── SETTINGS ────────────────────────────────────────────────────────────────

@router.message(F.text == "⚙️ Sozlamalar")
async def admin_settings(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    from database.db import get_all_settings
    settings = await get_all_settings()
    await msg.answer("⚙️ <b>Sozlamalar</b>\n\nO'zgartirish uchun tugmani bosing:", 
                     reply_markup=settings_kb(settings), parse_mode="HTML")


@router.callback_query(F.data.startswith("setting_edit:"))
async def edit_setting(cq: CallbackQuery, state: FSMContext):
    key = cq.data.split(":")[1]
    await state.update_data(setting_key=key)
    await state.set_state(SettingsState.waiting_value)
    if key == "orders_open":
        current = await get_setting(key)
        new_val = "0" if current == "1" else "1"
        await set_setting(key, new_val)
        await cq.answer(f"{'✅ Buyurtmalar ochildi' if new_val == '1' else '❌ Buyurtmalar yopildi'}", show_alert=True)
        await state.clear()
        from database.db import get_all_settings
        settings = await get_all_settings()
        await cq.message.edit_reply_markup(reply_markup=settings_kb(settings))
    else:
        await cq.message.answer(f"✏️ Yangi qiymat kiriting:")
        await cq.answer()


@router.message(SettingsState.waiting_value)
async def save_setting(msg: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("setting_key")
    await set_setting(key, msg.text.strip())
    await state.clear()
    await msg.answer("✅ Saqlandi!", reply_markup=admin_main_kb())


# ─── ADMINS MANAGEMENT ───────────────────────────────────────────────────────

@router.message(F.text == "👨‍💼 Adminlar")
async def admin_admins(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    admins = await get_admins()
    from aiogram.utils.keyboard import ReplyKeyboardBuilder
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Admin qo'shish")
    kb.button(text="🔙 Admin panel")
    kb.adjust(2)
    lines = ["👨‍💼 <b>Adminlar:</b>\n"]
    for a in admins:
        lines.append(f"• @{a.get('username', '—')} ({a['role']}) [/removeadmin_{a['id']}]")
    await msg.answer("\n".join(lines), reply_markup=kb.as_markup(resize_keyboard=True), parse_mode="HTML")


@router.message(F.text == "➕ Admin qo'shish")
async def start_add_admin(msg: Message, state: FSMContext):
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("Faqat super admin qo'sha oladi.")
        return
    await state.set_state(AdminState.add_id)
    await msg.answer("👤 Admin Telegram ID sini kiriting:")


@router.message(AdminState.add_id)
async def admin_id_input(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
    except ValueError:
        await msg.answer("❌ ID raqam bo'lishi kerak.")
        return
    await state.update_data(new_admin_id=uid)
    await state.set_state(AdminState.add_role)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="👑 Super admin", callback_data="role_super")
    builder.button(text="🧑‍💼 Operator", callback_data="role_operator")
    builder.button(text="📦 Buyurtma menejeri", callback_data="role_order")
    builder.adjust(1)
    await msg.answer("Rol tanlang:", reply_markup=builder.as_markup())


@router.callback_query(AdminState.add_role)
async def admin_role(cq: CallbackQuery, state: FSMContext):
    role_map = {"role_super": "super", "role_operator": "operator", "role_order": "order_manager"}
    role = role_map.get(cq.data, "operator")
    data = await state.get_data()
    uid = data["new_admin_id"]
    await add_admin(uid, "", role)
    await state.clear()
    await cq.message.answer(f"✅ Admin qo'shildi! ID: {uid}, Rol: {role}", reply_markup=admin_main_kb())
    await cq.answer()
