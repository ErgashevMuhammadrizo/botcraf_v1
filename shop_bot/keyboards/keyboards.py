from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


# ─── USER MAIN MENU ───────────────────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="🛍 Mahsulotlar")
    kb.button(text="📂 Kategoriyalar")
    kb.button(text="🛒 Savatcha")
    kb.button(text="📦 Buyurtmalarim")
    kb.button(text="❤️ Saralanganlar")
    kb.button(text="🎁 Aksiyalar")
    kb.button(text="🔎 Qidirish")
    kb.button(text="☎️ Aloqa")
    kb.button(text="ℹ️ Do'kon haqida")
    kb.adjust(2, 2, 2, 3)
    return kb.as_markup(resize_keyboard=True)


def back_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔙 Orqaga")
    return kb.as_markup(resize_keyboard=True)


def contact_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📱 Telefon yuborish", request_contact=True)
    kb.button(text="🔙 Orqaga")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


def location_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📍 Lokatsiya yuborish", request_location=True)
    kb.button(text="✍️ Manzilni yozib yuborish")
    kb.button(text="🔙 Orqaga")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)


def skip_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="⏭ O'tkazib yuborish")
    kb.button(text="🔙 Orqaga")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


# ─── DELIVERY / PAYMENT ───────────────────────────────────────────────────────

def delivery_type_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="🚚 Kuryer orqali")
    kb.button(text="🏪 Olib ketish")
    kb.button(text="🔙 Orqaga")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


def payment_type_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="💵 Naqd")
    kb.button(text="💳 Karta o'tkazmasi")
    kb.button(text="📱 Click/Payme")
    kb.button(text="🔙 Orqaga")
    kb.adjust(2, 1, 1)
    return kb.as_markup(resize_keyboard=True)


def confirm_order_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="✅ Tasdiqlash")
    kb.button(text="❌ Bekor qilish")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


# ─── PRODUCTS INLINE ─────────────────────────────────────────────────────────

