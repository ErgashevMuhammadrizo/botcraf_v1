# ============================================================
# KINO BOT — MA'LUMOTLAR BAZASI (tezlashtirilgan WAL rejim)
# ============================================================

import aiosqlite
import logging
import os

logger = logging.getLogger(__name__)

_db_path = None


def get_db_path():
    global _db_path
    if _db_path is None:
        token = os.getenv("KINO_BOT_TOKEN", "default")
        short = token.split(":")[0]
        os.makedirs("data", exist_ok=True)
        _db_path = f"data/kino_{short}.db"
    return _db_path


async def init_kino_db():
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        # WAL rejim — tezroq yozish/o'qish
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA cache_size=10000")
        await db.execute("PRAGMA temp_store=MEMORY")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                title          TEXT NOT NULL,
                description    TEXT DEFAULT '',
                year           INTEGER DEFAULT 0,
                genre          TEXT DEFAULT '',
                file_id        TEXT NOT NULL,
                archive_chat_id TEXT DEFAULT '',
                archive_msg_id INTEGER DEFAULT 0,
                channel_msg_id INTEGER DEFAULT 0,
                kod            TEXT UNIQUE NOT NULL,
                poster_file_id TEXT DEFAULT '',
                added_by       INTEGER,
                added_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                views          INTEGER DEFAULT 0,
                is_active      INTEGER DEFAULT 1
            )
        """)

        # Seriallar — bitta serial uchun bitta kod (title+season)
        # Har bir serial o'z MASTER kodiga ega, qismlar shu serialga birikadi
        await db.execute("""
            CREATE TABLE IF NOT EXISTS serials (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                title          TEXT NOT NULL,
                season         INTEGER DEFAULT 1,
                episode        INTEGER DEFAULT 1,
                description    TEXT DEFAULT '',
                file_id        TEXT NOT NULL,
                archive_chat_id TEXT DEFAULT '',
                archive_msg_id INTEGER DEFAULT 0,
                channel_msg_id INTEGER DEFAULT 0,
                kod            TEXT UNIQUE NOT NULL,
                poster_file_id TEXT DEFAULT '',
                added_by       INTEGER,
                added_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                views          INTEGER DEFAULT 0,
                is_active      INTEGER DEFAULT 1
            )
        """)

        # Serial master — har serial uchun bitta kanal posti (title+season)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS serial_masters (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                title          TEXT NOT NULL,
                season         INTEGER DEFAULT 1,
                master_kod     TEXT UNIQUE NOT NULL,
                description    TEXT DEFAULT '',
                poster_file_id TEXT DEFAULT '',
                channel_msg_id INTEGER DEFAULT 0,
                added_by       INTEGER,
                added_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active      INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER UNIQUE NOT NULL,
                username    TEXT DEFAULT '',
                full_name   TEXT DEFAULT '',
                joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned   INTEGER DEFAULT 0,
                is_admin    INTEGER DEFAULT 0,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS required_channels (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id   TEXT UNIQUE NOT NULL,
                channel_name TEXT DEFAULT '',
                channel_url  TEXT DEFAULT '',
                channel_type TEXT DEFAULT 'public'
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS social_links (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT NOT NULL,
                url   TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER UNIQUE NOT NULL,
                username TEXT DEFAULT '',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        await db.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('payment_card', ?)", (os.getenv('PAYMENT_CARD', '8600 0000 0000 0000'),))
        await db.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('payment_card_owner', ?)", (os.getenv('PAYMENT_CARD_OWNER', 'Ism Familiya'),))
        await db.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('admin_username', ?)", (os.getenv('KINO_ADMIN_USERNAME', '@admin'),))
        await db.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('admin_contact_text', ?)", (os.getenv('KINO_ADMIN_CONTACT_TEXT', "Muammo yoki savol bo'lsa admin ga yozing."),))

        # Indekslar — qidiruv tezligi uchun
        await db.execute("CREATE INDEX IF NOT EXISTS idx_movies_kod ON movies(kod)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_movies_title ON movies(title)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_serials_kod ON serials(kod)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_serials_title ON serials(title)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_serial_masters_kod ON serial_masters(master_kod)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_serial_masters_title ON serial_masters(title)")

        for table, ddl in [('movies', 'archive_chat_id TEXT DEFAULT ""'), ('movies', 'archive_msg_id INTEGER DEFAULT 0'), ('serials', 'archive_chat_id TEXT DEFAULT ""'), ('serials', 'archive_msg_id INTEGER DEFAULT 0')]:
            col = ddl.split()[0]
            async with db.execute(f"PRAGMA table_info({table})") as cur:
                cols = [row[1] for row in await cur.fetchall()]
            if col not in cols:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
        await db.commit()
    logger.info("✅ Kino bot bazasi tayyor: %s", db_path)

    admin_id = int(os.getenv("KINO_ADMIN_ID", "0"))
    if admin_id:
        await add_admin(admin_id, "owner")


# ════════════════════════════════════════════════════════════
# FOYDALANUVCHILAR
# ════════════════════════════════════════════════════════════
async def register_kino_user(user_id, username, full_name):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                last_active=CURRENT_TIMESTAMP
        """, (user_id, username, full_name))
        await db.commit()


