import asyncio
import logging
import os
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from .database import (
    register_user, save_bot, get_user_bots, get_balance, add_balance, deduct_balance,
    is_main_admin, get_all_main_users, create_payment, get_pending_payments,
    approve_payment, reject_payment, get_user_payment_history, extend_bot_subscription,
    get_bot_by_id, add_main_required_channel, remove_main_required_channel,
    get_main_required_channels, create_referral, get_referral_stats, reward_referral_if_eligible,
    can_use_trial, mark_trial_used, token_exists, get_kino_monthly_price,
    get_media_monthly_price, get_shop_monthly_price, get_trial_days, get_referral_bonus, set_setting,
    get_payment_card, get_payment_card_owner, choose_available_server, add_waitlist
)
from .launcher import build_child_process
from .keyboards import (
    main_menu_kb, bot_type_kb, plan_select_kb, privacy_kb, confirm_kb, wallet_kb,
    topup_amounts_kb, cancel_topup_kb, admin_panel_kb, payment_action_kb,
    my_bot_actions_kb, main_sub_manage_kb, main_sub_check_kb, admin_price_kb
)

logger = logging.getLogger(__name__)
router = Router()
PRICE_MAP = {1: 49_000, 3: 130_000, 6: 250_000}


class CreateBot(StatesGroup):
    waiting_token = State()
    waiting_channel = State()
    waiting_privacy = State()
    waiting_admin_id = State()
    confirming = State()


class WalletStates(StatesGroup):
    waiting_custom_amount = State()
    waiting_receipt = State()


class AdminStates(StatesGroup):
    waiting_reject_reason = State()
    waiting_sub_id = State()
    waiting_sub_name = State()
    waiting_sub_url = State()
    waiting_rem_sub = State()
    waiting_broadcast = State()
    waiting_price = State()


def _normalize_channel_id(raw: str) -> str:
    value = (raw or '').strip()
    if not value:
        return value
    if value.startswith('https://t.me/'):
        tail = value.split('https://t.me/', 1)[1].strip('/')
        if tail.startswith('+'):
            return value
        return '@' + tail.lstrip('@')
    if value.startswith('t.me/'):
        tail = value.split('t.me/', 1)[1].strip('/')
        if tail.startswith('+'):
            return 'https://t.me/' + tail
        return '@' + tail.lstrip('@')
    return value


async def check_main_subscription(bot: Bot, user_id: int) -> bool:
    channels = await get_main_required_channels()
    if not channels:
        return True
    for ch_id, _, _ in channels:
        try:
            member = await bot.get_chat_member(ch_id, user_id)
            if member.status in ('left', 'kicked'):
                return False
        except Exception:
            return False
    return True


@router.message(Command('start'))
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    is_new = await register_user(message.from_user.id, message.from_user.username or '', message.from_user.full_name or '')
    start_arg = (message.text or '').split(maxsplit=1)[1] if len((message.text or '').split(maxsplit=1)) > 1 else ''
    if is_new and start_arg.startswith('ref_'):
        try:
            referrer_id = int(start_arg.replace('ref_', '', 1))
            if referrer_id != message.from_user.id:
                await create_referral(referrer_id, message.from_user.id)
        except ValueError:
            pass
    if not await check_main_subscription(bot, message.from_user.id):
        channels = await get_main_required_channels()
        await message.answer('⚠️ <b>BotCraftdan foydalanish uchun quyidagi kanallarga obuna bo\'ling:</b>', reply_markup=main_sub_check_kb(channels), parse_mode='HTML')
        return
    trial_days = await get_trial_days()
    await message.answer(
        '🚀 <b>BotCraft</b>ga xush kelibsiz!\n\n'
        'Bu platforma orqali o\'zingizga child-bot yaratib, ijaraga olib boshqarishingiz mumkin.\n\n'
        f'🎁 Yangi user uchun: <b>{trial_days} kunlik test tarif</b> mavjud.\n'
        '🎬 Kino Bot, 📥 Save Bot va 🛍 Shop Bot mavjud.\n\n'
        'Kerakli bo\'limni pastdagi menyudan tanlang.',
        reply_markup=main_menu_kb(),
        parse_mode='HTML'
    )


@router.callback_query(F.data == 'main_check_sub')
async def main_check_sub_cb(callback: CallbackQuery, bot: Bot):
    if not await check_main_subscription(bot, callback.from_user.id):
        await callback.answer('Hali obuna bo\'lmadingiz', show_alert=True)
        return
    await callback.message.delete()
    await callback.message.answer('✅ Obuna tasdiqlandi!', reply_markup=main_menu_kb())
    await callback.answer()


@router.message(F.text == '🆘 Yordam')
async def help_reply(message: Message):
    await message.answer(
        '🆘 <b>Yordam</b>\n\n'
        '1) “🚀 Bot yaratish” ni bosing\n'
        '2) Bot tokenini yuboring\n'
        '3) Kerakli ma\'lumotlarni kiriting\n'
        '4) Tasdiqlang\n\n'
        'Savol bo\'lsa admin bilan bog\'laning.',
        parse_mode='HTML'
    )


