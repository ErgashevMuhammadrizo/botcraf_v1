# 🛍 Telegram Shop Bot

Aiogram 3 + SQLite asosidagi professional Telegram do'kon boti.

---

## 📁 Fayl tuzilmasi

```
shop_bot/
├── main.py                  # Bot kirish nuqtasi
├── config.py                # Konfiguratsiya
├── requirements.txt         # Kutubxonalar
├── .env                     # Muhit o'zgaruvchilari (yaratib qo'ying)
├── database/
│   └── db.py                # SQLite modellari va barcha so'rovlar
├── handlers/
│   ├── user.py              # User panel handlerlari
│   ├── order.py             # Buyurtma berish jarayoni
│   └── admin.py             # Admin panel handlerlari
├── keyboards/
│   └── keyboards.py         # Barcha tugmalar
├── middlewares/
│   └── middlewares.py       # Ban tekshiruvi
└── utils/
    ├── helpers.py           # Yordamchi funksiyalar
    └── states.py            # FSM holatlari
```

---

## ⚙️ O'rnatish

### 1. Virtual muhit yarating
```bash
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
```

### 2. Kutubxonalarni o'rnating
```bash
pip install -r requirements.txt
```

### 3. `.env` faylini yarating
```bash
cp .env.example .env
```

Faylni oching va o'zgartiring:
```
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
```

- `BOT_TOKEN` — [@BotFather](https://t.me/BotFather) dan oling
- `ADMIN_IDS` — Admin bo'ladigan Telegram ID lar (vergul bilan)

### 4. Botni ishga tushiring
```bash
python main.py
```

---

## 🚀 Funksiyalar

### 👤 User panel
| Tugma | Tavsif |
|-------|--------|
| 🛍 Mahsulotlar | Barcha mahsulotlar ro'yxati |
| 📂 Kategoriyalar | Kategoriyalar bo'yicha filterlash |
| 🛒 Savatcha | Savatcha ko'rish/tahrirlash |
| 📦 Buyurtmalarim | Buyurtmalar tarixi va holati |
| ❤️ Saralanganlar | Sevimli mahsulotlar |
| 🎁 Aksiyalar | Promo kodlar va takliflar |
| 🔎 Qidirish | Mahsulot qidirish |
| ☎️ Aloqa | Do'kon kontaktlari |
| ℹ️ Do'kon haqida | Ma'lumot, shartlar, qaytarish |

### 👨‍💼 Admin panel (`/admin`)
| Tugma | Tavsif |
|-------|--------|
| 📦 Mahsulotlar | Qo'shish/tahrirlash/o'chirish |
| 📂 Kategoriyalar | Kategoriyalar boshqaruvi |
| 🧾 Buyurtmalar | Filterlash, tasdiqlash, yetkazish |
| 👥 Mijozlar | Ban/unblock, ko'rish |
| 💳 To'lovlar | Screenshot tasdiqlash |
| 🎁 Promo kodlar | Yaratish, boshqarish |
| 📣 Reklama | Ommaviy xabar yuborish |
| 📊 Statistika | Daromad, buyurtmalar, top mahsulotlar |
| ⚙️ Sozlamalar | Do'kon ma'lumotlari, narxlar |
| 👨‍💼 Adminlar | Admin qo'shish/o'chirish |

---

## 💡 Qo'shimcha imkoniyatlar

- **Promo kodlar**: foizli yoki summali chegirma, bir martalik yoki ko'p martalik
- **Rasmlar**: bir mahsulotga bir nechta rasm
- **O'lcham/rang**: dinamik tanlash
- **Screenshot to'lov**: karta to'lovini tasdiqlash
- **Avtomatik xabarlar**: buyurtma statusi o'zgarganda userga bildirishnoma
- **Ban tizimi**: user bloklovchi middleware

---

## 🔧 Sozlamalar (Admin panel → ⚙️)

Barcha sozlamalar admin paneldan o'zgartiriladi:
- Do'kon nomi, telefon, manzil
- Yetkazib berish narxi
- Bepul yetkazib berish chegarasi
- Karta raqamlari
- Buyurtma qabul qilishni yoqish/o'chirish
- Valyuta, minimal buyurtma
