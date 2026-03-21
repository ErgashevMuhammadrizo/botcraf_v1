import aiosqlite
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
DB_PATH = os.getenv('DB_PATH', 'data/main_bot.db')
DEFAULT_PRICES = {
    'kino_paid_30': 49_000,
    'media_paid_30': 39_000,
    'shop_paid_30': 59_000,
    'trial_days': 10,
    'referral_bonus': 1_000,
    'payment_card': '8600 0000 0000 0000',
    'payment_card_owner': 'Ism Familiya',
}
PRICE_MAP = {1: 49_000, 3: 130_000, 6: 250_000}


async def _ensure_column(db, table: str, column: str, ddl: str):
    async with db.execute(f"PRAGMA table_info({table})") as cur:
        cols = [row[1] async for row in cur]
    if column not in cols:
        await db.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


async def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('PRAGMA journal_mode=WAL')
        await db.execute('PRAGMA synchronous=NORMAL')
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS main_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bots_count INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                trial_bots_used INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS created_bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                owner_username TEXT,
                bot_token TEXT UNIQUE NOT NULL,
                bot_username TEXT,
                bot_type TEXT DEFAULT 'kino',
                channel_id TEXT,
                channel_type TEXT DEFAULT 'public',
                admin_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                process_pid INTEGER,
                plan_code TEXT DEFAULT 'paid_30',
                price_paid INTEGER DEFAULT 0,
                meta_json TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER UNIQUE NOT NULL,
                reward_amount INTEGER DEFAULT 1000,
                rewarded INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rewarded_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                months INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                receipt_file_id TEXT,
                reject_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS main_required_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT DEFAULT '',
                channel_url TEXT DEFAULT '',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS server_nodes (
                code TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                host TEXT NOT NULL,
                max_bots INTEGER DEFAULT 10,
                is_enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS server_waitlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                bot_type TEXT NOT NULL,
                plan_code TEXT DEFAULT 'paid_30',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notified_at TIMESTAMP,
                is_done INTEGER DEFAULT 0
            );
            """
        )
        await _ensure_column(db, 'main_users', 'trial_bots_used', 'trial_bots_used INTEGER DEFAULT 0')
        await _ensure_column(db, 'created_bots', 'bot_type', "bot_type TEXT DEFAULT 'kino'")
        await _ensure_column(db, 'created_bots', 'meta_json', "meta_json TEXT DEFAULT '{}'")
        await _ensure_column(db, 'created_bots', 'server_code', "server_code TEXT DEFAULT 'main'")
        await _ensure_column(db, 'created_bots', 'is_blocked', 'is_blocked INTEGER DEFAULT 0')
        await _ensure_column(db, 'created_bots', 'stopped_at', 'stopped_at TIMESTAMP')
        await _ensure_column(db, 'created_bots', 'blocked_at', 'blocked_at TIMESTAMP')
        for k, v in DEFAULT_PRICES.items():
            await db.execute('INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)', (k, str(v)))
        await db.execute(
            'INSERT OR IGNORE INTO server_nodes(code, label, host, max_bots, is_enabled) VALUES(?,?,?,?,?)',
            ('main', 'Main server', os.getenv('SERVER_MAIN_HOST', '127.0.0.1'), int(os.getenv('SERVER_MAIN_MAX_BOTS', '50')), 1),
        )
        await db.commit()
    logger.info('✅ Main DB ready: %s', DB_PATH)


async def register_user(user_id: int, username: str, full_name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            'INSERT OR IGNORE INTO main_users (user_id, username, full_name) VALUES (?, ?, ?)',
            (user_id, username, full_name),
        )
        await db.execute('UPDATE main_users SET username=?, full_name=? WHERE user_id=?', (username, full_name, user_id))
        await db.commit()
        return cur.rowcount > 0


async def get_setting(key: str, default: int | str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT value FROM settings WHERE key=?', (key,)) as cur:
            row = await cur.fetchone()
    return row[0] if row else default


async def set_setting(key: str, value: int | str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO settings(key, value, updated_at) VALUES(?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP""",
            (key, str(value)),
        )
        await db.commit()


