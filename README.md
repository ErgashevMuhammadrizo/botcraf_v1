# 🎬 BotCraft Tizimi — To'liq Versiya

## 📁 Papka tuzilmasi

```
kinobot_project/
├── run_main_bot.py              ← Asosiy botni ishga tushirish
├── main_bot/
│   ├── database.py              ← Botlar + foydalanuvchilar + to'lovlar
│   ├── handlers.py              ← Barcha handlerlar (hamyon, admin panel...)
│   └── keyboards.py             ← Reply + Inline tugmalar
├── kino_bot/
│   ├── run_kino_bot.py          ← Subprocess entry point
│   ├── database.py              ← Kinolar, seriallar, userlar
│   ├── keyboards.py             ← User + Admin klaviaturalar
│   ├── utils.py                 ← Kod generatsiya, kanal post, obuna tekshirish
│   └── handlers/
│       ├── user_handlers.py     ← /start (deep link), qidiruv, profil
│       └── admin_handlers.py    ← Kino/serial qo'shish (poster+video), ban...
├── data/                        ← SQLite bazalar (avtomatik)
├── logs/                        ← Loglar (avtomatik)
├── requirements.txt
└── .env.example → .env
```

---

## ⚙️ O'rnatish

```bash
pip install -r requirements.txt
cp .env.example .env
# .env faylini to'ldiring
python run_main_bot.py
```

## 🔧 .env fayli

```
MAIN_BOT_TOKEN=1234567890:ABC...
MAIN_ADMIN_ID=123456789
DB_PATH=data/main_bot.db
```

---

## 🤖 Asosiy bot xususiyatlari

- **Reply klaviatura** — /start bosilganda pastda chiqadi
- **🤖 Bot yasash** → Kino Bot → Token → Kanal → Admin ID
- **💰 Hamyon** → Balans, tarix, to'ldirish (chek yuborish)
- **📋 Mening botlarim** → Yaratilgan botlar ro'yxati
- **/admin** → To'lovlarni tasdiqlash, foydalanuvchilar, statistika

## 💰 To'lov tizimi

1. User **"💰 Hamyon"** → **"💳 Balans to'ldirish"** → muddat tanlaydi
2. Rekvizit ko'rsatiladi → User chek fotosini yuboradi
3. Admin **/admin** → **"💰 To'lovlarni tasdiqlash"** → tasdiqlash/rad etish
4. Tasdiqlansa — balansi to'ldiriladi, userga xabar
5. Rad etilsa — sabab so'raladi, userga sabab yuboriladi

---

## 🎬 Kino bot xususiyatlari

### User panel (faqat):
- 🔍 Kino qidirish
- 👤 Profil
- 📞 Admin bilan bog'lanish
- 4 xonali kod yozib kino olish

### Admin panel (/admin):
- 🎬 Kino qo'shish (poster rasm + video)
- 📺 Serial qo'shish (mavsum/qism + poster + video)
- 🗑 Kino/serial o'chirish (kanaldan ham)
- 👥 Foydalanuvchilar + /ban [id] / /unban [id]
- 📢 Majburiy obuna (ochiq/yopiq kanal)
- 🌐 Ijtimoiy tarmoqlar
- 👮 Adminlar boshqaruvi
- 📊 Statistika

### Kanal post tizimi:
- Kino qo'shilganda kanalga **poster + tavsif + "▶️ Tomosha qilish"** tugmali post
- Tugma bosilsa → `t.me/bot?start=KOD` → bot avtomatik kinoni yuboradi
- Video alohida yashirin arxivlanadi
- Kod: **4 xonali raqam** (masalan: 7429)


## ✅ Yangi tuzatishlar

- Media Saver botlar endi har biri alohida papka va baza bilan ishlaydi.
- Asosiy BotCraft qayta ishga tushsa, faol child botlar avtomatik qayta ko'tariladi.
- Hamyon to'ldirish oynasida karta raqami va egasi ko'rsatiladi.
- Admin panelda tariflar, test kunlari va karta ma'lumotlarini tahrirlash qo'shildi.
- Yordam bo'limida @BotFather orqali token olish qadamlari aniq yozildi.


## 🛍 Shop bot xususiyatlari

### User panel:
- 🛍 Mahsulotlar
- 📂 Kategoriyalar
- 🛒 Savatcha
- 📦 Buyurtmalarim
- ❤️ Saralanganlar
- 🔎 Qidirish
- ☎️ Aloqa
- ℹ️ Do'kon haqida

### Admin panel (/admin):
- 📦 Mahsulot qo'shish / tahrirlash / o'chirish
- 📂 Kategoriyalar boshqaruvi
- 🧾 Buyurtmalarni ko'rish va holatini yangilash
- 💳 To'lov screenshotlarini tasdiqlash
- 📣 Reklama yuborish
- 📊 Statistika
- ⚙️ Sozlamalar