@router.message(F.text == '🎁 Referat')
async def on_referral_reply(message: Message, bot: Bot):
    invited_count, earned_total = await get_referral_stats(message.from_user.id)
    me = await bot.get_me()
    ref_bonus = await get_referral_bonus()
    bot_username = (me.username or os.getenv('BOT_USERNAME', '')).lstrip('@')
    ref_link = f'https://t.me/{bot_username}?start=ref_{message.from_user.id}' if bot_username else f'/start ref_{message.from_user.id}'
    text = (
        '🎁 <b>Referat dasturi</b>\n\n'
        'Do\'stingiz sizning link orqali kirib, <b>birinchi botini yaratsa</b>, sizga bonus tushadi.\n\n'
        f'👥 Takliflar: <b>{invited_count}</b>\n'
        f'💰 Ishlangan bonus: <b>{earned_total:,} so\'m</b>\n'
        f'🎁 Har bir faol referat: <b>{ref_bonus:,} so\'m</b>\n\n'
        f'🔗 <code>{ref_link}</code>\n\n'
        'Bu bonus pul faqat BotCraft ichida bot yaratish va muddat uzaytirishga ishlatiladi.'
    )
    await message.answer(text, parse_mode='HTML')


@router.message(F.text == '💳 Hamyon')
async def wallet_menu(message: Message):
    balance = await get_balance(message.from_user.id)
    await message.answer(
        f'💳 <b>Hamyon</b>\n\n💰 Balans: <b>{balance:,} so\'m</b>\n\nBalansni to\'ldirishingiz yoki tarixni ko\'rishingiz mumkin.',
        reply_markup=wallet_kb(), parse_mode='HTML'
    )