def product_list_kb(product_id: int, user_id: int = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Savatchaga", callback_data=f"cart_add:{product_id}")
    builder.button(text="❤️ Saqlash", callback_data=f"fav_toggle:{product_id}")
    builder.button(text="📄 Batafsil", callback_data=f"product_detail:{product_id}")
    builder.adjust(2, 1)
    return builder.as_markup()


def product_detail_kb(product_id: int, is_fav: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Savatchaga qo'shish", callback_data=f"cart_add:{product_id}")
    builder.button(text="⚡ Hozir buyurtma", callback_data=f"order_now:{product_id}")
    fav_text = "💔 Saralangandan o'chirish" if is_fav else "❤️ Saralanganlarga"
    builder.button(text=fav_text, callback_data=f"fav_toggle:{product_id}")
    builder.button(text="🔙 Orqaga", callback_data="back_products")
    builder.adjust(1)
    return builder.as_markup()


def categories_kb(categories: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(
            text=f"{cat['emoji']} {cat['name']}",
            callback_data=f"cat_products:{cat['id']}"
        )
    builder.button(text="🔙 Orqaga", callback_data="back_main")
    builder.adjust(2)
    return builder.as_markup()


def cart_item_kb(cart_id: int, quantity: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➖", callback_data=f"cart_dec:{cart_id}")
    builder.button(text=f"{quantity}", callback_data=f"cart_qty:{cart_id}")
    builder.button(text="➕", callback_data=f"cart_inc:{cart_id}")
    builder.button(text="❌ O'chirish", callback_data=f"cart_remove:{cart_id}")
    builder.adjust(3, 1)
    return builder.as_markup()


def cart_bottom_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🧹 Tozalash", callback_data="cart_clear")
    builder.button(text="✅ Buyurtma berish", callback_data="cart_checkout")
    builder.adjust(1)
    return builder.as_markup()


def order_list_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📄 Batafsil", callback_data=f"order_detail:{order_id}")
    builder.adjust(1)
    return builder.as_markup()


def screenshot_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔙 Orqaga")
    return kb.as_markup(resize_keyboard=True)


# ─── ADMIN ────────────────────────────────────────────────────────────────────

def admin_main_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📦 Mahsulotlar")
    kb.button(text="📂 Kategoriyalar")
    kb.button(text="🧾 Buyurtmalar")
    kb.button(text="👥 Mijozlar")
    kb.button(text="💳 To'lovlar")
    kb.button(text="🎁 Promo kodlar")
    kb.button(text="📣 Reklama")
    kb.button(text="📊 Statistika")
    kb.button(text="⚙️ Sozlamalar")
    kb.button(text="👨‍💼 Adminlar")
    kb.button(text="🔙 User panel")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def admin_products_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Mahsulot qo'shish")
    kb.button(text="📋 Mahsulotlar ro'yxati")
    kb.button(text="🔙 Admin panel")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


def admin_categories_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="➕ Kategoriya qo'shish")
    kb.button(text="📋 Kategoriyalar ro'yxati")
    kb.button(text="🔙 Admin panel")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


def admin_product_item_kb(product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Tahrirlash", callback_data=f"ap_edit:{product_id}")
    builder.button(text="📦 Qoldiq", callback_data=f"ap_stock:{product_id}")
    builder.button(text="🔄 Holat", callback_data=f"ap_toggle:{product_id}")
    builder.button(text="❌ O'chirish", callback_data=f"ap_delete:{product_id}")
    builder.adjust(2)
    return builder.as_markup()


def admin_category_item_kb(cat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Tahrirlash", callback_data=f"ac_edit:{cat_id}")
    builder.button(text="❌ O'chirish", callback_data=f"ac_delete:{cat_id}")
    builder.adjust(2)
    return builder.as_markup()


def admin_order_kb(order_id: int, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if status == "new":
        builder.button(text="✅ Tasdiqlash", callback_data=f"ao_confirm:{order_id}")
        builder.button(text="❌ Bekor qilish", callback_data=f"ao_cancel:{order_id}")
    elif status == "confirmed":
        builder.button(text="🚚 Yetkazishga berish", callback_data=f"ao_deliver:{order_id}")
        builder.button(text="❌ Bekor qilish", callback_data=f"ao_cancel:{order_id}")
    elif status in ("delivering", "on_way"):
        builder.button(text="🎉 Yakunlash", callback_data=f"ao_close:{order_id}")
    builder.button(text="✍️ Izoh", callback_data=f"ao_note:{order_id}")
    builder.button(text="💬 Bog'lanish", callback_data=f"ao_contact:{order_id}")
    builder.adjust(2)
    return builder.as_markup()


def admin_orders_filter_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🆕 Yangi", callback_data="af_new")
    builder.button(text="✅ Tasdiqlangan", callback_data="af_confirmed")
    builder.button(text="🚚 Yetkazilmoqda", callback_data="af_delivering")
    builder.button(text="🎉 Yopilgan", callback_data="af_closed")
    builder.button(text="❌ Bekor", callback_data="af_cancelled")
    builder.button(text="📋 Barchasi", callback_data="af_all")
    builder.adjust(3)
    return builder.as_markup()


def admin_payment_kb(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"pay_confirm:{order_id}")
    builder.button(text="❌ Rad etish", callback_data=f"pay_reject:{order_id}")
    builder.adjust(2)
    return builder.as_markup()


def admin_user_kb(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_banned:
        builder.button(text="✅ Unblock", callback_data=f"user_unban:{user_id}")
    else:
        builder.button(text="🚫 Ban", callback_data=f"user_ban:{user_id}")
    builder.button(text="💬 Xabar", callback_data=f"user_msg:{user_id}")
    builder.adjust(2)
    return builder.as_markup()


def admin_promo_kb(promo_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Aktivlik", callback_data=f"promo_toggle:{promo_id}")
    builder.button(text="❌ O'chirish", callback_data=f"promo_delete:{promo_id}")
    builder.adjust(2)
    return builder.as_markup()


def broadcast_target_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Hammaga", callback_data="bc_all")
    builder.button(text="🛒 Buyurtma qilganlarga", callback_data="bc_buyers")
    builder.button(text="🆕 Yangi userlarga", callback_data="bc_new")
    builder.adjust(1)
    return builder.as_markup()


def settings_kb(settings: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    items = [
        ("shop_name", "🏪 Do'kon nomi"),
        ("shop_phone", "📞 Telefon"),
        ("shop_address", "📍 Manzil"),
        ("shop_hours", "🕐 Ish vaqti"),
        ("delivery_price", "🚚 Yetkazib berish narxi"),
        ("free_delivery_from", "🎁 Bepul yetkazib berish dari"),
        ("min_order", "💰 Minimal buyurtma"),
        ("card_numbers", "💳 Karta raqamlari"),
        ("orders_open", "🔓 Buyurtma qabul qilish"),
        ("welcome_text", "👋 Xush kelibsiz matni"),
        ("currency", "💱 Valyuta"),
    ]
    for key, label in items:
        val = settings.get(key, "—")
        if key == "orders_open":
            val = "✅ Ochiq" if val == "1" else "❌ Yopiq"
        builder.button(text=f"{label}: {val[:20]}", callback_data=f"setting_edit:{key}")
    builder.adjust(1)
    return builder.as_markup()


def sizes_selection_kb(sizes: list, selected: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in sizes:
        check = "✅ " if s in selected else ""
        builder.button(text=f"{check}{s}", callback_data=f"size_select:{s}")
    builder.button(text="➡️ Davom etish", callback_data="size_done")
    builder.adjust(3)
    return builder.as_markup()


def colors_selection_kb(colors: list, selected: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for c in colors:
        check = "✅ " if c in selected else ""
        builder.button(text=f"{check}{c}", callback_data=f"color_select:{c}")
    builder.button(text="➡️ Davom etish", callback_data="color_done")
    builder.adjust(3)
    return builder.as_markup()
