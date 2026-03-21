"""SQLite async database — users, downloads, premium, payments"""

import aiosqlite
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
from config.settings import DATA_DIR
DB_PATH = f"{DATA_DIR}/mediabot.db"


async def init_db():
    import os; os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id      INTEGER PRIMARY KEY,
                username     TEXT,
                full_name    TEXT,
                is_banned    INTEGER DEFAULT 0,
                is_premium   INTEGER DEFAULT 0,
                premium_until TEXT,
                joined_at    TEXT,
                last_active  TEXT
            );

            CREATE TABLE IF NOT EXISTS downloads (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                platform    TEXT,
                url         TEXT,
                quality     TEXT,
                status      TEXT,
                file_size   REAL DEFAULT 0,
                created_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS payments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                plan         TEXT,
                amount       INTEGER,
                status       TEXT DEFAULT 'pending',
                receipt_file TEXT,
                created_at   TEXT,
                approved_at  TEXT,
                approved_by  INTEGER
            );

            CREATE TABLE IF NOT EXISTS required_channels (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id   TEXT UNIQUE,
                username     TEXT,
                title        TEXT,
                is_active    INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        await db.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('payment_card', ?)", (os.getenv('PAYMENT_CARD', '8600 0000 0000 0000'),))
        await db.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('payment_card_owner', ?)", (os.getenv('PAYMENT_CARD_OWNER', 'Ism Familiya'),))
        await db.commit()
    logger.info("✅ DB tayyor.")


# ───────────────── USERS ─────────────────

async def add_or_update_user(user_id: int, username: str, full_name: str):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if await cur.fetchone():
            await db.execute(
                "UPDATE users SET username=?,full_name=?,last_active=? WHERE user_id=?",
                (username, full_name, now, user_id))
        else:
            await db.execute(
                "INSERT INTO users(user_id,username,full_name,joined_at,last_active) VALUES(?,?,?,?,?)",
                (user_id, username, full_name, now, now))
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def is_banned(user_id: int) -> bool:
    u = await get_user(user_id)
    return bool(u and u["is_banned"])


async def is_premium(user_id: int) -> bool:
    u = await get_user(user_id)
    if not u or not u["is_premium"]:
        return False
    if u["premium_until"]:
        return datetime.fromisoformat(u["premium_until"]) > datetime.now()
    return False


async def set_premium(user_id: int, plan: str):
    """Premium berish: monthly=30kun, quarterly=90, yearly=365"""
    days = {"monthly": 30, "quarterly": 90, "yearly": 365}.get(plan, 30)
    u = await get_user(user_id)
    if u and u["is_premium"] and u["premium_until"]:
        try:
            current_until = datetime.fromisoformat(u["premium_until"])
            if current_until > datetime.now():
                until = current_until + timedelta(days=days)
            else:
                until = datetime.now() + timedelta(days=days)
        except Exception:
            until = datetime.now() + timedelta(days=days)
    else:
        until = datetime.now() + timedelta(days=days)

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?",
            (until.isoformat(), user_id))
        await db.commit()
    return until


async def revoke_premium(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_premium=0, premium_until=NULL WHERE user_id=?", (user_id,))
        await db.commit()


async def ban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
        await db.commit()


async def unban_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
        await db.commit()


async def get_all_user_ids() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE is_banned=0")
        return [r[0] for r in await cur.fetchall()]


async def get_stats() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        def q(sql): return db.execute(sql)
        total_users = (await (await q("SELECT COUNT(*) FROM users")).fetchone())[0]
        premium_users = (await (await q("SELECT COUNT(*) FROM users WHERE is_premium=1")).fetchone())[0]
        total_dl = (await (await q("SELECT COUNT(*) FROM downloads WHERE status='success'")).fetchone())[0]
        pending_pay = (await (await q("SELECT COUNT(*) FROM payments WHERE status='pending'")).fetchone())[0]
        yt = (await (await q("SELECT COUNT(*) FROM downloads WHERE platform='youtube'")).fetchone())[0]
        ig = (await (await q("SELECT COUNT(*) FROM downloads WHERE platform='instagram'")).fetchone())[0]
        tt = (await (await q("SELECT COUNT(*) FROM downloads WHERE platform='tiktok'")).fetchone())[0]
    return {
        "total_users": total_users, "premium_users": premium_users,
        "total_downloads": total_dl, "pending_payments": pending_pay,
        "youtube": yt, "instagram": ig, "tiktok": tt,
    }


# ───────────────── DOWNLOADS ─────────────────

async def log_download(user_id: int, platform: str, url: str, quality: str,
                        status: str, file_size: float = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO downloads(user_id,platform,url,quality,status,file_size,created_at) VALUES(?,?,?,?,?,?,?)",
            (user_id, platform, url, quality, status, file_size, datetime.now().isoformat()))
        await db.commit()


# ───────────────── PAYMENTS ─────────────────

async def create_payment(user_id: int, plan: str, amount: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO payments(user_id,plan,amount,status,created_at) VALUES(?,?,?,'pending',?)",
            (user_id, plan, amount, datetime.now().isoformat()))
        await db.commit()
        return cur.lastrowid


async def update_payment_receipt(payment_id: int, file_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET receipt_file=? WHERE id=?", (file_id, payment_id))
        await db.commit()


async def get_pending_payments() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT p.*, u.username, u.full_name
            FROM payments p
            JOIN users u ON p.user_id = u.user_id
            WHERE p.status='pending'
            ORDER BY p.created_at ASC
        """)
        return [dict(r) for r in await cur.fetchall()]


async def get_payment(payment_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM payments WHERE id=?", (payment_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def approve_payment(payment_id: int, admin_id: int) -> dict | None:
    payment = await get_payment(payment_id)
    if not payment:
        return None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status='approved', approved_at=?, approved_by=? WHERE id=?",
            (datetime.now().isoformat(), admin_id, payment_id))
        await db.commit()
    until = await set_premium(payment["user_id"], payment["plan"])
    return {"user_id": payment["user_id"], "plan": payment["plan"], "until": until}


async def reject_payment(payment_id: int, admin_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE payments SET status='rejected', approved_at=?, approved_by=? WHERE id=?",
            (datetime.now().isoformat(), admin_id, payment_id))
        await db.commit()
    p = await get_payment(payment_id)
    return p["user_id"] if p else None


# ───────────────── REQUIRED CHANNELS ─────────────────

async def get_active_channels() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM required_channels WHERE is_active=1")
        return [dict(r) for r in await cur.fetchall()]


async def add_channel(channel_id: str, username: str, title: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO required_channels(channel_id,username,title,is_active) VALUES(?,?,?,1)",
            (channel_id, username, title))
        await db.commit()


async def remove_channel(channel_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE required_channels SET is_active=0 WHERE channel_id=?", (channel_id,))
        await db.commit()


async def get_setting(key: str, default: str = '') -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute('SELECT value FROM settings WHERE key=?', (key,))
        row = await cur.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        await db.commit()
