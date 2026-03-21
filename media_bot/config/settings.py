import os
import shutil
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.getenv("MEDIA_BOT_BASE_DIR", os.getcwd())
os.makedirs(BASE_DIR, exist_ok=True)

# ===== BOT =====
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "123456789").split(",")))

# ===== PAPKALAR =====
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
for _p in (DOWNLOADS_DIR, DATA_DIR, LOGS_DIR):
    os.makedirs(_p, exist_ok=True)

# ===== CHEKLOVLAR =====
MAX_FILE_SIZE_MB = 50
DOWNLOAD_TIMEOUT = 180

# ===== FFMPEG =====
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None

# ===== MAJBURIY OBUNA KANALLARI =====
# Format: [{"id": -100123456, "username": "channel_username", "title": "Kanal nomi"}]
REQUIRED_CHANNELS = [
    # {"id": -1001234567890, "username": "your_channel", "title": "Mening kanalim"},
]

# ===== PREMIUM NARXLARI =====
PREMIUM_PRICES = {
    "monthly": {"amount": 15000, "label": "1 oy — 15,000 so'm"},
    "quarterly": {"amount": 40000, "label": "3 oy — 40,000 so'm"},
    "yearly": {"amount": 120000, "label": "1 yil — 120,000 so'm"},
}

# ===== TO'LOV KARTA =====
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "8600 0000 0000 0000")
PAYMENT_CARD_OWNER = os.getenv("PAYMENT_CARD_OWNER", "Ism Familiya")

# ===== SIFAT VARIANTLARI =====
# premium=True → faqat premium foydalanuvchilar uchun
QUALITY_OPTIONS = {
    "480p": {
        "label": "📱 480p SD",
        "format": "best[height<=480][ext=mp4]/best[height<=480]/best",
        "premium": False,
    },
    "720p": {
        "label": "📺 720p HD",
        "format": "best[height<=720][ext=mp4]/best[height<=720]/best",
        "premium": False,
    },
    "1080p": {
        "label": "📹 1080p Full HD ⭐",
        "format": (
            "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
            if FFMPEG_AVAILABLE
            else "best[height<=1080][ext=mp4]/best[height<=1080]/best"
        ),
        "premium": True,
    },
    "best": {
        "label": "🔥 Eng yaxshi sifat ⭐",
        "format": (
            "bestvideo+bestaudio/best"
            if FFMPEG_AVAILABLE
            else "best[ext=mp4]/best"
        ),
        "premium": True,
    },
    "audio": {
        "label": "🎵 Faqat Audio (MP3)",
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "premium": False,
    },
}
