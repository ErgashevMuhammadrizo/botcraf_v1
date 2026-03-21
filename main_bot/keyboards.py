from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def _kb_btn(text: str, style: str | None = None) -> KeyboardButton:
    kwargs = {'text': text}
    if style:
        kwargs['style'] = style
    try:
        return KeyboardButton(**kwargs)
    except Exception:
        kwargs.pop('style', None)
        return KeyboardButton(**kwargs)


def _inline_btn(text: str, callback_data: str | None = None, url: str | None = None, style: str | None = None) -> InlineKeyboardButton:
    kwargs = {'text': text}
    if callback_data is not None:
        kwargs['callback_data'] = callback_data
    if url is not None:
        kwargs['url'] = url
    if style:
        kwargs['style'] = style
    try:
        return InlineKeyboardButton(**kwargs)
    except Exception:
        kwargs.pop('style', None)
        return InlineKeyboardButton(**kwargs)


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [_kb_btn('🚀 Bot yaratish', 'primary')],
            [_kb_btn('📦 Mening botlarim'), _kb_btn('💳 Hamyon', 'success')],
            [_kb_btn('🎁 Referat', 'primary'), _kb_btn('🆘 Yordam')],
        ],
        resize_keyboard=True,
        input_field_placeholder='BotCraft menyusidan tanlang...',
    )


def bot_type_kb(kino_price: int, media_price: int, shop_price: int, can_trial: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [_inline_btn(f"🎬 Kino Bot — {kino_price:,} so'm / oy", callback_data='type_kino', style='primary')],
        [_inline_btn(f"📥 Save Bot — {media_price:,} so'm / oy", callback_data='type_media', style='primary')],
        [_inline_btn(f"🛍 Shop Bot — {shop_price:,} so'm / oy", callback_data='type_shop', style='primary')],
    ]
    coming = [
        ('🤖 CRM Bot', 'coming_crm'), ('📣 Reklama Bot', 'coming_ads'), ('🧾 Invoice Bot', 'coming_invoice'),
        ('📚 Kurs Bot', 'coming_course'), ('🎟 Support Bot', 'coming_support'), ('📊 Analitika Bot', 'coming_analytics'),
        ('🏪 SMM Bot', 'coming_smm'), ('🎵 Music Bot', 'coming_music'), ('📦 Ombor Bot', 'coming_warehouse'),
        ("🗳 So'rov Bot", 'coming_poll'), ('👥 Guruh Manager', 'coming_group'), ('📰 News Bot', 'coming_news'),
        ('🏆 Quiz Bot', 'coming_quiz'), ('🛎 Booking Bot', 'coming_booking'), ('🧠 AI Assistant', 'coming_ai'),
        ('🎮 Game Bot', 'coming_game'), ('💼 Portfolio Bot', 'coming_portfolio'), ('📞 Call Center Bot', 'coming_callcenter'),
        ('🎁 Giveaway Bot', 'coming_giveaway'), ('📄 CV Bot', 'coming_cv'), ('🧮 Hisob Bot', 'coming_accounting'),
    ]
    for i in range(0, len(coming), 2):
        pair = coming[i:i+2]
        rows.append([_inline_btn(t, callback_data=c) for t, c in pair])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def plan_select_kb(bot_type: str, paid_price: int, can_trial: bool) -> InlineKeyboardMarkup:
    label_map = {'kino': '🎬 Kino Bot', 'media': '📥 Save Bot', 'shop': '🛍 Shop Bot'}
    label = label_map.get(bot_type, '🤖 Bot')
    rows = []
    if can_trial:
        rows.append([_inline_btn('🧪 Test — 10 kun bepul', callback_data=f'choose_{bot_type}_trial', style='success')])
    rows.append([_inline_btn(f"💎 Pullik — {paid_price:,} so'm / 30 kun", callback_data=f'choose_{bot_type}_paid', style='primary')])
    rows.append([_inline_btn('⬅️ Ortga', callback_data='back_types')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def privacy_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        _inline_btn('🌐 Ochiq kanal', callback_data='privacy_public', style='primary'),
        _inline_btn('🔒 Yopiq kanal', callback_data='privacy_private'),
    ]])


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        _inline_btn('✅ Tasdiqlash', callback_data='confirm_create', style='success'),
        _inline_btn('❌ Bekor qilish', callback_data='cancel_create', style='danger'),
    ]])


