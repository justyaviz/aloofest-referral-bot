from __future__ import annotations

import time
import aiosqlite
from config import DB_PATH, REGISTRATION_BONUS, REFERRAL_BONUS


DEFAULT_PRIZES = [
    ("🥇 1-o‘rin", "Tecno Spark Go 30C", "TOP reytingdagi 1-o‘rin uchun sovg‘a"),
    ("🥈 2-o‘rin", "Mini pech Artel", "TOP reytingdagi 2-o‘rin uchun sovg‘a"),
    ("🥉 3-o‘rin", "Ryugzak", "TOP reytingdagi 3-o‘rin uchun sovg‘a"),
    ("🎲 Random sovg‘a 1", "AirPods Max Copy", "Random g‘olibi uchun sovg‘a"),
    ("🎲 Random sovg‘a 2", "AirPods Max Copy", "Random g‘olibi uchun sovg‘a"),
    ("🎲 Random sovg‘a 3", "AirPods Max Copy", "Random g‘olibi uchun sovg‘a"),
]

PROMO_CODES = {
    "2101": "ANGREN",
    "2102": "OHANGARON",
    "2103": "OLMALIQ",
    "2104": "QIBRAY",
    "2105": "CHIRCHIQ",
    "2106": "GAZALKENT",
    "2107": "PISKENT",
    "2108": "CHINOZ",
    "2109": "OQQO‘RG‘ON",
    "2110": "PARKENT",
    "3101": "SHO‘RCHI",
    "3102": "JARQO‘RG‘ON",
    "3103": "SHEROBOD",
    "4101": "GULISTON",
}


