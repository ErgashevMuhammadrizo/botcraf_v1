# BotCraft + Admin Web ishga tushirish

## 1. Kutubxonalar
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Env tayyorlash
```bash
cp .env.example .env
nano .env
```
Muhim maydonlar:
- MAIN_BOT_TOKEN
- MAIN_ADMIN_ID
- WEB_ADMIN_URL
- WEB_ADMIN_USERNAME
- WEB_ADMIN_PASSWORD

## 3. Admin webni ishga tushirish
```bash
python run_admin_web.py
```
Brauzerda oching: `http://SERVER_IP:8000`

## 4. Asosiy botni ishga tushirish
```bash
python run_main_bot.py
```

## 5. Telegramdan admin panel
Asosiy botda `/admin` yuboring. Bot sizga web panel linki va login/parolni yuboradi.

## 6. Sahifalar
- `/dashboard`
- `/users`
- `/bots`
- `/payments`
- `/nodes`
- `/settings`

## 7. Birinchi ish
- settings sahifasidan admin login/parolni almashtiring
- payment karta ma'lumotlarini kiriting
- tarif narxlarini tekshiring
- node/server qo'shing

## 8. Eslatma
Bu MVP panel. Child botlarni boshqa serverga avtomatik deploy qilish hali keyingi bosqich uchun qoldirilgan.
