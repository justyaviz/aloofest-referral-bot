from __future__ import annotations

import sqlite3
import time
from typing import Any

import aiosqlite

from config import DB_PATH, REFERRAL_BONUS, REGISTRATION_BONUS


class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                tg_first_name TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                region TEXT,
                district TEXT,
                referrer_id INTEGER,
                is_registered INTEGER DEFAULT 0,
                diamonds INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0,
                referral_awarded INTEGER DEFAULT 0,
                joined_at INTEGER NOT NULL,
                registered_at INTEGER,
                updated_at INTEGER NOT NULL
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inviter_id INTEGER NOT NULL,
                invited_user_id INTEGER NOT NULL UNIQUE,
                bonus INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS diamond_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS support_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                admin_message_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_text TEXT,
                created_at INTEGER NOT NULL
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS random_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winner_user_id INTEGER NOT NULL,
                winner_name TEXT NOT NULL,
                winner_phone TEXT,
                winner_region TEXT,
                winner_district TEXT,
                winner_diamonds INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                participants_count INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                admin_id INTEGER NOT NULL
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS prizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                place_name TEXT NOT NULL,
                prize_title TEXT NOT NULL,
                prize_description TEXT,
                created_at INTEGER NOT NULL
            )
            """)

            await db.commit()

            cur = await db.execute("SELECT COUNT(*) FROM prizes")
            count = (await cur.fetchone())[0]
            if count == 0:
                now = int(time.time())
                default_prizes = [
                    ("🥇 1-o‘rin", "iPhone 15", "Asosiy sovg‘a"),
                    ("🥈 2-o‘rin", "Redmi Note", "Ikkinchi o‘rin sovg‘asi"),
                    ("🥉 3-o‘rin", "AirPods", "Uchinchi o‘rin sovg‘asi"),
                    ("🎲 Haftalik random", "Smart Watch", "Har hafta random sovg‘a"),
                ]
                await db.executemany(
                    "INSERT INTO prizes (place_name, prize_title, prize_description, created_at) VALUES (?, ?, ?, ?)",
                    [(a, b, c, now) for a, b, c in default_prizes]
                )
                await db.commit()

    async def add_or_touch_user(self, user_id: int, username: str | None, tg_first_name: str | None):
        now = int(time.time())
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            if row:
                await db.execute("""
                    UPDATE users
                    SET username = ?, tg_first_name = ?, updated_at = ?
                    WHERE user_id = ?
                """, (username, tg_first_name, now, user_id))
            else:
                await db.execute("""
                    INSERT INTO users (
                        user_id, username, tg_first_name, joined_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, username, tg_first_name, now, now))
            await db.commit()

    async def set_referrer_if_empty(self, user_id: int, referrer_id: int):
        if user_id == referrer_id:
            return
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT referrer_id, is_registered FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = await cur.fetchone()
            if not row:
                return
            current_referrer, is_registered = row
            if current_referrer is None and is_registered == 0:
                await db.execute(
                    "UPDATE users SET referrer_id = ?, updated_at = ? WHERE user_id = ?",
                    (referrer_id, int(time.time()), user_id)
                )
                await db.commit()

    async def get_user(self, user_id: int) -> sqlite3.Row | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return await cur.fetchone()

    async def register_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str,
        last_name: str,
        region: str,
        district: str,
        is_subscribed: bool,
    ):
        now = int(time.time())
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = await cur.fetchone()
            if not user:
                return False, "Foydalanuvchi topilmadi"

            first_registration = 1 if user["is_registered"] == 0 else 0

            await db.execute("""
                UPDATE users
                SET username = ?, first_name = ?, last_name = ?, region = ?, district = ?,
                    is_registered = 1,
                    registered_at = COALESCE(registered_at, ?),
                    updated_at = ?
                WHERE user_id = ?
            """, (
                username, first_name, last_name, region, district,
                now, now, user_id
            ))

            if first_registration:
                await db.execute("""
                    UPDATE users
                    SET diamonds = diamonds + ?
                    WHERE user_id = ?
                """, (REGISTRATION_BONUS, user_id))

                await db.execute("""
                    INSERT INTO diamond_history (user_id, amount, reason, created_at)
                    VALUES (?, ?, ?, ?)
                """, (user_id, REGISTRATION_BONUS, "Ro‘yxatdan o‘tish bonusi", now))

            if (
                first_registration
                and user["referrer_id"]
                and user["referrer_id"] != user_id
                and user["referral_awarded"] == 0
                and is_subscribed
            ):
                await db.execute("""
                    INSERT OR IGNORE INTO referrals (inviter_id, invited_user_id, bonus, created_at)
                    VALUES (?, ?, ?, ?)
                """, (user["referrer_id"], user_id, REFERRAL_BONUS, now))

                cur2 = await db.execute(
                    "SELECT COUNT(*) FROM referrals WHERE invited_user_id = ?",
                    (user_id,)
                )
                inserted_count = (await cur2.fetchone())[0]

                if inserted_count > 0:
                    await db.execute("""
                        UPDATE users
                        SET diamonds = diamonds + ?,
                            referral_count = referral_count + 1,
                            referral_awarded = referral_awarded,
                            updated_at = ?
                        WHERE user_id = ?
                    """, (REFERRAL_BONUS, now, user["referrer_id"]))

                    await db.execute("""
                        INSERT INTO diamond_history (user_id, amount, reason, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (user["referrer_id"], REFERRAL_BONUS, "Referal bonusi", now))

                    await db.execute("""
                        UPDATE users
                        SET referral_awarded = 1,
                            updated_at = ?
                        WHERE user_id = ?
                    """, (now, user_id))

            await db.commit()
            return True, "OK"

    async def get_top_users(self, limit: int = 10):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute("""
                SELECT * FROM users
                WHERE is_registered = 1
                ORDER BY diamonds DESC, referral_count DESC, registered_at ASC
                LIMIT ?
            """, (limit,))
            return await cur.fetchall()

    async def get_user_rank(self, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
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

            cur = await db.execute(
                "SELECT COUNT(*) FROM users WHERE is_registered = 1"
            )
            total = (await cur.fetchone())[0]

            return {"rank": rank, "total": total, "diamonds": diamonds}

    async def get_diamond_history(self, user_id: int, limit: int = 15):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute("""
                SELECT * FROM diamond_history
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            """, (user_id, limit))
            return await cur.fetchall()

    async def get_prizes(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute("""
                SELECT * FROM prizes
                ORDER BY id ASC
            """)
            return await cur.fetchall()

    async def get_stats(self):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cur.fetchone())[0]

            cur = await db.execute("SELECT COUNT(*) FROM users WHERE is_registered = 1")
            registered = (await cur.fetchone())[0]

            cur = await db.execute("SELECT COUNT(*) FROM referrals")
            referrals = (await cur.fetchone())[0]

            cur = await db.execute("SELECT COALESCE(SUM(diamonds), 0) FROM users")
            diamonds = (await cur.fetchone())[0]

            return {
                "total_users": total_users,
                "registered": registered,
                "referrals": referrals,
                "diamonds": diamonds,
            }

    async def get_all_users(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute("SELECT * FROM users ORDER BY joined_at ASC")
            return await cur.fetchall()

    async def save_support_thread(self, admin_id: int, admin_message_id: int, user_id: int, user_text: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO support_threads (admin_id, admin_message_id, user_id, user_text, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (admin_id, admin_message_id, user_id, user_text, int(time.time())))
            await db.commit()

    async def get_support_thread(self, admin_id: int, admin_message_id: int):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute("""
                SELECT * FROM support_threads
                WHERE admin_id = ? AND admin_message_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (admin_id, admin_message_id))
            return await cur.fetchone()

    async def get_random_candidates(self, start_date: str, end_date: str):
        start_ts = int(time.mktime(time.strptime(start_date, "%Y-%m-%d")))
        end_ts = int(time.mktime(time.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")))
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute("""
                SELECT * FROM users
                WHERE is_registered = 1
                  AND registered_at IS NOT NULL
                  AND registered_at BETWEEN ? AND ?
                ORDER BY registered_at ASC
            """, (start_ts, end_ts))
            return await cur.fetchall()

    async def save_random_history(
        self,
        winner_user_id: int,
        winner_name: str,
        winner_phone: str,
        winner_region: str,
        winner_district: str,
        winner_diamonds: int,
        start_date: str,
        end_date: str,
        participants_count: int,
        admin_id: int,
    ):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO random_history (
                    winner_user_id, winner_name, winner_phone, winner_region, winner_district,
                    winner_diamonds, start_date, end_date, participants_count, created_at, admin_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                winner_user_id, winner_name, winner_phone, winner_region, winner_district,
                winner_diamonds, start_date, end_date, participants_count, int(time.time()), admin_id
            ))
            await db.commit()

    async def get_random_history(self, limit: int = 20):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute("""
                SELECT * FROM random_history
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            return await cur.fetchall()

    async def search_users(self, query: str, limit: int = 10):
        like = f"%{query}%"
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            if query.isdigit():
                cur = await db.execute("""
                    SELECT * FROM users
                    WHERE user_id = ?
                    LIMIT ?
                """, (int(query), limit))
            else:
                cur = await db.execute("""
                    SELECT * FROM users
                    WHERE username LIKE ?
                       OR first_name LIKE ?
                       OR last_name LIKE ?
                       OR phone LIKE ?
                    LIMIT ?
                """, (like, like, like, like, limit))
            return await cur.fetchall()


db = Database(DB_PATH)