async def get_user(user_id):
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()


async def ban_user(user_id):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
        await db.commit()


async def unban_user(user_id):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute(
            "SELECT user_id, username, full_name, joined_at, is_banned FROM users ORDER BY joined_at DESC"
        ) as cur:
            return await cur.fetchall()


# ════════════════════════════════════════════════════════════
# ADMINLAR
# ════════════════════════════════════════════════════════════
async def add_admin(user_id, username=""):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id, username) VALUES (?,?)", (user_id, username))
        await db.execute("UPDATE users SET is_admin=1 WHERE user_id=?", (user_id,))
        await db.commit()


async def remove_admin(user_id):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.execute("UPDATE users SET is_admin=0 WHERE user_id=?", (user_id,))
        await db.commit()


async def is_admin(user_id):
    owner = int(os.getenv("KINO_ADMIN_ID", "0"))
    if user_id == owner:
        return True
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("SELECT id FROM admins WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None


async def get_all_admins():
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("SELECT user_id, username, added_at FROM admins") as cur:
            return await cur.fetchall()


# ════════════════════════════════════════════════════════════
# KINOLAR
# ════════════════════════════════════════════════════════════
async def add_movie(title, description, year, genre,
                    file_id, channel_msg_id, kod, added_by, poster_file_id="", archive_chat_id="", archive_msg_id=0):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("""
            INSERT INTO movies (title, description, year, genre,
                                file_id, archive_chat_id, archive_msg_id, channel_msg_id, kod, added_by, poster_file_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (title, description, year, genre, file_id, archive_chat_id, archive_msg_id, channel_msg_id, kod, added_by, poster_file_id))
        await db.commit()


async def get_movie_by_kod(kod):
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("SELECT * FROM movies WHERE kod=? AND is_active=1", (kod,)) as cur:
            return await cur.fetchone()


async def search_movies(query):
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("""
            SELECT id, title, year, genre, kod, views
            FROM movies WHERE title LIKE ? AND is_active=1
            ORDER BY views DESC LIMIT 10
        """, (f"%{query}%",)) as cur:
            return await cur.fetchall()


async def delete_movie(kod):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("UPDATE movies SET is_active=0 WHERE kod=?", (kod,))
        await db.commit()


async def increment_movie_views(kod):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("UPDATE movies SET views=views+1 WHERE kod=?", (kod,))
        await db.commit()


async def get_all_movies(limit=50):
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("""
            SELECT id, title, year, genre, kod, views, added_at, channel_msg_id
            FROM movies WHERE is_active=1 ORDER BY added_at DESC LIMIT ?
        """, (limit,)) as cur:
            return await cur.fetchall()


# ════════════════════════════════════════════════════════════
# SERIAL MASTER — bitta serial uchun bitta kanal posti
# ════════════════════════════════════════════════════════════
async def get_or_create_serial_master(title: str, season: int, added_by: int,
                                       description: str = "", poster_file_id: str = "") -> tuple:
    """Serial master olish yoki yaratish — (master_kod, is_new)"""
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute(
            "SELECT master_kod, id FROM serial_masters WHERE title=? AND season=? AND is_active=1",
            (title, season)
        ) as cur:
            existing = await cur.fetchone()

        if existing:
            return existing[0], False

        # Yangi master yaratish
        import random, string
        kod = "".join(random.choices(string.digits, k=4))
        while True:
            async with db.execute("SELECT id FROM serial_masters WHERE master_kod=?", (kod,)) as cur:
                if not await cur.fetchone():
                    break
            kod = "".join(random.choices(string.digits, k=4))

        await db.execute("""
            INSERT INTO serial_masters (title, season, master_kod, description, poster_file_id, added_by)
            VALUES (?,?,?,?,?,?)
        """, (title, season, kod, description, poster_file_id, added_by))
        await db.commit()
        return kod, True


async def get_serial_master_by_kod(master_kod: str):
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute(
            "SELECT * FROM serial_masters WHERE master_kod=? AND is_active=1", (master_kod,)
        ) as cur:
            return await cur.fetchone()


async def update_serial_master_channel(master_kod: str, channel_msg_id: int):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "UPDATE serial_masters SET channel_msg_id=? WHERE master_kod=?",
            (channel_msg_id, master_kod)
        )
        await db.commit()


async def get_serial_episodes(title: str, season: int):
    """Bitta serial barcha qismlarini olish — tugmalar uchun"""
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("""
            SELECT kod, episode FROM serials
            WHERE title=? AND season=? AND is_active=1
            ORDER BY episode ASC
        """, (title, season)) as cur:
            return await cur.fetchall()


async def get_serial_seasons(title: str):
    """Serial barcha mavsumlari"""
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("""
            SELECT DISTINCT season FROM serial_masters
            WHERE title=? AND is_active=1 ORDER BY season
        """, (title,)) as cur:
            return [r[0] for r in await cur.fetchall()]


# ════════════════════════════════════════════════════════════
# SERIALLAR — qismlar
# ════════════════════════════════════════════════════════════
async def add_serial(title, season, episode, description,
                     file_id, channel_msg_id, kod, added_by, poster_file_id="", archive_chat_id="", archive_msg_id=0):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("""
            INSERT INTO serials (title, season, episode, description,
                                 file_id, archive_chat_id, archive_msg_id, channel_msg_id, kod, added_by, poster_file_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (title, season, episode, description, file_id, archive_chat_id, archive_msg_id, channel_msg_id, kod, added_by, poster_file_id))
        await db.commit()


async def get_serial_by_kod(kod):
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("SELECT * FROM serials WHERE kod=? AND is_active=1", (kod,)) as cur:
            return await cur.fetchone()


async def search_serials(query):
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("""
            SELECT DISTINCT title, season
            FROM serial_masters WHERE title LIKE ? AND is_active=1
            ORDER BY title, season LIMIT 10
        """, (f"%{query}%",)) as cur:
            return await cur.fetchall()


async def search_serial_masters(query):
    """Serial masterlarni qidirish"""
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("""
            SELECT id, title, season, master_kod
            FROM serial_masters WHERE title LIKE ? AND is_active=1
            ORDER BY title, season LIMIT 10
        """, (f"%{query}%",)) as cur:
            return await cur.fetchall()


async def delete_serial(kod):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("UPDATE serials SET is_active=0 WHERE kod=?", (kod,))
        await db.commit()


async def increment_serial_views(kod):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("UPDATE serials SET views=views+1 WHERE kod=?", (kod,))
        await db.commit()


# ════════════════════════════════════════════════════════════
# MAJBURIY OBUNA
# ════════════════════════════════════════════════════════════
async def add_required_channel(channel_id, name, url, ctype="public"):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("""
            INSERT OR IGNORE INTO required_channels (channel_id, channel_name, channel_url, channel_type)
            VALUES (?,?,?,?)
        """, (channel_id, name, url, ctype))
        await db.commit()


async def remove_required_channel(channel_id):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM required_channels WHERE channel_id=?", (channel_id,))
        await db.commit()


async def get_required_channels():
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute(
            "SELECT channel_id, channel_name, channel_url, channel_type FROM required_channels"
        ) as cur:
            return await cur.fetchall()


# ════════════════════════════════════════════════════════════
# IJTIMOIY TARMOQLAR
# ════════════════════════════════════════════════════════════
async def add_social(name, url):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("INSERT INTO social_links (name, url) VALUES (?,?)", (name, url))
        await db.commit()


async def get_socials():
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("SELECT id, name, url FROM social_links") as cur:
            return await cur.fetchall()


async def remove_social(social_id):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute("DELETE FROM social_links WHERE id=?", (social_id,))
        await db.commit()

# ════════════════════════════════════════════════════════════
# SOZLAMALAR
# ════════════════════════════════════════════════════════════
async def get_setting(key: str, default: str = ''):
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(get_db_path()) as db:
        await db.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value))
        )
        await db.commit()


async def get_all_settings():
    async with aiosqlite.connect(get_db_path()) as db:
        async with db.execute("SELECT key, value FROM settings") as cur:
            rows = await cur.fetchall()
            return {k: v for k, v in rows}