def wallet_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_inline_btn("💳 Balans to'ldirish", callback_data='wallet_topup', style='success')],
        [_inline_btn("🧾 To'lovlar tarixi", callback_data='wallet_history')],
    ])


def topup_amounts_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_inline_btn("49 000 so'm", callback_data='topup_preset_49000', style='success')],
        [_inline_btn("130 000 so'm", callback_data='topup_preset_130000')],
        [_inline_btn("250 000 so'm", callback_data='topup_preset_250000')],
        [_inline_btn('✍️ Boshqa summa', callback_data='topup_custom')],
        [_inline_btn('❌ Bekor qilish', callback_data='wallet_menu', style='danger')],
    ])


def cancel_topup_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_inline_btn('❌ Bekor qilish', callback_data='wallet_menu', style='danger')]])


def my_bot_actions_kb(bot_id: int, is_active: bool) -> InlineKeyboardMarkup:
    rows = [
        [_inline_btn('🔄 1 oy uzaytirish', callback_data=f'extend_bot_{bot_id}_1', style='success')],
        [_inline_btn('🔄 3 oy uzaytirish', callback_data=f'extend_bot_{bot_id}_3')],
    ]
    if not is_active:
        rows.append([_inline_btn('⚠️ Faollashtirish uchun uzaytiring', callback_data=f'extend_bot_{bot_id}_1', style='primary')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_inline_btn("💰 To'lovlarni tasdiqlash", callback_data='admin_payments', style='success')],
        [_inline_btn('📢 Reklama yuborish', callback_data='admin_broadcast', style='primary')],
        [_inline_btn('💸 Tariflarni sozlash', callback_data='admin_prices')],
        [_inline_btn('👥 Foydalanuvchilar', callback_data='admin_users'), _inline_btn('📊 Statistika', callback_data='admin_stats')],
        [_inline_btn('📢 Majburiy obuna', callback_data='admin_main_subs')],
    ])


def payment_action_kb(payment_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        _inline_btn('✅ Tasdiqlash', callback_data=f'pay_approve_{payment_id}_{user_id}', style='success'),
        _inline_btn('❌ Rad etish', callback_data=f'pay_reject_{payment_id}_{user_id}', style='danger'),
    ]])


def main_sub_manage_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_inline_btn("➕ Kanal qo'shish", callback_data='main_sub_add', style='success')],
        [_inline_btn("➖ Kanal o'chirish", callback_data='main_sub_remove', style='danger')],
        [_inline_btn("📋 Kanallar ro'yxati", callback_data='main_sub_list')],
        [_inline_btn('⬅️ Orqaga', callback_data='admin_back')],
    ])


def main_sub_check_kb(channels: list) -> InlineKeyboardMarkup:
    buttons = []
    for ch_id, ch_name, ch_url in channels:
        url = ch_url if ch_url else f"https://t.me/{str(ch_id).lstrip('@')}"
        buttons.append([_inline_btn(f'📢 {ch_name}', url=url, style='primary')])
    buttons.append([_inline_btn('✅ Obunani tekshirish', callback_data='main_check_sub', style='success')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_price_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_inline_btn('🎬 Kino narxi', callback_data='setprice_kino')],
        [_inline_btn('📥 Media narxi', callback_data='setprice_media')],
        [_inline_btn('🛍 Shop narxi', callback_data='setprice_shop')],
        [_inline_btn('🎁 Referat bonusi', callback_data='setprice_ref')],
        [_inline_btn('🧪 Test kunlari', callback_data='setprice_trial')],
        [_inline_btn('💳 Karta raqami', callback_data='setcard_number')],
        [_inline_btn('👤 Karta egasi', callback_data='setcard_owner')],
        [_inline_btn('⬅️ Orqaga', callback_data='admin_back')],
    ])