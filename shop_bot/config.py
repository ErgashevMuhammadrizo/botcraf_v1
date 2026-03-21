import os
from dotenv import load_dotenv

BASE_DIR = os.getenv('SHOP_BOT_BASE_DIR', os.getcwd())
os.makedirs(BASE_DIR, exist_ok=True)
load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
]

# Order statuses
ORDER_STATUSES = {
    "new": "🆕 Yangi",
    "confirmed": "✅ Tasdiqlandi",
    "delivering": "🚚 Yetkazilmoqda",
    "on_way": "📍 Yo'lda",
    "closed": "🎉 Yopildi",
    "cancelled": "❌ Bekor qilindi",
}

DELIVERY_TYPES = {
    "courier": "🚚 Kuryer orqali",
    "pickup": "🏪 Olib ketish",
}

PAYMENT_TYPES = {
    "cash": "💵 Naqd",
    "card": "💳 Karta o'tkazmasi",
    "click": "📱 Click/Payme",
}
