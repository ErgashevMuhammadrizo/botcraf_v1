from aiogram.fsm.state import State, StatesGroup


class OrderState(StatesGroup):
    full_name = State()
    phone = State()
    address = State()
    delivery_type = State()
    payment_type = State()
    promo_code = State()
    comment = State()
    confirm = State()
    payment_screenshot = State()


class ProductState(StatesGroup):
    name = State()
    description = State()
    price = State()
    discount_price = State()
    category = State()
    images = State()
    sizes = State()
    colors = State()
    stock = State()
    sku = State()


class CategoryState(StatesGroup):
    name = State()
    emoji = State()
    edit_name = State()
    edit_emoji = State()


class PromoState(StatesGroup):
    code = State()
    discount_type = State()
    discount_value = State()
    min_order = State()
    max_uses = State()


class BroadcastState(StatesGroup):
    message = State()
    target = State()
    confirm = State()


class SettingsState(StatesGroup):
    waiting_value = State()


class AdminState(StatesGroup):
    add_id = State()
    add_role = State()


class SearchState(StatesGroup):
    query = State()
