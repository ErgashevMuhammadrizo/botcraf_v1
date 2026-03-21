import aiosqlite
import os

BASE_DIR = os.getenv('SHOP_BOT_BASE_DIR', os.getcwd())
os.makedirs(BASE_DIR, exist_ok=True)
DB_PATH = os.getenv('SHOP_DB_PATH', os.path.join(BASE_DIR, 'shop.db'))


async def get_db():
    return await aiosqlite.connect(DB_PATH)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            emoji TEXT DEFAULT '📦',
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            discount_price REAL,
            category_id INTEGER,
            images TEXT DEFAULT '[]',
            sizes TEXT DEFAULT '[]',
            colors TEXT DEFAULT '[]',
            stock INTEGER DEFAULT 0,
            sku TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            address TEXT,
            is_banned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            size TEXT,
            color TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT,
            phone TEXT,
            address TEXT,
            delivery_type TEXT,
            payment_type TEXT,
            comment TEXT,
            promo_code TEXT,
            discount_amount REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'new',
            admin_note TEXT,
            courier_id INTEGER,
            payment_screenshot TEXT,
            payment_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            size TEXT,
            color TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS promo_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            discount_type TEXT NOT NULL,
            discount_value REAL NOT NULL,
            min_order_amount REAL DEFAULT 0,
            max_uses INTEGER DEFAULT 0,
            used_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS promo_uses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            promo_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            order_id INTEGER,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY,
            username TEXT,
            role TEXT DEFAULT 'operator',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS couriers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            telegram_id INTEGER,
            is_active INTEGER DEFAULT 1
        );

        INSERT OR IGNORE INTO settings (key, value) VALUES
            ('shop_name', 'Online Do''kon'),
            ('welcome_text', 'Xush kelibsiz! 🎉\nBizning do''konimizga xush kelibsiz.'),
            ('shop_phone', '+998901234567'),
            ('shop_address', 'Toshkent sh.'),
            ('shop_hours', 'Du-Sha: 9:00-18:00'),
            ('delivery_price', '15000'),
            ('free_delivery_from', '200000'),
            ('currency', 'so''m'),
            ('min_order', '50000'),
            ('orders_open', '1'),
            ('card_numbers', '8600 1234 5678 9012'),
            ('shop_about', 'Biz sifatli mahsulotlar yetkazib beramiz.'),
            ('delivery_terms', 'Yetkazib berish 1-3 ish kuni ichida amalga oshiriladi.'),
            ('payment_terms', 'Naqd yoki karta orqali to''lov qabul qilinadi.'),
            ('return_policy', 'Mahsulot 14 kun ichida qaytarilishi mumkin.');
        """)
        await db.commit()


# ─── SETTINGS ────────────────────────────────────────────────────────────────

async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else ""


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
        await db.commit()


async def get_all_settings() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key, value FROM settings") as cur:
            rows = await cur.fetchall()
            return {r[0]: r[1] for r in rows}


# ─── USERS ────────────────────────────────────────────────────────────────────

async def upsert_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (id, username, full_name, last_active)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                last_active=CURRENT_TIMESTAMP
        """, (user_id, username, full_name))
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_all_users() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY created_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def ban_user(user_id: int, ban: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_banned=? WHERE id=?", (1 if ban else 0, user_id))
        await db.commit()


# ─── CATEGORIES ──────────────────────────────────────────────────────────────

async def get_categories(active_only=True) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT * FROM categories"
        if active_only:
            q += " WHERE is_active=1"
        q += " ORDER BY sort_order, id"
        async with db.execute(q) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def add_category(name: str, emoji: str = "📦") -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO categories (name, emoji) VALUES (?,?)", (name, emoji))
        await db.commit()
        return cur.lastrowid


async def update_category(cat_id: int, name: str, emoji: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE categories SET name=?, emoji=? WHERE id=?", (name, emoji, cat_id))
        await db.commit()


async def delete_category(cat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        await db.commit()


async def get_category(cat_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM categories WHERE id=?", (cat_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


# ─── PRODUCTS ────────────────────────────────────────────────────────────────

async def get_products(category_id: int = None, active_only=True, search: str = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conditions = []
        params = []
        if active_only:
            conditions.append("p.is_active=1")
        if category_id:
            conditions.append("p.category_id=?")
            params.append(category_id)
        if search:
            conditions.append("p.name LIKE ?")
            params.append(f"%{search}%")
        q = "SELECT p.*, c.name as cat_name FROM products p LEFT JOIN categories c ON p.category_id=c.id"
        if conditions:
            q += " WHERE " + " AND ".join(conditions)
        q += " ORDER BY p.id DESC"
        async with db.execute(q, params) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_product(product_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT p.*, c.name as cat_name FROM products p LEFT JOIN categories c ON p.category_id=c.id WHERE p.id=?",
            (product_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def add_product(data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO products (name, description, price, discount_price, category_id,
                images, sizes, colors, stock, sku, is_active)
            VALUES (:name, :description, :price, :discount_price, :category_id,
                :images, :sizes, :colors, :stock, :sku, :is_active)
        """, data)
        await db.commit()
        return cur.lastrowid


async def update_product(product_id: int, data: dict):
    fields = ", ".join(f"{k}=:{k}" for k in data)
    data["id"] = product_id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE products SET {fields} WHERE id=:id", data)
        await db.commit()


async def delete_product(product_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM products WHERE id=?", (product_id,))
        await db.commit()


# ─── CART ─────────────────────────────────────────────────────────────────────

async def get_cart(user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT c.*, p.name, p.price, p.discount_price, p.images, p.stock
            FROM cart c JOIN products p ON c.product_id=p.id
            WHERE c.user_id=?
        """, (user_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def add_to_cart(user_id: int, product_id: int, quantity: int = 1, size: str = None, color: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await db.execute(
            "SELECT id, quantity FROM cart WHERE user_id=? AND product_id=? AND size IS ? AND color IS ?",
            (user_id, product_id, size, color)
        )
        row = await existing.fetchone()
        if row:
            await db.execute("UPDATE cart SET quantity=quantity+? WHERE id=?", (quantity, row[0]))
        else:
            await db.execute(
                "INSERT INTO cart (user_id, product_id, quantity, size, color) VALUES (?,?,?,?,?)",
                (user_id, product_id, quantity, size, color)
            )
        await db.commit()


async def update_cart_quantity(cart_id: int, quantity: int):
    async with aiosqlite.connect(DB_PATH) as db:
        if quantity <= 0:
            await db.execute("DELETE FROM cart WHERE id=?", (cart_id,))
        else:
            await db.execute("UPDATE cart SET quantity=? WHERE id=?", (quantity, cart_id))
        await db.commit()


async def remove_from_cart(cart_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart WHERE id=?", (cart_id,))
        await db.commit()


async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart WHERE user_id=?", (user_id,))
        await db.commit()


# ─── FAVORITES ───────────────────────────────────────────────────────────────

async def get_favorites(user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT f.*, p.name, p.price, p.discount_price, p.images, p.is_active
            FROM favorites f JOIN products p ON f.product_id=p.id
            WHERE f.user_id=?
        """, (user_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def toggle_favorite(user_id: int, product_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM favorites WHERE user_id=? AND product_id=?", (user_id, product_id)
        ) as cur:
            row = await cur.fetchone()
        if row:
            await db.execute("DELETE FROM favorites WHERE id=?", (row[0],))
            await db.commit()
            return False
        else:
            await db.execute("INSERT INTO favorites (user_id, product_id) VALUES (?,?)", (user_id, product_id))
            await db.commit()
            return True


async def is_favorite(user_id: int, product_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM favorites WHERE user_id=? AND product_id=?", (user_id, product_id)
        ) as cur:
            return bool(await cur.fetchone())


# ─── ORDERS ──────────────────────────────────────────────────────────────────

async def create_order(data: dict, items: list) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO orders (user_id, full_name, phone, address, delivery_type,
                payment_type, comment, promo_code, discount_amount, total_amount)
            VALUES (:user_id, :full_name, :phone, :address, :delivery_type,
                :payment_type, :comment, :promo_code, :discount_amount, :total_amount)
        """, data)
        order_id = cur.lastrowid
        for item in items:
            item["order_id"] = order_id
            await db.execute("""
                INSERT INTO order_items (order_id, product_id, product_name, quantity, price, size, color)
                VALUES (:order_id, :product_id, :product_name, :quantity, :price, :size, :color)
            """, item)
        await db.commit()
        return order_id


async def get_orders(user_id: int = None, status: str = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        conditions = []
        params = []
        if user_id:
            conditions.append("o.user_id=?")
            params.append(user_id)
        if status:
            conditions.append("o.status=?")
            params.append(status)
        q = """
            SELECT o.*, u.username, u.full_name as user_name
            FROM orders o LEFT JOIN users u ON o.user_id=u.id
        """
        if conditions:
            q += " WHERE " + " AND ".join(conditions)
        q += " ORDER BY o.created_at DESC"
        async with db.execute(q, params) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_order(order_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT o.*, u.username, u.full_name as user_name
            FROM orders o LEFT JOIN users u ON o.user_id=u.id
            WHERE o.id=?
        """, (order_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_order_items(order_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def update_order_status(order_id: int, status: str, admin_note: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if admin_note:
            await db.execute(
                "UPDATE orders SET status=?, admin_note=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (status, admin_note, order_id)
            )
        else:
            await db.execute(
                "UPDATE orders SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (status, order_id)
            )
        await db.commit()


async def update_payment_screenshot(order_id: int, file_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET payment_screenshot=?, payment_status='submitted' WHERE id=?",
            (file_id, order_id)
        )
        await db.commit()


async def confirm_payment(order_id: int, confirmed: bool):
    status = "confirmed" if confirmed else "pending"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE orders SET payment_status=? WHERE id=?",
            (status, order_id)
        )
        await db.commit()


# ─── PROMO CODES ─────────────────────────────────────────────────────────────

async def get_promo(code: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM promo_codes WHERE code=? AND is_active=1", (code.upper(),)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def use_promo(promo_id: int, user_id: int, order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE id=?", (promo_id,))
        await db.execute(
            "INSERT INTO promo_uses (promo_id, user_id, order_id) VALUES (?,?,?)",
            (promo_id, user_id, order_id)
        )
        await db.commit()


async def add_promo(data: dict) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""
            INSERT INTO promo_codes (code, discount_type, discount_value, min_order_amount, max_uses, expires_at)
            VALUES (:code, :discount_type, :discount_value, :min_order_amount, :max_uses, :expires_at)
        """, data)
        await db.commit()
        return cur.lastrowid


async def get_all_promos() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promo_codes ORDER BY created_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]


# ─── STATISTICS ──────────────────────────────────────────────────────────────

async def get_statistics() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            stats["total_users"] = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders") as cur:
            stats["total_orders"] = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE date(created_at)=date('now')"
        ) as cur:
            stats["today_orders"] = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE date(created_at)>=date('now','-7 days')"
        ) as cur:
            stats["week_orders"] = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE status='closed'"
        ) as cur:
            stats["total_revenue"] = (await cur.fetchone())[0]
        async with db.execute(
            "SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE status='closed' AND date(created_at)=date('now')"
        ) as cur:
            stats["today_revenue"] = (await cur.fetchone())[0]
        async with db.execute("""
            SELECT p.name, SUM(oi.quantity) as sold
            FROM order_items oi JOIN products p ON oi.product_id=p.id
            GROUP BY oi.product_id ORDER BY sold DESC LIMIT 5
        """) as cur:
            stats["top_products"] = await cur.fetchall()
        return stats


# ─── ADMINS ──────────────────────────────────────────────────────────────────

async def get_admins() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM admins") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def add_admin(user_id: int, username: str, role: str = "operator"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO admins (id, username, role) VALUES (?,?,?)",
            (user_id, username, role)
        )
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE id=?", (user_id,))
        await db.commit()
