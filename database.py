from __future__ import annotations

import sqlite3
import time
from typing import Any, Iterable

import aiosqlite

from config import settings


class Database:
    def __init__(self, path: str) -> None:
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute('PRAGMA journal_mode=WAL;')
            await db.execute('PRAGMA foreign_keys=ON;')

            await db.execute(
                '''
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
                    referral_awarded INTEGER DEFAULT 0,
                    diamonds INTEGER DEFAULT 0,
                    referral_count INTEGER DEFAULT 0,
                    joined_at INTEGER NOT NULL,
                    registered_at INTEGER,
                    updated_at INTEGER NOT NULL
                )
                '''
            )

            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inviter_id INTEGER NOT NULL,
                    invited_user_id INTEGER NOT NULL UNIQUE,
                    diamonds_added INTEGER NOT NULL,
                    created_at INTEGER NOT NULL
                )
                '''
            )

            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS diamond_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
                '''
            )

            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS prizes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    place_label TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    sort_order INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                '''
            )

            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS support_map (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    admin_message_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    user_text TEXT,
                    created_at INTEGER NOT NULL
                )
                '''
            )

            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS random_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    winner_user_id INTEGER NOT NULL,
                    winner_name TEXT NOT NULL,
                    winner_phone TEXT,
                    winner_region TEXT,
                    winner_district TEXT,
                    winner_diamonds INTEGER DEFAULT 0,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    participants_count INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    admin_id INTEGER NOT NULL
                )
                '''
            )

            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS winner_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    history_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY(history_id) REFERENCES random_history(id) ON DELETE CASCADE
                )
                '''
            )

            await db.execute(
                '''
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT DEFAULT '',
                    created_at INTEGER NOT NULL
                )
                '''
            )

            await db.commit()
            await self._seed_default_prizes(db)

    async def _seed_default_prizes(self, db: aiosqlite.Connection) -> None:
        cur = await db.execute('SELECT COUNT(*) FROM prizes')
        count = (await cur.fetchone())[0]
        if count:
            return
        now = int(time.time())
        default_rows = [
            ('🥇 1-o‘rin', 'Sovg‘a tez orada e’lon qilinadi', '', 1),
            ('🥈 2-o‘rin', 'Sovg‘a tez orada e’lon qilinadi', '', 2),
            ('🥉 3-o‘rin', 'Sovg‘a tez orada e’lon qilinadi', '', 3),
            ('🎲 Haftalik random', 'Sovg‘a tez orada e’lon qilinadi', '', 4),
        ]
        await db.executemany(
            '''
            INSERT INTO prizes (place_label, title, description, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            [(p, t, d, s, now, now) for p, t, d, s in default_rows],
        )
        await db.commit()

    async def execute(self, query: str, params: Iterable[Any] = ()) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(query, tuple(params))
            await db.commit()

    async def fetchone(self, query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute(query, tuple(params))
            return await cur.fetchone()

    async def fetchall(self, query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute(query, tuple(params))
            return await cur.fetchall()

    async def create_or_touch_user(self, user_id: int, username: str | None, tg_first_name: str | None) -> None:
        now = int(time.time())
        row = await self.fetchone('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if row:
            await self.execute(
                'UPDATE users SET username = ?, tg_first_name = ?, updated_at = ? WHERE user_id = ?',
                (username, tg_first_name, now, user_id),
            )
        else:
            await self.execute(
                '''
                INSERT INTO users (user_id, username, tg_first_name, joined_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (user_id, username, tg_first_name, now, now),
            )

    async def set_referrer_if_empty(self, user_id: int, referrer_id: int) -> None:
        if user_id == referrer_id:
            return
        row = await self.fetchone('SELECT referrer_id, is_registered FROM users WHERE user_id = ?', (user_id,))
        if row and row['referrer_id'] is None and row['is_registered'] == 0:
            await self.execute(
                'UPDATE users SET referrer_id = ?, updated_at = ? WHERE user_id = ?',
                (referrer_id, int(time.time()), user_id),
            )

    async def get_user(self, user_id: int) -> sqlite3.Row | None:
        return await self.fetchone('SELECT * FROM users WHERE user_id = ?', (user_id,))

    async def register_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str,
        last_name: str,
        region: str,
        district: str,
    ) -> tuple[bool, str]:
        now = int(time.time())
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            cur = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user = await cur.fetchone()
            if not user:
                return False, 'Foydalanuvchi topilmadi. Avval botda /start bosing.'

            first_registration = user['is_registered'] == 0
            await db.execute(
                '''
                UPDATE users
                SET username = ?, first_name = ?, last_name = ?, region = ?, district = ?,
                    is_registered = 1,
                    registered_at = COALESCE(registered_at, ?),
                    updated_at = ?
                WHERE user_id = ?
                ''',
                (username, first_name, last_name, region, district, now, now, user_id),
            )

            if first_registration:
                await db.execute(
                    'UPDATE users SET diamonds = diamonds + ?, updated_at = ? WHERE user_id = ?',
                    (settings.registration_bonus, now, user_id),
                )
                await db.execute(
                    '''
                    INSERT INTO diamond_history (user_id, amount, reason, created_at)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (user_id, settings.registration_bonus, 'Ro‘yxatdan o‘tish bonusi', now),
                )

            if first_registration and user['referrer_id'] and user['referrer_id'] != user_id and user['referral_awarded'] == 0:
                cur = await db.execute('SELECT 1 FROM referrals WHERE invited_user_id = ?', (user_id,))
                exists = await cur.fetchone()
                if not exists:
                    await db.execute(
                        '''
                        INSERT INTO referrals (inviter_id, invited_user_id, diamonds_added, created_at)
                        VALUES (?, ?, ?, ?)
                        ''',
                        (user['referrer_id'], user_id, settings.referral_bonus, now),
                    )
                    await db.execute(
                        '''
                        UPDATE users
                        SET diamonds = diamonds + ?, referral_count = referral_count + 1, updated_at = ?
                        WHERE user_id = ?
                        ''',
                        (settings.referral_bonus, now, user['referrer_id']),
                    )
                    await db.execute(
                        '''
                        INSERT INTO diamond_history (user_id, amount, reason, created_at)
                        VALUES (?, ?, ?, ?)
                        ''',
                        (user['referrer_id'], settings.referral_bonus, f'Referal bonusi: {user_id}', now),
                    )
                    await db.execute(
                        'UPDATE users SET referral_awarded = 1, updated_at = ? WHERE user_id = ?',
                        (now, user_id),
                    )

            await db.commit()
        return True, 'OK'

    async def get_top_users(self, limit: int = 10) -> list[sqlite3.Row]:
        return await self.fetchall(
            '''
            SELECT * FROM users
            WHERE is_registered = 1
            ORDER BY diamonds DESC, referral_count DESC, registered_at ASC
            LIMIT ?
            ''',
            (limit,),
        )

    async def get_rank_for_user(self, user_id: int) -> int | None:
        user = await self.get_user(user_id)
        if not user or user['is_registered'] != 1:
            return None
        row = await self.fetchone('SELECT COUNT(*) + 1 AS rank FROM users WHERE diamonds > ?', (user['diamonds'],))
        return int(row['rank']) if row else None

    async def get_neighbors(self, user_id: int) -> tuple[sqlite3.Row | None, sqlite3.Row | None]:
        rank = await self.get_rank_for_user(user_id)
        if rank is None:
            return None, None
        ranked = await self.fetchall(
            '''
            SELECT * FROM users
            WHERE is_registered = 1
            ORDER BY diamonds DESC, referral_count DESC, registered_at ASC
            LIMIT 2000
            '''
        )
        ids = [r['user_id'] for r in ranked]
        if user_id not in ids:
            return None, None
        idx = ids.index(user_id)
        prev_row = ranked[idx - 1] if idx > 0 else None
        next_row = ranked[idx + 1] if idx < len(ranked) - 1 else None
        return prev_row, next_row

    async def get_ball_history(self, user_id: int, limit: int = 20) -> list[sqlite3.Row]:
        return await self.fetchall(
            '''
            SELECT * FROM diamond_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            ''',
            (user_id, limit),
        )

    async def get_all_users(self) -> list[sqlite3.Row]:
        return await self.fetchall('SELECT * FROM users ORDER BY joined_at ASC')

    async def save_support_map(self, admin_id: int, admin_message_id: int, user_id: int, user_text: str) -> None:
        await self.execute(
            '''
            INSERT INTO support_map (admin_id, admin_message_id, user_id, user_text, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (admin_id, admin_message_id, user_id, user_text, int(time.time())),
        )

    async def get_support_map(self, admin_id: int, admin_message_id: int) -> sqlite3.Row | None:
        return await self.fetchone(
            '''
            SELECT * FROM support_map
            WHERE admin_id = ? AND admin_message_id = ?
            ORDER BY id DESC LIMIT 1
            ''',
            (admin_id, admin_message_id),
        )

    async def get_stats(self) -> dict[str, int]:
        total_users = (await self.fetchone('SELECT COUNT(*) AS c FROM users'))['c']
        registered = (await self.fetchone('SELECT COUNT(*) AS c FROM users WHERE is_registered = 1'))['c']
        referrals = (await self.fetchone('SELECT COUNT(*) AS c FROM referrals'))['c']
        diamonds = (await self.fetchone('SELECT COALESCE(SUM(diamonds), 0) AS c FROM users'))['c']
        return {
            'total_users': total_users,
            'registered': registered,
            'referrals': referrals,
            'diamonds': diamonds,
        }

    async def get_prizes(self) -> list[sqlite3.Row]:
        return await self.fetchall(
            'SELECT * FROM prizes WHERE is_active = 1 ORDER BY sort_order ASC, id ASC'
        )

    async def upsert_prize(self, place_label: str, title: str, description: str, sort_order: int) -> None:
        now = int(time.time())
        row = await self.fetchone('SELECT id FROM prizes WHERE place_label = ?', (place_label,))
        if row:
            await self.execute(
                '''
                UPDATE prizes SET title = ?, description = ?, sort_order = ?, updated_at = ?, is_active = 1
                WHERE id = ?
                ''',
                (title, description, sort_order, now, row['id']),
            )
        else:
            await self.execute(
                '''
                INSERT INTO prizes (place_label, title, description, sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (place_label, title, description, sort_order, now, now),
            )

    async def search_user(self, query: str) -> sqlite3.Row | None:
        if query.isdigit():
            row = await self.get_user(int(query))
            if row:
                return row
        query_like = f'%{query.replace("@", "")}%'
        return await self.fetchone(
            '''
            SELECT * FROM users
            WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ?
            ORDER BY joined_at DESC LIMIT 1
            ''',
            (query_like, query_like, query_like),
        )

    async def get_random_candidates(self, start_date: str, end_date: str) -> list[sqlite3.Row]:
        start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
        end_ts = int(datetime.combine(datetime.strptime(end_date, '%Y-%m-%d').date(), time(23, 59, 59)).timestamp())
        return await self.fetchall(
            '''
            SELECT * FROM users
            WHERE is_registered = 1
              AND registered_at IS NOT NULL
              AND registered_at BETWEEN ? AND ?
            ORDER BY registered_at ASC
            ''',
            (start_ts, end_ts),
        )

    async def save_random_history(
        self,
        winner_user_id: int,
        winner_name: str,
        winner_phone: str | None,
        winner_region: str | None,
        winner_district: str | None,
        winner_diamonds: int,
        start_date: str,
        end_date: str,
        participants_count: int,
        admin_id: int,
    ) -> int:
        now = int(time.time())
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                '''
                INSERT INTO random_history (
                    winner_user_id, winner_name, winner_phone, winner_region, winner_district,
                    winner_diamonds, start_date, end_date, participants_count, created_at, admin_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    winner_user_id,
                    winner_name,
                    winner_phone,
                    winner_region,
                    winner_district,
                    winner_diamonds,
                    start_date,
                    end_date,
                    participants_count,
                    now,
                    admin_id,
                ),
            )
            history_id = cur.lastrowid
            await db.execute(
                'INSERT INTO winner_status (history_id, status, updated_at) VALUES (?, ?, ?)',
                (history_id, '🟡 Bog‘lanilmadi', now),
            )
            await db.commit()
            return int(history_id)

    async def get_random_history(self, limit: int = 20) -> list[sqlite3.Row]:
        return await self.fetchall(
            '''
            SELECT rh.*, ws.status AS winner_status
            FROM random_history rh
            LEFT JOIN winner_status ws ON ws.history_id = rh.id
            ORDER BY rh.created_at DESC
            LIMIT ?
            ''',
            (limit,),
        )

    async def update_winner_status(self, history_id: int, status: str) -> None:
        now = int(time.time())
        row = await self.fetchone('SELECT history_id FROM winner_status WHERE history_id = ?', (history_id,))
        if row:
            await self.execute('UPDATE winner_status SET status = ?, updated_at = ? WHERE history_id = ?', (status, now, history_id))
        else:
            await self.execute('INSERT INTO winner_status (history_id, status, updated_at) VALUES (?, ?, ?)', (history_id, status, now))

    async def get_recent_winners(self, limit: int = 20) -> list[sqlite3.Row]:
        return await self.fetchall(
            '''
            SELECT rh.*, ws.status AS winner_status
            FROM random_history rh
            LEFT JOIN winner_status ws ON ws.history_id = rh.id
            ORDER BY rh.created_at DESC
            LIMIT ?
            ''',
            (limit,),
        )

    async def add_admin_log(self, admin_id: int, action: str, details: str = '') -> None:
        await self.execute(
            'INSERT INTO admin_logs (admin_id, action, details, created_at) VALUES (?, ?, ?, ?)',
            (admin_id, action, details, int(time.time())),
        )


db = Database(settings.db_path)