@router.callback_query(F.data == 'wallet_menu')
async def wallet_menu_cb(callback: CallbackQuery):
    balance = await get_balance(callback.from_user.id)
    await callback.message.edit_text(f'💳 <b>Hamyon</b>\n\n💰 Balans: <b>{balance:,} so\'m</b>', reply_markup=wallet_kb(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'wallet_topup')
async def wallet_topup_cb(callback: CallbackQuery):
    await callback.message.edit_text('💵 <b>Summani tanlang</b>', reply_markup=topup_amounts_kb(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.startswith('topup_preset_'))
async def topup_preset_cb(callback: CallbackQuery, state: FSMContext):
    amount = int(callback.data.split('_')[-1])
    await state.set_state(WalletStates.waiting_receipt)
    await state.update_data(topup_amount=amount)
    card = await get_payment_card()
    owner = await get_payment_card_owner()
    await callback.message.edit_text(
        f"💳 <b>{amount:,} so'm</b> to'lov uchun chek rasmini yuboring.\n\n"
        f"💳 Karta: <code>{card}</code>\n"
        f"👤 Egasi: <b>{owner}</b>\n\n"
        "Admin tekshiradi va balansingizga qo'shadi.",
        reply_markup=cancel_topup_kb(), parse_mode='HTML'
    )
    await callback.answer()


@router.callback_query(F.data == 'topup_custom')
async def topup_custom_cb(callback: CallbackQuery, state: FSMContext):
    await state.set_state(WalletStates.waiting_custom_amount)
    card = await get_payment_card()
    owner = await get_payment_card_owner()
    await callback.message.edit_text(
        '✍️ Summani raqamda yuboring. Masalan: <code>49000</code>\n\n'
        f'💳 Karta: <code>{card}</code>\n'
        f'👤 Egasi: <b>{owner}</b>',
        reply_markup=cancel_topup_kb(), parse_mode='HTML'
    )
    await callback.answer()


@router.message(WalletStates.waiting_custom_amount)
async def custom_amount_received(message: Message, state: FSMContext):
    txt = (message.text or '').replace(' ', '')
    if not txt.isdigit() or int(txt) < 5000:
        await message.answer('❌ Kamida 5000 so\'m kiriting.')
        return
    await state.set_state(WalletStates.waiting_receipt)
    await state.update_data(topup_amount=int(txt))
    await message.answer('🧾 Endi chek rasmini yuboring.', reply_markup=cancel_topup_kb())


@router.message(WalletStates.waiting_receipt, F.photo)
async def receipt_received(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    amount = int(data['topup_amount'])
    file_id = message.photo[-1].file_id
    payment_id = await create_payment(message.from_user.id, amount, 1, file_id)
    await message.answer('✅ Chekingiz qabul qilindi. Admin tasdiqlagach, balansga tushadi.', reply_markup=main_menu_kb())
    admin_id = int(os.getenv('MAIN_ADMIN_ID', '0'))
    if admin_id:
        try:
            await bot.send_photo(admin_id, photo=file_id, caption=f'💰 <b>To\'lov #{payment_id}</b>\n\n👤 <code>{message.from_user.id}</code>\n💵 {amount:,} so\'m', reply_markup=payment_action_kb(payment_id, message.from_user.id), parse_mode='HTML')
        except Exception:
            pass


@router.callback_query(F.data == 'wallet_history')
async def wallet_history_cb(callback: CallbackQuery):
    history = await get_user_payment_history(callback.from_user.id)
    if not history:
        await callback.message.edit_text('🧾 To\'lovlar tarixi bo\'sh.', reply_markup=wallet_kb())
        await callback.answer()
        return
    icons = {'pending': '⏳', 'approved': '✅', 'rejected': '❌'}
    lines = ['🧾 <b>To\'lovlar tarixi</b>\n']
    for amount, months, status, created, reason in history:
        line = f"{icons.get(status, '•')} {amount:,} so'm — {str(created)[:16]}"
        if status == 'rejected' and reason:
            line += f'\n   ↳ {reason}'
        lines.append(line)
    await callback.message.edit_text('\n'.join(lines), reply_markup=wallet_kb(), parse_mode='HTML')
    await callback.answer()


@router.message(F.text == '🚀 Bot yaratish')
async def on_bot_yasash(message: Message):
    kino_price = await get_kino_monthly_price()
    media_price = await get_media_monthly_price()
    shop_price = await get_shop_monthly_price()
    trial = await can_use_trial(message.from_user.id)
    await message.answer(
        '🤖 <b>BotCraft xizmatlari</b>\n\n'
        '🎬 Kino Bot — kino/serial baza, post va qidiruv\n'
        '📥 Save Bot — YouTube / Instagram / TikTok yuklovchi\n'
        '🛍 Shop Bot — mahsulot katalogi, savatcha va buyurtmalar\n\n'
        "Kerakli turini tanlang. Pastda 20+ tur ko'rinadi, hozircha faqat Kino, Save va Shop ishlaydi:",
        reply_markup=bot_type_kb(kino_price, media_price, shop_price, trial), parse_mode='HTML'
    )


@router.callback_query(F.data == 'back_types')
async def back_types(callback: CallbackQuery):
    kino_price = await get_kino_monthly_price()
    media_price = await get_media_monthly_price()
    shop_price = await get_shop_monthly_price()
    trial = await can_use_trial(callback.from_user.id)
    await callback.message.edit_text('🤖 <b>Bot turlarini tanlang</b>', reply_markup=bot_type_kb(kino_price, media_price, shop_price, trial), parse_mode='HTML')
    await callback.answer()



@router.callback_query(F.data.startswith('coming_'))
async def coming_soon_cb(callback: CallbackQuery):
    await callback.answer("Bu bot turi tez orada qo'shiladi", show_alert=True)

@router.callback_query(F.data.in_(['type_kino', 'type_media', 'type_shop']))
async def choose_bot_type(callback: CallbackQuery):
    bot_type = {'type_kino': 'kino', 'type_media': 'media', 'type_shop': 'shop'}[callback.data]
    price_getters = {'kino': get_kino_monthly_price, 'media': get_media_monthly_price, 'shop': get_shop_monthly_price}
    price = await price_getters[bot_type]()
    trial = await can_use_trial(callback.from_user.id)
    label = {'kino': '🎬 Kino Bot', 'media': '📥 Save Bot', 'shop': '🛍 Shop Bot'}[bot_type]
    await callback.message.edit_text(f'{label}\n\nTarifni tanlang:', reply_markup=plan_select_kb(bot_type, price, trial), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.regexp(r'^choose_(kino|media|shop)_(trial|paid)$'))
async def choose_plan(callback: CallbackQuery, state: FSMContext):
    _, bot_type, plan_mode = callback.data.split('_')
    if plan_mode == 'trial' and not await can_use_trial(callback.from_user.id):
        await callback.answer('Test tarif allaqachon ishlatilgan', show_alert=True)
        return
    price_getters = {'kino': get_kino_monthly_price, 'media': get_media_monthly_price, 'shop': get_shop_monthly_price}
    price = 0 if plan_mode == 'trial' else await price_getters[bot_type]()
    if price > 0 and await get_balance(callback.from_user.id) < price:
        await callback.answer('Balans yetarli emas', show_alert=True)
        return
    await state.set_state(CreateBot.waiting_token)
    await state.update_data(bot_type=bot_type, plan_code=('trial_10' if plan_mode == 'trial' else 'paid_30'), price=price, duration_days=(await get_trial_days() if plan_mode == 'trial' else 30))
    await callback.message.answer('🔑 <b>1-qadam: Bot tokenini yuboring</b>\n\n@BotFather ichiga kiring → /newbot → bot yarating → olingan tokenni shu yerga yuboring.', parse_mode='HTML')
    await callback.answer()


@router.message(CreateBot.waiting_token)
async def on_token(message: Message, state: FSMContext):
    token = (message.text or '').strip()
    if ':' not in token or len(token) < 20:
        await message.answer('❌ Token formati noto\'g\'ri.')
        return
    try:
        test_bot = Bot(token=token)
        info = await test_bot.get_me()
        await test_bot.session.close()
    except Exception as e:
        await message.answer(f'❌ Token ishlamaydi: <code>{str(e)[:120]}</code>', parse_mode='HTML')
        return
    existing = await token_exists(token)
    if existing and int(existing[3] or 0):
        await message.answer(f'❌ Bu token bilan allaqachon @{existing[2] or info.username} ishlayapti.')
        return
    data = await state.get_data()
    await state.update_data(token=token, bot_username=info.username)
    if data.get('bot_type') in {'media', 'shop'}:
        await state.set_state(CreateBot.waiting_admin_id)
        await message.answer(f"✅ Bot: <b>@{info.username}</b>\n\n👤 Endi shu child-bot admin paneliga kirishi kerak bo'lgan Telegram ID ni yuboring.\nMasalan: <code>123456789</code>", parse_mode="HTML")
    else:
        await state.set_state(CreateBot.waiting_channel)
        await message.answer(f"✅ Bot: <b>@{info.username}</b>\n\n📢 <b>2-qadam:</b> kino bazasi bo'ladigan kanalni yuboring.\nYuborish formati: <code>@kanal</code> yoki <code>-100...</code>.\n⚠️ Muhim: yaratayotgan botingiz o'sha kanalga admin qilingan bo'lishi kerak.", parse_mode="HTML")


@router.message(CreateBot.waiting_channel)
async def on_channel(message: Message, state: FSMContext):
    channel_id = (message.text or '').strip()
    if not channel_id or (not channel_id.startswith('@') and not channel_id.startswith('-100')):
        await message.answer("❌ Kanal noto'g'ri. <code>@kanal</code> yoki <code>-100...</code> yuboring.", parse_mode='HTML')
        return
    data = await state.get_data()
    token = data.get('token')
    if token:
        try:
            check_bot = Bot(token=token)
            info = await check_bot.get_me()
            member = await check_bot.get_chat_member(channel_id, info.id)
            await check_bot.session.close()
            if member.status not in ('administrator', 'creator'):
                await message.answer("❌ Bot kanalga admin qilinmagan. Avval child-botni kanalga admin qiling.", parse_mode='HTML')
                return
        except Exception as e:
            await message.answer(f"❌ Kanalni tekshirib bo'lmadi: <code>{str(e)[:180]}</code>\nBot kanalga qo'shilib admin qilinganini tekshiring.", parse_mode="HTML")
            return
    await state.update_data(channel_id=channel_id)
    await state.set_state(CreateBot.waiting_privacy)
    await message.answer('🔐 <b>3-qadam:</b> kanal turini tanlang.', reply_markup=privacy_kb(), parse_mode='HTML')


@router.callback_query(F.data.in_(['privacy_public', 'privacy_private']))
async def on_privacy(callback: CallbackQuery, state: FSMContext):
    await state.update_data(channel_type=('public' if callback.data.endswith('public') else 'private'))
    await state.set_state(CreateBot.waiting_admin_id)
    await callback.message.edit_text("👤 <b>4-qadam:</b> yaratayotgan bot admin paneliga kirishi kerak bo'lgan Telegram ID ni yuboring.\nMasalan: <code>123456789</code>", parse_mode="HTML")
    await callback.answer()


@router.message(CreateBot.waiting_admin_id)
async def on_admin_id(message: Message, state: FSMContext):
    if not (message.text or '').strip().isdigit():
        await message.answer('❌ Admin ID raqam bo\'lishi kerak.')
        return
    admin_id = int((message.text or '').strip())
    await state.update_data(admin_id=admin_id)
    data = await state.get_data()
    await state.set_state(CreateBot.confirming)
    balance = await get_balance(message.from_user.id)
    bot_type_label = {'kino': 'Kino Bot', 'media': 'Save Bot', 'shop': 'Shop Bot'}.get(data['bot_type'], 'Bot')
    await message.answer(
        '📋 <b>Tekshiruv</b>\n\n'
        f"🤖 Bot: @{data['bot_username']}\n"
        f"🧩 Turi: {bot_type_label}\n"
        + (f"📢 Kanal: <code>{data.get('channel_id','—')}</code>\n" if data['bot_type']=='kino' else '')
        + (f"🔐 Kanal turi: {data.get('channel_type','—')}\n" if data['bot_type']=='kino' else '')
        + f"👤 Admin ID: <code>{admin_id}</code>\n"
        + f"💵 To'lov: <b>{int(data.get('price',0)):,} so'm</b>\n"
        + f"💳 Balans: <b>{balance:,} so'm</b>",
        reply_markup=confirm_kb(), parse_mode='HTML'
    )


@router.callback_query(F.data == 'confirm_create')
async def on_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    price = int(data.get('price', 0))
    duration_days = int(data.get('duration_days', 30))
    plan_code = data.get('plan_code', 'paid_30')
    bot_type = data.get('bot_type', 'kino')
    if price > 0 and not await deduct_balance(callback.from_user.id, price):
        await callback.message.answer('❌ Balans yetarli emas.', reply_markup=main_menu_kb())
        await callback.answer()
        return
    server_code = await choose_available_server()
    if not server_code:
        await add_waitlist(callback.from_user.id, bot_type, plan_code)
        if price > 0:
            await add_balance(callback.from_user.id, price)
        await callback.message.answer(
            "⚠️ <b>Hozircha bo'sh server qolmagan.</b>\n\nIltimos biroz kuting. Yangi server qo'shilganda sizga xabar beramiz.",
            parse_mode='HTML',
            reply_markup=main_menu_kb(),
        )
        admin_id = int(os.getenv('MAIN_ADMIN_ID', '0') or 0)
        if admin_id:
            try:
                await bot.send_message(
                    admin_id,
                    f"⚠️ Serverda bo'sh joy qolmadi.\nUser: <code>{callback.from_user.id}</code>\nBot turi: <b>{bot_type}</b>\nPlan: <b>{plan_code}</b>",
                    parse_mode='HTML',
                )
            except Exception:
                logger.exception('Admin ga server full xabari yuborilmadi')
        await callback.answer()
        return
    wait_msg = await callback.message.answer(f'⏳ <b>Child bot yaratilmoqda...</b>\n🖥 Server: <b>{server_code}</b>', parse_mode='HTML')
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path, cwd, env, child_log_path = build_child_process(
        project_root,
        bot_type=bot_type,
        token=data['token'],
        owner_id=callback.from_user.id,
        admin_id=data['admin_id'],
        channel_id=data.get('channel_id', ''),
        channel_type=data.get('channel_type', 'public'),
        bot_username=data.get('bot_username', ''),
    )
    if bot_type == 'kino':
        env['KINO_ADMIN_USERNAME'] = '@' + (callback.from_user.username or 'admin')
    proc = None
    try:
        import subprocess, sys
        with open(child_log_path, 'ab') as child_log:
            proc = subprocess.Popen([sys.executable, script_path], env=env, cwd=cwd, stdout=child_log, stderr=child_log)
        await asyncio.sleep(3)
        if proc.poll() is not None:
            raise RuntimeError(f'Child bot ishga tushmadi. Log: {child_log_path}')
        await save_bot(callback.from_user.id, callback.from_user.username or '', data['token'], data['bot_username'], data.get('channel_id',''), data.get('channel_type','public'), data['admin_id'], proc.pid, days=duration_days, plan_code=plan_code, price_paid=price, bot_type=bot_type, server_code=server_code)
        if plan_code == 'trial_10':
            await mark_trial_used(callback.from_user.id)
        referral_bonus = await reward_referral_if_eligible(callback.from_user.id)
        new_balance = await get_balance(callback.from_user.id)
        bot_type_label = {'kino': 'Kino Bot', 'media': 'Save Bot', 'shop': 'Shop Bot'}.get(bot_type, 'Bot')
        await wait_msg.edit_text(
            '🎉 <b>Bot muvaffaqiyatli yaratildi!</b>\n\n'
            f"🤖 @{data['bot_username']}\n"
            f"🧩 {bot_type_label}\n"
            f"⏳ Muddat: {duration_days} kun\n"
            f"💵 To'lov: {price:,} so'm\n"
            f"💳 Qolgan balans: {new_balance:,} so'm\n\n"
            f"🚀 https://t.me/{data['bot_username']}",
            parse_mode='HTML'
        )
        if referral_bonus:
            await callback.message.answer(f'🎁 Referat bonusi tushdi: {referral_bonus:,} so\'m')
        await callback.message.answer('✨ BotCraft asosiy menyusi', reply_markup=main_menu_kb())
    except Exception as e:
        if price > 0:
            await add_balance(callback.from_user.id, price)
        if proc and proc.poll() is None:
            proc.terminate()
        await wait_msg.edit_text(f'❌ <b>Xato yuz berdi:</b> <code>{str(e)[:3000]}</code>\n\nPul balansingizga qaytarildi.', parse_mode='HTML')
        await callback.message.answer('🏠 Asosiy menyu', reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == 'cancel_create')
async def on_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer('❌ Bekor qilindi.', reply_markup=main_menu_kb())
    await callback.answer()


@router.message(F.text == '📦 Mening botlarim')
async def on_my_bots_reply(message: Message):
    bots = await get_user_bots(message.from_user.id)
    if not bots:
        await message.answer('📋 Sizda hali bot yo\'q.')
        return
    for i, row in enumerate(bots, 1):
        # Backward/forward compatible unpacking: older DB/query had 11 columns,
        # newer version adds server_code as the 12th column.
        uname, ch, chtype, created, active, token, expires_at, bot_id, plan_code, price_paid, bot_type, *rest = row
        server_code = rest[0] if rest else 'main'
        is_blocked = bool(rest[1]) if len(rest) > 1 else False
        exp = str(expires_at)[:10] if expires_at else '—'
        bot_type_title = {'kino': 'Kino Bot', 'media': 'Media Saver Bot', 'shop': 'Shop Bot'}.get(bot_type, 'Bot')
        await message.answer(
            f"<b>{i}. @{uname}</b>\n"
            f"🧩 Turi: {bot_type_title}\n"
            f"📢 Kanal: <code>{ch or 'kerak emas'}</code>\n"
            f"🖥 Server: <b>{server_code or 'main'}</b>\n"
            f"📅 Tugash: <b>{exp}</b>\n"
            f"📌 Holat: {'Bloklangan ⛔' if is_blocked else ('Faol ✅' if active else 'To\'xtagan ❌')}",
            reply_markup=my_bot_actions_kb(bot_id, bool(active)), parse_mode='HTML'
        )


@router.callback_query(F.data.regexp(r'^extend_bot_\d+_\d+$'))
async def extend_bot_cb(callback: CallbackQuery):
    _, _, bot_id, months = callback.data.split('_')
    bot_id = int(bot_id); months = int(months)
    price = PRICE_MAP.get(months, 49_000)
    balance = await get_balance(callback.from_user.id)
    if balance < price:
        await callback.answer('Balans yetarli emas', show_alert=True)
        return
    bot_row = await get_bot_by_id(bot_id)
    if not bot_row or bot_row[1] != callback.from_user.id:
        await callback.answer('Bu bot sizga tegishli emas', show_alert=True)
        return
    await deduct_balance(callback.from_user.id, price)
    new_exp = await extend_bot_subscription(bot_id, months)
    await callback.message.edit_text(f'✅ Muddat uzaytirildi.\n\n⏰ Yangi muddat: <b>{str(new_exp)[:10]}</b>', parse_mode='HTML')
    await callback.answer('Uzaytirildi')


@router.message(Command('admin'))
async def cmd_admin(message: Message):
    if not await is_main_admin(message.from_user.id):
        return
    web_url = os.getenv('WEB_ADMIN_URL', 'http://127.0.0.1:8000')
    web_user = os.getenv('WEB_ADMIN_USERNAME', 'admin')
    web_pass = os.getenv('WEB_ADMIN_PASSWORD', 'admin123')
    await message.answer(
        f"🌐 <b>Admin web panel</b>\n\n🔗 Link: {web_url}\n👤 Login: <code>{web_user}</code>\n🔐 Parol: <code>{web_pass}</code>\n\nKirgandan keyin profil sahifasidan login/parolni almashtirib oling.",
        parse_mode='HTML'
    )


@router.callback_query(F.data == 'admin_back')
async def admin_back_cb(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        return
    await callback.message.edit_text('👮 <b>BotCraft admin paneli</b>', reply_markup=admin_panel_kb(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'admin_payments')
async def admin_payments_cb(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        return
    payments = await get_pending_payments()
    if not payments:
        await callback.message.edit_text('✅ Kutayotgan to\'lov yo\'q.', reply_markup=admin_panel_kb())
        await callback.answer()
        return
    await callback.message.edit_text(f'💰 Kutayotgan to\'lovlar: <b>{len(payments)}</b>', reply_markup=admin_panel_kb(), parse_mode='HTML')
    for pay in payments:
        pay_id, user_id, amount, months, file_id, created, fname, uname = pay
        caption = f'💰 <b>To\'lov #{pay_id}</b>\n👤 {fname or uname or "—"}\n🆔 <code>{user_id}</code>\n💵 {amount:,} so\'m\n📅 {str(created)[:16]}'
        try:
            await callback.message.answer_photo(file_id, caption=caption, reply_markup=payment_action_kb(pay_id, user_id), parse_mode='HTML')
        except Exception:
            await callback.message.answer(caption, reply_markup=payment_action_kb(pay_id, user_id), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.regexp(r'^pay_approve_\d+_\d+$'))
async def pay_approve_cb(callback: CallbackQuery, bot: Bot):
    if not await is_main_admin(callback.from_user.id):
        return
    _, _, pay_id, user_id = callback.data.split('_')
    payment_id = int(pay_id); user_id = int(user_id)
    payments = await get_pending_payments()
    amount = next((p[2] for p in payments if p[0] == payment_id), 0)
    await approve_payment(payment_id, user_id, amount)
    await callback.answer('Tasdiqlandi')
    try:
        await bot.send_message(user_id, f'✅ To\'lov tasdiqlandi.\n💰 {amount:,} so\'m balansga qo\'shildi.', parse_mode='HTML')
    except Exception:
        pass
    if callback.message.photo:
        await callback.message.edit_caption(caption='✅ Tasdiqlandi', parse_mode='HTML')
    else:
        await callback.message.edit_text('✅ Tasdiqlandi')


@router.callback_query(F.data.regexp(r'^pay_reject_\d+_\d+$'))
async def pay_reject_cb(callback: CallbackQuery, state: FSMContext):
    if not await is_main_admin(callback.from_user.id):
        return
    _, _, pay_id, user_id = callback.data.split('_')
    await state.set_state(AdminStates.waiting_reject_reason)
    await state.update_data(reject_payment_id=int(pay_id), reject_user_id=int(user_id))
    await callback.message.answer('✏️ Rad etish sababini yuboring.')
    await callback.answer()


@router.message(AdminStates.waiting_reject_reason)
async def reject_reason_received(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data(); await state.clear()
    await reject_payment(data['reject_payment_id'], message.text or 'Sabab ko\'rsatilmagan')
    try:
        await bot.send_message(data['reject_user_id'], f'❌ To\'lov rad etildi.\nSabab: {message.text}')
    except Exception:
        pass
    await message.answer('✅ To\'lov rad etildi.', reply_markup=admin_panel_kb())


@router.callback_query(F.data == 'admin_users')
async def admin_users_cb(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        return
    users = await get_all_main_users()
    text = [f'👥 <b>Foydalanuvchilar: {len(users)} ta</b>']
    for uid, uname, fname, bal, bots in users[:30]:
        text.append(f'• <code>{uid}</code> {fname or uname or "—"} — {bal:,} so\'m | {bots} bot')
    await callback.message.edit_text('\n'.join(text), reply_markup=admin_panel_kb(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'admin_stats')
async def admin_stats_cb(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        return
    users = await get_all_main_users()
    pending = await get_pending_payments()
    total_balance = sum(int(u[3] or 0) for u in users)
    total_bots = sum(int(u[4] or 0) for u in users)
    await callback.message.edit_text(f'📊 <b>Statistika</b>\n\n👥 Userlar: {len(users)}\n🤖 Botlar: {total_bots}\n💰 Balanslar jami: {total_balance:,} so\'m\n⏳ Kutayotgan to\'lovlar: {len(pending)}', reply_markup=admin_panel_kb(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'admin_broadcast')
async def admin_broadcast_cb(callback: CallbackQuery, state: FSMContext):
    if not await is_main_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.message.answer('📢 Yuboriladigan xabarni/rasmni/videoni caption bilan yuboring. U barcha BotCraft userlariga tarqatiladi.')
    await callback.answer()


@router.message(AdminStates.waiting_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not await is_main_admin(message.from_user.id):
        return
    await state.clear()
    users = await get_all_main_users()
    success = 0
    for uid, *_ in users:
        try:
            if message.photo:
                await bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await bot.send_video(uid, message.video.file_id, caption=message.caption)
            else:
                await bot.send_message(uid, message.text or message.caption or '')
            success += 1
        except Exception:
            pass
    await message.answer(f'✅ Reklama yuborildi: {success}/{len(users)}', reply_markup=admin_panel_kb())



@router.callback_query(F.data == 'admin_main_subs')
async def admin_main_subs_cb(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        return
    channels = await get_main_required_channels()
    info = f"📢 <b>Majburiy obuna</b>\n\nUlangan kanallar: <b>{len(channels)}</b> ta"
    await callback.message.edit_text(info, reply_markup=main_sub_manage_kb(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'main_sub_add')
async def main_sub_add_cb(callback: CallbackQuery, state: FSMContext):
    if not await is_main_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_sub_id)
    await callback.message.answer(
        "📥 Kanal ID yoki username yuboring.\n\nMisol: <code>@kanalim</code> yoki <code>-1001234567890</code>",
        parse_mode='HTML'
    )
    await callback.answer()


@router.message(AdminStates.waiting_sub_id)
async def main_sub_id_received(message: Message, state: FSMContext):
    if not await is_main_admin(message.from_user.id):
        return
    channel_id = _normalize_channel_id(message.text)
    if not channel_id or (not channel_id.startswith('@') and not channel_id.startswith('-100')):
        await message.answer("❌ Noto'g'ri format. <code>@kanal</code> yoki <code>-100...</code> yuboring.", parse_mode='HTML')
        return
    await state.update_data(main_sub_id=channel_id)
    await state.set_state(AdminStates.waiting_sub_name)
    await message.answer("✍️ Kanal nomini yuboring. Masalan: <code>Bizning kanal</code>", parse_mode='HTML')


@router.message(AdminStates.waiting_sub_name)
async def main_sub_name_received(message: Message, state: FSMContext):
    if not await is_main_admin(message.from_user.id):
        return
    channel_name = (message.text or '').strip()
    if not channel_name:
        await message.answer("❌ Kanal nomini yuboring.")
        return
    await state.update_data(main_sub_name=channel_name)
    await state.set_state(AdminStates.waiting_sub_url)
    await message.answer(
        "🔗 Kanal linkini yuboring.\n\nMisol: <code>https://t.me/kanalim</code>\nAgar username bilan ishlamoqchi bo'lsangiz /skip yuboring.",
        parse_mode='HTML'
    )


@router.message(AdminStates.waiting_sub_url)
async def main_sub_url_received(message: Message, state: FSMContext):
    if not await is_main_admin(message.from_user.id):
        return
    data = await state.get_data()
    await state.clear()
    channel_id = data['main_sub_id']
    channel_name = data['main_sub_name']
    raw = (message.text or '').strip()
    channel_url = '' if raw == '/skip' else raw
    if not channel_url and channel_id.startswith('@'):
        channel_url = f"https://t.me/{channel_id.lstrip('@')}"
    await add_main_required_channel(channel_id, channel_name, channel_url)
    await message.answer("✅ Kanal majburiy obunaga qo'shildi.", reply_markup=admin_panel_kb())


@router.callback_query(F.data == 'main_sub_list')
async def main_sub_list_cb(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        return
    channels = await get_main_required_channels()
    if not channels:
        await callback.message.edit_text("📭 Majburiy obuna kanallari yo'q.", reply_markup=main_sub_manage_kb())
        await callback.answer()
        return
    lines = ["📋 <b>Majburiy obuna kanallari</b>"]
    for ch_id, ch_name, ch_url in channels:
        lines.append(f"• <b>{ch_name or '—'}</b>\nID: <code>{ch_id}</code>\nLink: {ch_url or '—'}")
    await callback.message.edit_text('\n\n'.join(lines), reply_markup=main_sub_manage_kb(), parse_mode='HTML', disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data == 'main_sub_remove')
async def main_sub_remove_cb(callback: CallbackQuery, state: FSMContext):
    if not await is_main_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_rem_sub)
    await callback.message.answer("🗑 O'chiriladigan kanal ID yoki username sini yuboring.", parse_mode='HTML')
    await callback.answer()


@router.message(AdminStates.waiting_rem_sub)
async def main_sub_remove_received(message: Message, state: FSMContext):
    if not await is_main_admin(message.from_user.id):
        return
    channel_id = _normalize_channel_id(message.text)
    await remove_main_required_channel(channel_id)
    await state.clear()
    await message.answer("✅ Kanal majburiy obunadan o'chirildi.", reply_markup=admin_panel_kb())


@router.callback_query(F.data == 'admin_prices')
async def admin_prices_cb(callback: CallbackQuery):
    if not await is_main_admin(callback.from_user.id):
        return
    kino = await get_kino_monthly_price(); media = await get_media_monthly_price(); shop = await get_shop_monthly_price(); ref = await get_referral_bonus()
    await callback.message.edit_text(f'💸 <b>Tariflar</b>\n\n🎬 Kino: {kino:,} so\'m\n📥 Media: {media:,} so\'m\n🛍 Shop: {shop:,} so\'m\n🎁 Referat: {ref:,} so\'m', reply_markup=admin_price_kb(), parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data.in_(['setprice_kino', 'setprice_media', 'setprice_shop', 'setprice_ref', 'setprice_trial', 'setcard_number', 'setcard_owner']))
async def setprice_cb(callback: CallbackQuery, state: FSMContext):
    if not await is_main_admin(callback.from_user.id):
        return
    key_map = {'setprice_kino': 'kino_paid_30', 'setprice_media': 'media_paid_30', 'setprice_shop': 'shop_paid_30', 'setprice_ref': 'referral_bonus', 'setprice_trial': 'trial_days', 'setcard_number': 'payment_card', 'setcard_owner': 'payment_card_owner'}
    await state.set_state(AdminStates.waiting_price)
    await state.update_data(setting_key=key_map[callback.data])
    prompt = '✍️ Yangi qiymatni yuboring.' if callback.data in ('setcard_number', 'setcard_owner') else '✍️ Yangi summani raqamda yuboring.'
    await callback.message.answer(prompt)
    await callback.answer()


@router.message(AdminStates.waiting_price)
async def setprice_save(message: Message, state: FSMContext):
    if not await is_main_admin(message.from_user.id):
        return
    raw_text = (message.text or '').strip()
    data = await state.get_data()
    await state.clear()
    setting_key = data['setting_key']
    if setting_key in {'payment_card', 'payment_card_owner'}:
        if not raw_text:
            await message.answer("❌ Bo'sh qiymat yubormang.")
            return
        await set_setting(setting_key, raw_text)
        await message.answer('✅ Saqlandi.', reply_markup=admin_panel_kb())
        return
    txt = raw_text.replace(' ', '')
    if not txt.isdigit():
        await message.answer('❌ Faqat raqam yuboring.')
        return
    await set_setting(setting_key, int(txt))
    await message.answer('✅ Saqlandi.', reply_markup=admin_panel_kb())