class Database:
    async def init(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                tg_name TEXT,
                full_name TEXT,
                instagram TEXT,
                phone TEXT,
                region TEXT,
                district TEXT,
                fest_id TEXT UNIQUE,
                referrer_id INTEGER,
                promo_code TEXT,
                promo_branch TEXT,
                registered INTEGER DEFAULT 0,
                phone_verified INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0,
                diamonds INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                created_at INTEGER,
                registered_at INTEGER
            )
            """)

            # eski bazalarda column bo'lmasa qo'shib ketadi
            for sql in [
                "ALTER TABLE users ADD COLUMN phone TEXT",
                "ALTER TABLE users ADD COLUMN phone_verified INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN promo_code TEXT",
                "ALTER TABLE users ADD COLUMN promo_branch TEXT",
                "ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0",
            ]:
                try:
                    await db.execute(sql)
                except Exception:
                    pass

            await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                invited_user_id INTEGER PRIMARY KEY,
                inviter_id INTEGER,
                created_at INTEGER
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS prizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                place_name TEXT,
                title TEXT,
                description TEXT,
                created_at INTEGER
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                full_name TEXT,
                message_text TEXT,
                created_at INTEGER
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS pending_support_replies (
                admin_id INTEGER PRIMARY KEY,
                target_user_id INTEGER
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS random_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winner_user_id INTEGER,
                winner_name TEXT,
                telegram_id INTEGER,
                instagram TEXT,
                fest_id TEXT,
                diamonds INTEGER,
                start_date TEXT,
                end_date TEXT,
                created_at INTEGER,
                confirmed INTEGER DEFAULT 0
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                body TEXT,
                created_at INTEGER
            )
            """)

            await db.commit()

            cur = await db.execute("SELECT COUNT(*) FROM prizes")
            count = (await cur.fetchone())[0]
            if count == 0:
                now = int(time.time())
                await db.executemany(
                    "INSERT INTO prizes (place_name, title, description, created_at) VALUES (?, ?, ?, ?)",
                    [(a, b, c, now) for a, b, c in DEFAULT_PRIZES]
                )
                await db.commit()

    async def add_user(self, user_id: int, username: str | None, tg_name: str | None):
        now = int(time.time())
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            if not row:
                await db.execute("""
                    INSERT INTO users (user_id, username, tg_name, created_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, username, tg_name, now))
            else:
                await db.execute("""
                    UPDATE users SET username = ?, tg_name = ?
                    WHERE user_id = ?
                """, (username, tg_name, user_id))
            await db.commit()

    async def set_referrer_if_empty(self, user_id: int, referrer_id: int):
        if user_id == referrer_id:
            return
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT referrer_id, registered FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cur.fetchone()
            if row and row[0] is None and row[1] == 0:
                await db.execute(
                    "UPDATE users SET referrer_id = ? WHERE user_id = ?",
                    (referrer_id, user_id)
                )
                await db.commit()

    async def get_user(self, user_id: int):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return await cur.fetchone()

    async def get_user_by_fest(self, fest_id: str):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE fest_id = ?", (fest_id,))
            return await cur.fetchone()

    async def next_fest_id(self) -> str:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*) FROM users WHERE registered = 1")
            count = (await cur.fetchone())[0] + 1
            return f"FEST-{count:03d}"

    async def register_user(
        self,
        user_id: int,
        full_name: str,
        instagram: str,
        region: str,
        district: str,
        promo_code: str | None = None,
    ):
        now = int(time.time())
        fest_id = await self.next_fest_id()

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = await cur.fetchone()
            if not user:
                return False, "Foydalanuvchi topilmadi", None

            first_registration = user["registered"] == 0

            promo_branch = None
            promo_bonus = 0
            if promo_code:
                promo_branch = PROMO_CODES.get(promo_code)
                if not promo_branch:
                    return False, "Promokod noto‘g‘ri", None
                promo_bonus = 5

            await db.execute("""
                UPDATE users
                SET full_name = ?, instagram = ?, region = ?, district = ?,
                    fest_id = COALESCE(fest_id, ?),
                    promo_code = COALESCE(promo_code, ?),
                    promo_branch = COALESCE(promo_branch, ?),
                    registered = 1,
                    registered_at = COALESCE(registered_at, ?)
                WHERE user_id = ?
            """, (
                full_name, instagram, region, district,
                fest_id, promo_code, promo_branch, now, user_id
            ))

            if first_registration:
                await db.execute("""
                    UPDATE users
                    SET diamonds = diamonds + ?
                    WHERE user_id = ?
                """, (REGISTRATION_BONUS + promo_bonus, user_id))

                if user["referrer_id"]:
                    await db.execute("""
                        INSERT OR IGNORE INTO referrals (invited_user_id, inviter_id, created_at)
                        VALUES (?, ?, ?)
                    """, (user_id, user["referrer_id"], now))

                    cur2 = await db.execute(
                        "SELECT COUNT(*) FROM referrals WHERE invited_user_id = ?",
                        (user_id,)
                    )
                    inserted = (await cur2.fetchone())[0]
                    if inserted:
                        await db.execute("""
                            UPDATE users
                            SET diamonds = diamonds + ?, referral_count = referral_count + 1
                            WHERE user_id = ?
                        """, (REFERRAL_BONUS, user["referrer_id"]))

            await db.commit()
            return True, fest_id, promo_branch

    async def save_phone(self, user_id: int, phone: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE users
                SET phone = ?, phone_verified = 1
                WHERE user_id = ?
            """, (phone, user_id))
            await db.commit()

    async def seed_test_random_users(self):
        test_users = [
            (8124320409, 25, 5),
            (7803701344, 25, 5),
        ]
        async with aiosqlite.connect(DB_PATH) as db:
            for user_id, diamonds, refs in test_users:
                await db.execute("""
                    UPDATE users
                    SET diamonds = ?, referral_count = ?, registered = 1
                    WHERE user_id = ?
                """, (diamonds, refs, user_id))

            await db.execute("""
                UPDATE users
                SET diamonds = 25, referral_count = 5, registered = 1
                WHERE fest_id = 'FEST-002'
            """)
            await db.commit()

    async def top_users(self, limit: int = 10):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("""
                SELECT * FROM users
                WHERE registered = 1 AND banned = 0
                ORDER BY diamonds DESC, referral_count DESC, registered_at ASC
                LIMIT ?
            """, (limit,))
            return await cur.fetchall()

    async def get_rank(self, user_id: int):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT diamonds FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            if not row:
                return None
            diamonds = row["diamonds"]

            cur = await db.execute(
                "SELECT COUNT(*) + 1 FROM users WHERE diamonds > ? AND registered = 1 AND banned = 0",
                (diamonds,)
            )
            rank = (await cur.fetchone())[0]

            cur = await db.execute("SELECT COUNT(*) FROM users WHERE registered = 1 AND banned = 0")
            total = (await cur.fetchone())[0]

            return {"rank": rank, "total": total, "diamonds": diamonds}

    async def get_prizes(self):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM prizes ORDER BY id ASC")
            return await cur.fetchall()

    async def update_prize(self, prize_id: int, place_name: str, title: str, description: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE prizes
                SET place_name = ?, title = ?, description = ?
                WHERE id = ?
            """, (place_name, title, description, prize_id))
            await db.commit()

    async def save_support_message(self, user_id: int, username: str | None, full_name: str | None, message_text: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO support_messages (user_id, username, full_name, message_text, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, full_name, message_text, int(time.time())))
            await db.commit()

    async def set_pending_reply(self, admin_id: int, target_user_id: int):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO pending_support_replies (admin_id, target_user_id)
                VALUES (?, ?)
                ON CONFLICT(admin_id) DO UPDATE SET target_user_id=excluded.target_user_id
            """, (admin_id, target_user_id))
            await db.commit()

    async def get_pending_reply(self, admin_id: int):
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("""
                SELECT target_user_id FROM pending_support_replies WHERE admin_id = ?
            """, (admin_id,))
            row = await cur.fetchone()
            return row[0] if row else None

    async def clear_pending_reply(self, admin_id: int):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM pending_support_replies WHERE admin_id = ?", (admin_id,))
            await db.commit()

    async def get_recent_users(self, limit: int = 50):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("""
                SELECT * FROM users ORDER BY created_at DESC LIMIT ?
            """, (limit,))
            return await cur.fetchall()

    async def get_stats(self):
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cur.fetchone())[0]

            cur = await db.execute("SELECT COUNT(*) FROM users WHERE registered = 1")
            registered = (await cur.fetchone())[0]

            cur = await db.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
            banned = (await cur.fetchone())[0]

            cur = await db.execute("SELECT COALESCE(SUM(diamonds),0) FROM users")
            total_diamonds = (await cur.fetchone())[0]

            cur = await db.execute("SELECT COUNT(*) FROM users WHERE referral_count >= 3 AND banned = 0 AND registered = 1")
            random_ready = (await cur.fetchone())[0]

            return {
                "total_users": total_users,
                "registered": registered,
                "banned": banned,
                "diamonds": total_diamonds,
                "random_ready": random_ready,
            }

    async def get_region_stats(self):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("""
                SELECT region, COUNT(*) as total, COALESCE(SUM(diamonds),0) as diamonds
                FROM users
                WHERE registered = 1
                GROUP BY region
                ORDER BY total DESC
            """)
            return await cur.fetchall()

    async def get_promo_stats(self):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("""
                SELECT promo_branch, promo_code, COUNT(*) as total
                FROM users
                WHERE promo_code IS NOT NULL AND promo_branch IS NOT NULL
                GROUP BY promo_branch, promo_code
                ORDER BY total DESC, promo_branch ASC
            """)
            return await cur.fetchall()

    async def ban_user(self, user_id: int):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def unban_user(self, user_id: int):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def search_users(self, query: str, limit: int = 10):
        like = f"%{query}%"
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if query.isdigit():
                cur = await db.execute("SELECT * FROM users WHERE user_id = ? LIMIT ?", (int(query), limit))
            else:
                cur = await db.execute("""
                    SELECT * FROM users
                    WHERE username LIKE ? OR full_name LIKE ? OR fest_id LIKE ? OR instagram LIKE ? OR promo_code LIKE ? OR promo_branch LIKE ?
                    LIMIT ?
                """, (like, like, like, like, like, like, limit))
            return await cur.fetchall()

    async def all_users(self):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users ORDER BY created_at ASC")
            return await cur.fetchall()

    async def save_random_history(
        self,
        winner_user_id: int,
        winner_name: str,
        telegram_id: int,
        instagram: str,
        fest_id: str,
        diamonds: int,
        start_date: str,
        end_date: str,
    ):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO random_history (
                    winner_user_id, winner_name, telegram_id, instagram,
                    fest_id, diamonds, start_date, end_date, created_at, confirmed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                winner_user_id, winner_name, telegram_id, instagram,
                fest_id, diamonds, start_date, end_date, int(time.time())
            ))
            await db.commit()

    async def get_last_random(self):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("""
                SELECT * FROM random_history ORDER BY id DESC LIMIT 1
            """)
            return await cur.fetchone()

    async def confirm_last_random(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                UPDATE random_history
                SET confirmed = 1
                WHERE id = (SELECT id FROM random_history ORDER BY id DESC LIMIT 1)
            """)
            await db.commit()

    async def get_random_candidates(self, start_ts: int, end_ts: int):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("""
                SELECT * FROM users
                WHERE registered = 1
                  AND banned = 0
                  AND registered_at BETWEEN ? AND ?
                  AND referral_count >= 3
                  AND diamonds >= 15
            """, (start_ts, end_ts))
            return await cur.fetchall()

    async def save_ad(self, title: str, body: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO ads (title, body, created_at)
                VALUES (?, ?, ?)
            """, (title, body, int(time.time())))
            await db.commit()

    async def get_ads(self, limit: int = 10):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM ads ORDER BY id DESC LIMIT ?", (limit,))
            return await cur.fetchall()


db = Database()
