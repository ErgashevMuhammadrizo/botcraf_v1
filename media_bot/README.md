# 🎬 MediaBot v3.0

Professional Telegram media downloader bot — YouTube, Instagram, TikTok.

## ✨ Xususiyatlar

| Funksiya | Tavsif |
|---------|--------|
| 📥 Yuklab olish | YouTube, Instagram, TikTok |
| 🎞 Sifat tanlash | 480p, 720p bepul · 1080p, Best premium |
| 🎵 Audio | MP3 yuklab olish |
| ⭐ Premium | Oylik/kvartal/yillik tariflar |
| 💳 To'lov | Karta + chek screenshot orqali |
| 📢 Majburiy obuna | Kanal obunasini tekshirish |
| 👑 Admin panel | Broadcast, ban, premium berish, kanallar |

## 🚀 O'rnatish

```bash
# 1. Papkaga o'tish
cd mediabot

# 2. Venv yaratish
python3 -m venv venv
source venv/bin/activate

# 3. Kutubxonalar
pip install -r requirements.txt

# 4. Sozlash
cp .env.example .env
nano .env   # BOT_TOKEN va ADMIN_IDS ni to'ldiring

# 5. Ishga tushirish
python bot.py
```

## ⚙️ Sozlamalar (config/settings.py)

```python
# Majburiy obuna kanallarini qo'shish:
REQUIRED_CHANNELS = [
    {"id": -1001234567890, "username": "my_channel", "title": "Mening kanalim"},
]

# Premium narxlarini o'zgartirish:
PREMIUM_PRICES = {
    "monthly": {"amount": 15000, "label": "1 oy — 15,000 so'm"},
    ...
}
```

Yoki admin panel orqali kanallarni qo'shish: `/admin` → 📡 Kanallar

## 👑 Admin buyruqlari

| Buyruq | Tavsif |
|--------|--------|
| `/admin` | Admin panel |
| `/stats` | Statistika |
| `/ban <id>` | Ban qilish |
| `/unban <id>` | Unban |
| `/premium <id> <plan>` | Premium berish |

## 💳 Premium tariflar

- `monthly` — 1 oy
- `quarterly` — 3 oy  
- `yearly` — 1 yil

## 📁 Struktura

```
mediabot/
├── bot.py              # Asosiy fayl
├── config/settings.py  # Sozlamalar
├── handlers/
│   ├── start.py        # /start, /help
│   ├── download.py     # Yuklab olish
│   ├── premium.py      # Premium/to'lov
│   └── admin.py        # Admin panel
└── utils/
    ├── downloader.py   # yt-dlp
    ├── database.py     # SQLite
    ├── keyboards.py    # Tugmalar
    ├── subscription.py # Obuna tekshiruvi
    └── helpers.py      # Yordamchilar
```

## 🔧 ffmpeg (ixtiyoriy, lekin tavsiya etiladi)

```bash
sudo apt install ffmpeg -y
```

ffmpeg bo'lmasa ham bot ishlaydi — faqat 1080p biroz past bo'lishi mumkin.
