import time
import aiosqlite
from config import DB_PATH, REGISTRATION_BONUS, REFERRAL_BONUS


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
                region TEXT,
                district TEXT,
                fest_id TEXT,
                referrer_id INTEGER,
                registered INTEGER DEFAULT 0,
                diamonds INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                created_at INTEGER,
                registered_at INTEGER
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                invited_user_id INTEGER PRIMARY KEY,
                inviter_id INTEGER,
                created_at INTEGER
            )
            """)

            await db.commit()

    async def add_user(self, user_id: int, username: str | None, tg_name: str | None):
        now = int(time.time())
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            if not row:
                await db.execute("""
                    INSERT INTO users (
                        user_id, username, tg_name, created_at
                    ) VALUES (?, ?, ?, ?)
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

    async def next_fest_id(self) -> str:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute("SELECT COUNT(*) FROM users WHERE registered = 1")
            count = (await cur.fetchone())[0] + 1
            return f"FEST-{count:03d}"

    async def register_user(self, user_id: int, full_name: str, instagram: str, region: str, district: str):
        now = int(time.time())
        fest_id = await self.next_fest_id()

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = await cur.fetchone()
            if not user:
                return False, "Foydalanuvchi topilmadi"

            first_registration = user["registered"] == 0

            await db.execute("""
                UPDATE users
                SET full_name = ?, instagram = ?, region = ?, district = ?,
                    fest_id = COALESCE(fest_id, ?),
                    registered = 1,
                    registered_at = COALESCE(registered_at, ?)
                WHERE user_id = ?
            """, (full_name, instagram, region, district, fest_id, now, user_id))

            if first_registration:
                await db.execute("""
                    UPDATE users
                    SET diamonds = diamonds + ?
                    WHERE user_id = ?
                """, (REGISTRATION_BONUS, user_id))

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
            return True, fest_id

    async def top_users(self, limit: int = 10):
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("""
                SELECT * FROM users
                WHERE registered = 1
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
                "SELECT COUNT(*) + 1 FROM users WHERE diamonds > ?",
                (diamonds,)
            )
            rank = (await cur.fetchone())[0]

            cur = await db.execute("SELECT COUNT(*) FROM users WHERE registered = 1")
            total = (await cur.fetchone())[0]

            return {"rank": rank, "total": total, "diamonds": diamonds}


db = Database()