async def get_kino_monthly_price() -> int:
    return int(await get_setting('kino_paid_30', DEFAULT_PRICES['kino_paid_30']))


async def get_media_monthly_price() -> int:
    return int(await get_setting('media_paid_30', DEFAULT_PRICES['media_paid_30']))


async def get_shop_monthly_price() -> int:
    return int(await get_setting('shop_paid_30', DEFAULT_PRICES['shop_paid_30']))


async def get_trial_days() -> int:
    return int(await get_setting('trial_days', DEFAULT_PRICES['trial_days']))


async def get_referral_bonus() -> int:
    return int(await get_setting('referral_bonus', DEFAULT_PRICES['referral_bonus']))


async def get_payment_card() -> str:
    return str(await get_setting('payment_card', DEFAULT_PRICES['payment_card']))


async def get_payment_card_owner() -> str:
    return str(await get_setting('payment_card_owner', DEFAULT_PRICES['payment_card_owner']))


async def get_main_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT * FROM main_users WHERE user_id=?', (user_id,)) as cur:
            return await cur.fetchone()


async def get_balance(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT balance FROM main_users WHERE user_id=?', (user_id,)) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0


async def add_balance(user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE main_users SET balance = balance + ? WHERE user_id=?', (amount, user_id))
        await db.commit()


async def deduct_balance(user_id: int, amount: int) -> bool:
    if amount <= 0:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT balance FROM main_users WHERE user_id=?', (user_id,)) as cur:
            row = await cur.fetchone()
        if not row or int(row[0]) < amount:
            return False
        await db.execute('UPDATE main_users SET balance = balance - ? WHERE user_id=?', (amount, user_id))
        await db.commit()
        return True


async def is_main_admin(user_id: int) -> bool:
    main_admin = int(os.getenv('MAIN_ADMIN_ID', '0'))
    if user_id == main_admin:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT is_admin FROM main_users WHERE user_id=?', (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row and row[0])


async def get_all_main_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT user_id, username, full_name, balance, bots_count FROM main_users ORDER BY joined_at DESC') as cur:
            return await cur.fetchall()


async def can_use_trial(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT trial_bots_used FROM main_users WHERE user_id=?', (user_id,)) as cur:
            row = await cur.fetchone()
            return bool(row is not None and int(row[0] or 0) < 1)


async def mark_trial_used(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE main_users SET trial_bots_used = trial_bots_used + 1 WHERE user_id=?', (user_id,))
        await db.commit()


async def create_referral(referrer_id: int, referred_id: int):
    if referrer_id == referred_id:
        return
    bonus = await get_referral_bonus()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR IGNORE INTO referrals (referrer_id, referred_id, reward_amount) VALUES (?, ?, ?)',
            (referrer_id, referred_id, bonus),
        )
        await db.commit()


async def get_referral_stats(referrer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT COUNT(*), COALESCE(SUM(CASE WHEN rewarded=1 THEN reward_amount ELSE 0 END), 0) FROM referrals WHERE referrer_id=?',
            (referrer_id,),
        ) as cur:
            row = await cur.fetchone()
            return row if row else (0, 0)


async def reward_referral_if_eligible(referred_user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT referrer_id, reward_amount, rewarded FROM referrals WHERE referred_id=?', (referred_user_id,)) as cur:
            ref = await cur.fetchone()
        if not ref or int(ref[2] or 0):
            return 0
        async with db.execute('SELECT bots_count FROM main_users WHERE user_id=?', (referred_user_id,)) as cur:
            user = await cur.fetchone()
        bots_count = int(user[0]) if user else 0
        if bots_count != 1:
            return 0
        await db.execute('UPDATE main_users SET balance = balance + ? WHERE user_id=?', (int(ref[1]), int(ref[0])))
        await db.execute('UPDATE referrals SET rewarded=1, rewarded_at=CURRENT_TIMESTAMP WHERE referred_id=?', (referred_user_id,))
        await db.commit()
        return int(ref[1])


async def save_bot(owner_id, owner_username, token, bot_username, channel_id, channel_type, admin_id, pid=0, days=30, plan_code='paid_30', price_paid=0, bot_type='kino', server_code='main'):
    expires = datetime.now() + timedelta(days=days)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            '''
            INSERT OR REPLACE INTO created_bots
              (owner_id, owner_username, bot_token, bot_username, bot_type, channel_id, channel_type, admin_id, process_pid, expires_at, is_active, is_blocked, plan_code, price_paid, server_code, stopped_at, blocked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?, NULL, NULL)
            ''',
            (owner_id, owner_username, token, bot_username, bot_type, channel_id, channel_type, admin_id, pid, expires, plan_code, price_paid, server_code),
        )
        await db.execute('UPDATE main_users SET bots_count = bots_count + 1 WHERE user_id=?', (owner_id,))
        await db.commit()


async def get_user_bots(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT bot_username, channel_id, channel_type, created_at, is_active, bot_token, expires_at, id, plan_code, price_paid, bot_type, server_code, is_blocked FROM created_bots WHERE owner_id=? ORDER BY created_at DESC',
            (user_id,),
        ) as cur:
            return await cur.fetchall()


async def get_bot_by_id(bot_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT * FROM created_bots WHERE id=?', (bot_id,)) as cur:
            return await cur.fetchone()


async def token_exists(token: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT id, owner_id, bot_username, is_active, bot_type FROM created_bots WHERE bot_token=?', (token,)) as cur:
            return await cur.fetchone()


async def update_bot_process_pid(bot_token: str, pid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE created_bots SET process_pid=?, is_active=1, stopped_at=NULL WHERE bot_token=?', (pid, bot_token))
        await db.commit()


async def set_bot_active_state(bot_id: int, is_active: bool, *, pid: int | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if is_active:
            await db.execute('UPDATE created_bots SET is_active=1, process_pid=?, stopped_at=NULL WHERE id=?', (pid, bot_id))
        else:
            await db.execute('UPDATE created_bots SET is_active=0, process_pid=NULL, stopped_at=CURRENT_TIMESTAMP WHERE id=?', (bot_id,))
        await db.commit()


async def set_bot_blocked_state(bot_id: int, is_blocked: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        if is_blocked:
            await db.execute(
                'UPDATE created_bots SET is_blocked=1, is_active=0, process_pid=NULL, blocked_at=CURRENT_TIMESTAMP, stopped_at=CURRENT_TIMESTAMP WHERE id=?',
                (bot_id,),
            )
        else:
            await db.execute('UPDATE created_bots SET is_blocked=0, blocked_at=NULL WHERE id=?', (bot_id,))
        await db.commit()


async def extend_bot_subscription(bot_id: int, months: int = 1):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT expires_at FROM created_bots WHERE id=?', (bot_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        try:
            old_exp = datetime.fromisoformat(str(row[0])) if row[0] else datetime.now()
        except Exception:
            old_exp = datetime.now()
        base = max(old_exp, datetime.now())
        new_exp = base + timedelta(days=30 * months)
        await db.execute('UPDATE created_bots SET expires_at=?, is_active=1 WHERE id=?', (new_exp, bot_id))
        await db.commit()
        return new_exp


async def deactivate_expired_bots():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, owner_id, bot_username FROM created_bots WHERE is_active=1 AND expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP") as cur:
            expired = await cur.fetchall()
        for bot in expired:
            await db.execute('UPDATE created_bots SET is_active=0, process_pid=NULL, stopped_at=CURRENT_TIMESTAMP WHERE id=?', (bot[0],))
        await db.commit()
    return expired


async def get_expiring_bots(days: int = 3):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT cb.id, cb.owner_id, cb.bot_username, cb.expires_at FROM created_bots cb WHERE cb.is_active=1 AND cb.expires_at BETWEEN CURRENT_TIMESTAMP AND datetime('now', '+' || ? || ' days')",
            (str(days),),
        ) as cur:
            return await cur.fetchall()


async def get_all_active_bots():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT bot_token, bot_type, channel_id, channel_type, admin_id, owner_id FROM created_bots WHERE is_active=1 AND COALESCE(is_blocked, 0)=0') as cur:
            return await cur.fetchall()


async def create_payment(user_id: int, amount: int, months: int, receipt_file_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('INSERT INTO payments (user_id, amount, months, receipt_file_id) VALUES (?, ?, ?, ?)', (user_id, amount, months, receipt_file_id))
        await db.commit()
        return cursor.lastrowid


async def get_pending_payments():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT p.id, p.user_id, p.amount, p.months, p.receipt_file_id, p.created_at, u.full_name, u.username FROM payments p LEFT JOIN main_users u ON u.user_id = p.user_id WHERE p.status='pending' ORDER BY p.created_at ASC") as cur:
            return await cur.fetchall()


async def approve_payment(payment_id: int, user_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payments SET status='approved', processed_at=CURRENT_TIMESTAMP WHERE id=?", (payment_id,))
        await db.execute('UPDATE main_users SET balance = balance + ? WHERE user_id=?', (amount, user_id))
        await db.commit()


async def reject_payment(payment_id: int, reason: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payments SET status='rejected', reject_reason=?, processed_at=CURRENT_TIMESTAMP WHERE id=?", (reason, payment_id))
        await db.commit()


async def get_user_payment_history(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT amount, months, status, created_at, reject_reason FROM payments WHERE user_id=? ORDER BY created_at DESC LIMIT 20', (user_id,)) as cur:
            return await cur.fetchall()


async def add_main_required_channel(channel_id: str, name: str, url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT OR IGNORE INTO main_required_channels (channel_id, channel_name, channel_url) VALUES (?,?,?)', (channel_id, name, url))
        await db.commit()


async def remove_main_required_channel(channel_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('DELETE FROM main_required_channels WHERE channel_id=?', (channel_id,))
        await db.commit()


async def get_main_required_channels():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT channel_id, channel_name, channel_url FROM main_required_channels') as cur:
            return await cur.fetchall()


async def get_all_bots_admin(limit: int = 200):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            '''
            SELECT id, owner_id, owner_username, bot_username, bot_type, is_active, created_at, expires_at, plan_code, price_paid, server_code, COALESCE(is_blocked, 0), process_pid
            FROM created_bots
            ORDER BY created_at DESC
            LIMIT ?
            ''',
            (limit,),
        ) as cur:
            return await cur.fetchall()


async def get_all_payments(limit: int = 200):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            '''
            SELECT p.id, p.user_id, p.amount, p.months, p.status, p.created_at, p.processed_at, p.reject_reason,
                   COALESCE(u.full_name, u.username, '')
            FROM payments p
            LEFT JOIN main_users u ON u.user_id = p.user_id
            ORDER BY p.created_at DESC
            LIMIT ?
            ''',
            (limit,),
        ) as cur:
            return await cur.fetchall()


async def get_stats_summary():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT COUNT(*) FROM main_users') as cur:
            users = (await cur.fetchone())[0]
        async with db.execute('SELECT COUNT(*) FROM created_bots') as cur:
            bots = (await cur.fetchone())[0]
        async with db.execute('SELECT COUNT(*) FROM created_bots WHERE is_active=1') as cur:
            active_bots = (await cur.fetchone())[0]
        async with db.execute('SELECT COUNT(*) FROM created_bots WHERE COALESCE(is_blocked,0)=1') as cur:
            blocked_bots = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'") as cur:
            pending = (await cur.fetchone())[0]
        async with db.execute('SELECT COALESCE(SUM(balance), 0) FROM main_users') as cur:
            balance = (await cur.fetchone())[0]
        async with db.execute('SELECT COALESCE(SUM(max_bots),0) FROM server_nodes WHERE is_enabled=1') as cur:
            total_capacity = (await cur.fetchone())[0]
        async with db.execute('SELECT COUNT(*) FROM created_bots WHERE is_active=1 AND COALESCE(is_blocked,0)=0') as cur:
            used_capacity = (await cur.fetchone())[0]
        async with db.execute('SELECT COUNT(*) FROM server_waitlist WHERE is_done=0') as cur:
            waiting_users = (await cur.fetchone())[0]
    free_capacity = max(int(total_capacity or 0) - int(used_capacity or 0), 0)
    return {
        'users': int(users or 0),
        'bots': int(bots or 0),
        'active_bots': int(active_bots or 0),
        'blocked_bots': int(blocked_bots or 0),
        'pending_payments': int(pending or 0),
        'total_balance': int(balance or 0),
        'total_capacity': int(total_capacity or 0),
        'used_capacity': int(used_capacity or 0),
        'free_capacity': int(free_capacity),
        'waiting_users': int(waiting_users or 0),
    }


async def get_server_nodes():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            '''
            SELECT n.code, n.label, n.host, n.max_bots, n.is_enabled, n.created_at,
                   COALESCE((SELECT COUNT(*) FROM created_bots cb WHERE cb.server_code=n.code AND cb.is_active=1 AND COALESCE(cb.is_blocked,0)=0), 0) AS used_bots
            FROM server_nodes n
            ORDER BY n.created_at ASC
            '''
        ) as cur:
            return await cur.fetchall()


async def add_server_node(code: str, label: str, host: str, max_bots: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT OR REPLACE INTO server_nodes(code, label, host, max_bots, is_enabled) VALUES(?, ?, ?, ?, COALESCE((SELECT is_enabled FROM server_nodes WHERE code=?), 1))',
            (code, label, host, int(max_bots), code),
        )
        await db.commit()


async def set_server_enabled(code: str, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE server_nodes SET is_enabled=? WHERE code=?', (1 if enabled else 0, code))
        await db.commit()


async def choose_available_server() -> str | None:
    nodes = await get_server_nodes()
    enabled = [n for n in nodes if int(n[4] or 0) == 1]
    best_code = None
    best_free = -1
    for code, _label, _host, max_bots, _enabled, _created_at, used_bots in enabled:
        free = int(max_bots or 0) - int(used_bots or 0)
        if free > best_free and free > 0:
            best_code = code
            best_free = free
    return best_code


async def add_waitlist(user_id: int, bot_type: str, plan_code: str = 'paid_30'):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('INSERT INTO server_waitlist(user_id, bot_type, plan_code) VALUES(?,?,?)', (user_id, bot_type, plan_code))
        await db.commit()


async def get_pending_waitlist():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT id, user_id, bot_type, plan_code, created_at FROM server_waitlist WHERE is_done=0 ORDER BY created_at ASC') as cur:
            return await cur.fetchall()


async def mark_waitlist_notified(wait_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE server_waitlist SET is_done=1, notified_at=CURRENT_TIMESTAMP WHERE id=?', (wait_id,))
        await db.commit()


async def get_web_admin_credentials():
    username = str(await get_setting('web_admin_username', os.getenv('WEB_ADMIN_USERNAME', 'admin')))
    password = str(await get_setting('web_admin_password', os.getenv('WEB_ADMIN_PASSWORD', 'admin123')))
    return username, password


async def set_web_admin_credentials(username: str, password: str):
    await set_setting('web_admin_username', username)
    await set_setting('web_admin_password', password)
