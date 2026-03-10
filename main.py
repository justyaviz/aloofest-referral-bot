import asyncio
import hashlib
import hmac
import html
import io
import json
import logging
import os
import random
import sqlite3
from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional

import aiohttp
import aiosqlite
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from openpyxl import Workbook

# =========================
# CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
WEBAPP_SECRET = os.getenv("WEBAPP_SECRET", "change-me-secret")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "aloo_uzb").replace("@", "").strip()
SHOP_BOT_USERNAME = os.getenv("SHOP_BOT_USERNAME", "aloouz_bot").replace("@", "").strip()
ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
DB_PATH = os.getenv("DB_PATH", "bot.db")
PORT = int(os.getenv("PORT", "8080"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")
if not BASE_URL:
    raise RuntimeError("BASE_URL topilmadi")

CHANNEL_URL = f"https://t.me/{CHANNEL_USERNAME}"
SHOP_BOT_URL = f"https://t.me/{SHOP_BOT_USERNAME}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

router = Router()
BOT_USERNAME_CACHE = None

# =========================
# REGIONS / DISTRICTS
# =========================
DISTRICTS = {
    "Toshkent sh.": [
        "Bektemir", "Chilonzor", "Yakkasaroy", "Mirobod", "Mirzo Ulug‘bek",
        "Olmazor", "Sergeli", "Shayxontohur", "Uchtepa", "Yashnobod", "Yunusobod"
    ],
    "Toshkent vil.": [
        "Angren", "Bekobod sh.", "Chirchiq", "Olmaliq", "Ohangaron sh.",
        "Yangiyo‘l sh.", "Nurafshon", "Bekobod tumani", "Bo‘ka", "Bo‘stonliq",
        "Chinoz", "Qibray", "Ohangaron tumani", "Oqqo‘rg‘on", "Parkent",
        "Piskent", "Quyi Chirchiq", "Yangiyo‘l tumani", "Yuqori Chirchiq", "Zangiota"
    ],
    "Andijon": [
        "Andijon sh.", "Xonobod", "Andijon tumani", "Asaka", "Baliqchi",
        "Bo‘ston", "Buloqboshi", "Izboskan", "Jalaquduq", "Marhamat",
        "Oltinko‘l", "Paxtaobod", "Qo‘rg‘ontepa", "Shahrixon", "Ulug‘nor", "Xo‘jaobod"
    ],
    "Farg‘ona": [
        "Farg‘ona sh.", "Qo‘qon", "Marg‘ilon", "Quvasoy", "Farg‘ona tumani",
        "Oltiariq", "Bag‘dod", "Beshariq", "Buvayda", "Dang‘ara",
        "Furqat", "Qo‘shtepa", "Quva", "Rishton", "So‘x",
        "Toshloq", "Uchko‘prik", "Yozyovon"
    ],
    "Namangan": [
        "Namangan sh.", "Chust", "Kosonsoy", "Pop", "To‘raqo‘rg‘on",
        "Uychi", "Uchqo‘rg‘on", "Chortoq", "Mingbuloq", "Namangan tumani",
        "Norin", "Yangiqo‘rg‘on"
    ],
    "Samarqand": [
        "Samarqand sh.", "Kattaqo‘rg‘on sh.", "Bulung‘ur", "Ishtixon",
        "Jomboy", "Kattaqo‘rg‘on tumani", "Qo‘shrabot", "Narpay",
        "Nurobod", "Oqdaryo", "Paxtachi", "Pastdarg‘om",
        "Payariq", "Samarqand tumani", "Toyloq", "Urgut"
    ],
    "Buxoro": [
        "Buxoro sh.", "Kogon sh.", "Buxoro tumani", "G‘ijduvon",
        "Jondor", "Kogon tumani", "Olot", "Peshku",
        "Qorako‘l", "Qorovulbozor", "Romitan", "Shofirkon", "Vobkent"
    ],
    "Xorazm": [
        "Urganch sh.", "Xiva sh.", "Bog‘ot", "Gurlan", "Xiva tumani",
        "Hazorasp", "Xonqa", "Qo‘shko‘pir", "Shovot",
        "Urganch tumani", "Yangiariq", "Yangibozor", "Tuproqqal’a"
    ],
    "Qashqadaryo": [
        "Qarshi sh.", "Shahrisabz sh.", "Dehqonobod", "Kasbi", "Kitob",
        "Koson", "Ko‘kdala", "Mirishkor", "Muborak", "Nishon",
        "Qamashi", "Qarshi tumani", "Yakkabog‘", "Chiroqchi", "Shahrisabz tumani", "G‘uzor"
    ],
    "Surxondaryo": [
        "Termiz sh.", "Angor", "Bandixon", "Boysun", "Denov",
        "Jarqo‘rg‘on", "Muzrabot", "Oltinsoy", "Qiziriq", "Qumqo‘rg‘on",
        "Sariosiyo", "Sherobod", "Sho‘rchi", "Termiz tumani", "Uzun"
    ],
    "Navoiy": [
        "Navoiy sh.", "Zarafshon", "G‘ozg‘on", "Karmana", "Konimex",
        "Navbahor", "Nurota", "Qiziltepa", "Tomdi", "Uchquduq", "Xatirchi"
    ],
    "Jizzax": [
        "Jizzax sh.", "Arnasoy", "Baxmal", "Do‘stlik", "Forish",
        "G‘allaorol", "Mirzacho‘l", "Paxtakor", "Yangiobod",
        "Zafarobod", "Zarbdor", "Zomin", "Sharof Rashidov"
    ],
    "Sirdaryo": [
        "Guliston sh.", "Shirin", "Yangiyer", "Boyovut", "Guliston tumani",
        "Mirzaobod", "Oqoltin", "Sardoba", "Sayxunobod", "Sirdaryo", "Xovos"
    ],
    "Qoraqalpog‘iston": [
        "Nukus sh.", "Amudaryo", "Beruniy", "Bo‘zatov", "Chimboy",
        "Ellikqal’a", "Kegeyli", "Mo‘ynoq", "Nukus tumani", "Qanliko‘l",
        "Qo‘ng‘irot", "Qorao‘zak", "Shumanay", "Taxtako‘pir", "To‘rtko‘l", "Xo‘jayli"
    ],
}
REGIONS = list(DISTRICTS.keys())

# =========================
# STATES
# =========================
class SupportState(StatesGroup):
    waiting_message = State()


class BroadcastState(StatesGroup):
    waiting_content = State()


# =========================
# RANDOM PICKER
# =========================
@dataclass
class RandomPicker:
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    year: int = datetime.now().year
    month: int = datetime.now().month


RANDOM_STATE: dict[int, RandomPicker] = {}

# =========================
# TEXTS
# =========================
WELCOME_TEXT = """
🎉 <b>aloo konkurs botiga xush kelibsiz!</b>

Bu bot orqali siz:
• konkursda qatnashishingiz
• do‘stlaringizni taklif qilib 💎 ball yig‘ishingiz
• top rankingga kirishingiz
• random g‘oliblar tarixini ko‘rishingiz mumkin

Quyidagi menyudan kerakli bo‘limni tanlang.
""".strip()

SUBSCRIBE_TEXT = f"""
📌 <b>Botdan foydalanish uchun quyidagilarni bajaring:</b>

1️⃣ <b>{CHANNEL_USERNAME}</b> kanaliga a’zo bo‘ling  
2️⃣ <b>{SHOP_BOT_USERNAME}</b> botiga /start bosing

Hammasini bajarganingizdan so‘ng <b>✅ Tekshirish</b> tugmasini bosing.
""".strip()

SUBSCRIBE_OK_TEXT = """
✅ <b>Zo‘r, obuna tasdiqlandi!</b>

Endi konkurs ishtirokchisi bo‘lish uchun ro‘yxatdan o‘ting.
Quyidagi tugma orqali formani to‘ldiring.
""".strip()

REGISTERED_TEXT = """
✅ <b>Siz allaqachon ro‘yxatdan o‘tgansiz.</b>

Endi do‘stlaringizni taklif qilib 💎 ball yig‘ishingiz mumkin.
""".strip()

SUPPORT_TEXT = """
📞 <b>Bog‘lanish</b>

Iltimos, savolingiz yoki xabaringizni yuboring.
Xabaringiz adminlarga jo‘natiladi.

Chiqish uchun <b>❌ Yakunlash</b> tugmasini bosing.
""".strip()

# =========================
# HELPERS
# =========================
def esc(text: str | None) -> str:
    return html.escape(text or "")


def now_ts() -> int:
    return int(datetime.now().timestamp())


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def sign_uid(uid: int) -> str:
    return hmac.new(
        WEBAPP_SECRET.encode(),
        str(uid).encode(),
        hashlib.sha256
    ).hexdigest()


def verify_uid(uid: int, sig: str) -> bool:
    return hmac.compare_digest(sign_uid(uid), sig)


def month_name(month: int) -> str:
    return {
        1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel", 5: "May", 6: "Iyun",
        7: "Iyul", 8: "Avgust", 9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"
    }[month]


async def get_bot_username(bot: Bot) -> str:
    global BOT_USERNAME_CACHE
    if BOT_USERNAME_CACHE:
        return BOT_USERNAME_CACHE
    me = await bot.get_me()
    BOT_USERNAME_CACHE = me.username
    return BOT_USERNAME_CACHE


async def invite_link(bot: Bot, user_id: int) -> str:
    username = await get_bot_username(bot)
    return f"https://t.me/{username}?start=ref_{user_id}"


async def is_subscribed_http(user_id: int) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {
        "chat_id": f"@{CHANNEL_USERNAME}",
        "user_id": user_id,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=15) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    return False
                status = data["result"]["status"]
                return status in ("member", "administrator", "creator")
    except Exception:
        return False


# =========================
# DATABASE
# =========================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
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
            diamonds_added INTEGER NOT NULL DEFAULT 5,
            created_at INTEGER NOT NULL
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS support_map (
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
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            participants_count INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            admin_id INTEGER NOT NULL
        )
        """)

        await db.commit()


async def create_or_touch_user(user_id: int, username: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET username = ?, updated_at = ? WHERE user_id = ?",
                (username, now_ts(), user_id)
            )
        else:
            await db.execute("""
                INSERT INTO users (user_id, username, joined_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, now_ts(), now_ts()))
        await db.commit()


async def set_referrer_if_empty(user_id: int, referrer_id: int):
    if user_id == referrer_id:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT referrer_id, is_registered FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            current_referrer, is_registered = row
            if current_referrer is None and is_registered == 0:
                await db.execute(
                    "UPDATE users SET referrer_id = ?, updated_at = ? WHERE user_id = ?",
                    (referrer_id, now_ts(), user_id)
                )
                await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()


async def register_user(user_id: int, username: str | None, first_name: str, last_name: str, region: str, district: str):
    async with aiosqlite.connect(DB_PATH) as db:
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
                registered_at = CASE WHEN registered_at IS NULL THEN ? ELSE registered_at END,
                updated_at = ?
            WHERE user_id = ?
        """, (
            username, first_name, last_name, region, district,
            now_ts(), now_ts(), user_id
        ))

        # Fake referral filter:
        # - self-ref yo'q
        # - faqat bir marta
        # - faqat first registration
        # - taklif qilingan user kanalga obuna bo'lgan bo'lsa
        if first_registration and user["referrer_id"] and user["referrer_id"] != user_id and user["referral_awarded"] == 0:
            subscribed = await is_subscribed_http(user_id)
            if subscribed:
                await db.execute("""
                    INSERT OR IGNORE INTO referrals (inviter_id, invited_user_id, diamonds_added, created_at)
                    VALUES (?, ?, 5, ?)
                """, (user["referrer_id"], user_id, now_ts()))

                cur2 = await db.execute(
                    "SELECT COUNT(*) FROM referrals WHERE invited_user_id = ?",
                    (user_id,)
                )
                inserted = (await cur2.fetchone())[0]

                if inserted > 0:
                    await db.execute("""
                        UPDATE users
                        SET diamonds = diamonds + 5,
                            referral_count = referral_count + 1,
                            updated_at = ?
                        WHERE user_id = ?
                    """, (now_ts(), user["referrer_id"]))

                    await db.execute("""
                        UPDATE users
                        SET referral_awarded = 1,
                            updated_at = ?
                        WHERE user_id = ?
                    """, (now_ts(), user_id))

        await db.commit()
        return True, "OK"


async def top_users(limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = await db.execute("""
            SELECT * FROM users
            WHERE is_registered = 1
            ORDER BY diamonds DESC, referral_count DESC, registered_at ASC
            LIMIT ?
        """, (limit,))
        return await cur.fetchall()


async def all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = await db.execute("SELECT * FROM users ORDER BY joined_at ASC")
        return await cur.fetchall()


async def stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM users WHERE is_registered = 1")
        registered = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM referrals")
        referrals = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COALESCE(SUM(diamonds), 0) FROM users")
        total_diamonds = (await cur.fetchone())[0]

        return {
            "total_users": total_users,
            "registered": registered,
            "referrals": referrals,
            "diamonds": total_diamonds,
        }


async def save_support_map(admin_id: int, admin_message_id: int, user_id: int, user_text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO support_map (admin_id, admin_message_id, user_id, user_text, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (admin_id, admin_message_id, user_id, user_text, now_ts()))
        await db.commit()


async def get_support_map(admin_id: int, admin_message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = await db.execute("""
            SELECT * FROM support_map
            WHERE admin_id = ? AND admin_message_id = ?
            ORDER BY id DESC
            LIMIT 1
        """, (admin_id, admin_message_id))
        return await cur.fetchone()


async def save_random_history(winner_user_id: int, winner_name: str, start_date: str, end_date: str, participants_count: int, admin_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO random_history (
                winner_user_id, winner_name, start_date, end_date,
                participants_count, created_at, admin_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            winner_user_id, winner_name, start_date, end_date,
            participants_count, now_ts(), admin_id
        ))
        await db.commit()


async def get_random_history(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = await db.execute("""
            SELECT * FROM random_history
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        return await cur.fetchall()


async def random_candidates(start_date: str, end_date: str):
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
    end_ts = int(datetime.combine(datetime.strptime(end_date, "%Y-%m-%d").date(), time(23, 59, 59)).timestamp())

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = await db.execute("""
            SELECT * FROM users
            WHERE is_registered = 1
              AND registered_at IS NOT NULL
              AND registered_at BETWEEN ? AND ?
            ORDER BY registered_at ASC
        """, (start_ts, end_ts))
        return await cur.fetchall()


# =========================
# KEYBOARDS
# =========================
def main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="🎉 Konkursda qatnashish"))
    kb.row(
        KeyboardButton(text="💎 Mening ballarim"),
        KeyboardButton(text="🔗 Do‘st taklif qilish"),
    )
    kb.row(
        KeyboardButton(text="🏆 Top ranking"),
        KeyboardButton(text="🕘 Random tarixi"),
    )
    kb.row(
        KeyboardButton(text="📞 Bog‘lanish"),
        KeyboardButton(text="ℹ️ Mening profilim"),
    )
    return kb.as_markup(resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="🎲 Random o‘yin"))
    kb.row(
        KeyboardButton(text="📣 Broadcast"),
        KeyboardButton(text="📊 Statistika"),
    )
    kb.row(
        KeyboardButton(text="📥 Excel export"),
        KeyboardButton(text="🏆 Admin top ranking"),
    )
    kb.row(KeyboardButton(text="🏠 Asosiy menyu"))
    return kb.as_markup(resize_keyboard=True)


def support_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text="❌ Yakunlash"))
    return kb.as_markup(resize_keyboard=True)


def subscribe_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📢 Kanalga a’zo bo‘lish", url=CHANNEL_URL))
    kb.row(InlineKeyboardButton(text="🤖 Botga /start bosish", url=SHOP_BOT_URL))
    kb.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"))
    return kb.as_markup()


def register_keyboard(user_id: int) -> InlineKeyboardMarkup:
    sig = sign_uid(user_id)
    register_url = f"{BASE_URL}/register?uid={user_id}&sig={sig}"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📝 Ro‘yxatdan o‘tish", url=register_url))
    return kb.as_markup()


def profile_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    sig = sign_uid(user_id)
    register_url = f"{BASE_URL}/register?uid={user_id}&sig={sig}"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ Ma’lumotlarni yangilash", url=register_url))
    kb.row(InlineKeyboardButton(text="🔗 Taklif havolam", callback_data="my_invite"))
    return kb.as_markup()


def winner_keyboard(phone: str, full_name: str) -> InlineKeyboardMarkup:
    clean_phone = "".join(ch for ch in (phone or "") if ch.isdigit() or ch == "+")
    share_text = f"🎉 aloo random g‘olibi:\n\n👤 {full_name}\n📞 {phone}"

    kb = InlineKeyboardBuilder()

    # tel: ba'zi clientlarda ishlaydi, ishlamasa oddiy share baribir qoladi
    if clean_phone:
        kb.row(
            InlineKeyboardButton(text="📞 Qo‘ng‘iroq qilish", url=f"tel:{clean_phone}")
        )

    kb.row(
        InlineKeyboardButton(
            text="📤 Ulashish",
            url=f"https://t.me/share/url?url=&text={share_text}"
        )
    )
    return kb.as_markup()


def build_calendar(admin_id: int) -> InlineKeyboardMarkup:
    state = RANDOM_STATE.get(admin_id, RandomPicker())
    y, m = state.year, state.month

    first_day = datetime(y, m, 1)
    if m == 12:
        next_month = datetime(y + 1, 1, 1)
    else:
        next_month = datetime(y, m + 1, 1)

    days_in_month = (next_month - first_day).days
    first_weekday = first_day.isoweekday()

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="◀️", callback_data="cal_prev"),
        InlineKeyboardButton(text=f"{month_name(m)} {y}", callback_data="cal_ignore"),
        InlineKeyboardButton(text="▶️", callback_data="cal_next"),
    )
    kb.row(*[
        InlineKeyboardButton(text=d, callback_data="cal_ignore")
        for d in ["Du", "Se", "Cho", "Pa", "Ju", "Sha", "Ya"]
    ])

    row = []
    for _ in range(1, first_weekday):
        row.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))

    for day in range(1, days_in_month + 1):
        date_str = f"{y:04d}-{m:02d}-{day:02d}"
        label = str(day)
        if state.start_date == date_str:
            label = f"🟢 {day}"
        elif state.end_date == date_str:
            label = f"🔴 {day}"

        row.append(InlineKeyboardButton(text=label, callback_data=f"cal_pick:{date_str}"))
        if len(row) == 7:
            kb.row(*row)
            row = []

    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))
        kb.row(*row)

    if state.start_date and state.end_date:
        kb.row(InlineKeyboardButton(text="🎯 G‘olibni random orqali aniqlash", callback_data="random_draw"))

    kb.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="random_cancel"))
    return kb.as_markup()


# =========================
# WEB
# =========================
def registration_html(user_id: int, first_name: str, last_name: str, region: str, district: str, sig: str) -> str:
    districts_json = json.dumps(DISTRICTS, ensure_ascii=False)
    region_options = "".join(
        f'<option value="{html.escape(r)}" {"selected" if r == region else ""}>{html.escape(r)}</option>'
        for r in REGIONS
    )

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1.0" />
  <title>aloo ro‘yxatdan o‘tish</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 0;
      font-family: Arial, sans-serif;
      background: linear-gradient(135deg, #0b1220, #111a2f);
      color: white;
    }}
    .wrap {{
      max-width: 480px;
      margin: 0 auto;
      padding: 18px;
    }}
    .card {{
      margin-top: 18px;
      border-radius: 18px;
      padding: 20px;
      background: rgba(255,255,255,0.07);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.1);
      box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
    }}
    p {{
      color: #d6e2ff;
      line-height: 1.5;
    }}
    label {{
      display: block;
      margin-top: 14px;
      margin-bottom: 6px;
      font-size: 14px;
      color: #dbeafe;
    }}
    input, select {{
      width: 100%;
      padding: 14px;
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 12px;
      background: rgba(255,255,255,0.08);
      color: white;
      font-size: 15px;
      outline: none;
    }}
    option {{
      color: black;
    }}
    button {{
      width: 100%;
      margin-top: 18px;
      padding: 15px;
      border: 0;
      border-radius: 12px;
      background: linear-gradient(90deg, #22c55e, #16a34a);
      color: white;
      font-size: 16px;
      font-weight: bold;
      cursor: pointer;
    }}
    .ok, .err {{
      display: none;
      margin-top: 14px;
      padding: 12px;
      border-radius: 12px;
      font-size: 14px;
    }}
    .ok {{
      background: rgba(34,197,94,0.15);
      border: 1px solid rgba(34,197,94,0.35);
      color: #dcfce7;
    }}
    .err {{
      background: rgba(239,68,68,0.15);
      border: 1px solid rgba(239,68,68,0.35);
      color: #fee2e2;
    }}
    .note {{
      margin-top: 12px;
      font-size: 13px;
      color: #cbd5e1;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>🎉 aloo konkurs ro‘yxati</h1>
      <p>Formani to‘ldiring va <b>aloofest</b> konkursida ishtirokingizni faollashtiring.</p>

      <form id="regForm">
        <label>Ism</label>
        <input id="first_name" type="text" value="{html.escape(first_name)}" required />

        <label>Familiya</label>
        <input id="last_name" type="text" value="{html.escape(last_name)}" required />

        <label>Viloyatingizni tanlang</label>
        <select id="region" required>
          <option value="">Tanlang</option>
          {region_options}
        </select>

        <label>Shahar yoki tumaningizni tanlang</label>
        <select id="district" required>
          <option value="">Avval viloyat tanlang</option>
        </select>

        <button type="submit">RO‘YXATDAN O‘TISH</button>

        <div class="note">Ma’lumotlaringiz saqlanadi va keyingi kirishda qayta yo‘qolmaydi.</div>
        <div class="ok" id="okBox"></div>
        <div class="err" id="errBox"></div>
      </form>
    </div>
  </div>

<script>
const districts = {districts_json};
const selectedRegion = {json.dumps(region, ensure_ascii=False)};
const selectedDistrict = {json.dumps(district, ensure_ascii=False)};
const uid = {user_id};
const sig = {json.dumps(sig)};

const regionEl = document.getElementById("region");
const districtEl = document.getElementById("district");
const okBox = document.getElementById("okBox");
const errBox = document.getElementById("errBox");
const form = document.getElementById("regForm");

function loadDistricts(region, selected = "") {{
  districtEl.innerHTML = "";
  if (!region || !districts[region]) {{
    districtEl.innerHTML = '<option value="">Avval viloyat tanlang</option>';
    return;
  }}
  const first = document.createElement("option");
  first.value = "";
  first.textContent = "Tanlang";
  districtEl.appendChild(first);

  districts[region].forEach(item => {{
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    if (item === selected) opt.selected = true;
    districtEl.appendChild(opt);
  }});
}}

regionEl.addEventListener("change", () => {{
  loadDistricts(regionEl.value, "");
}});

if (selectedRegion) {{
  regionEl.value = selectedRegion;
  loadDistricts(selectedRegion, selectedDistrict);
}}

form.addEventListener("submit", async (e) => {{
  e.preventDefault();
  okBox.style.display = "none";
  errBox.style.display = "none";

  const payload = {{
    uid,
    sig,
    first_name: document.getElementById("first_name").value.trim(),
    last_name: document.getElementById("last_name").value.trim(),
    region: regionEl.value,
    district: districtEl.value,
  }};

  try {{
    const res = await fetch("/api/register", {{
      method: "POST",
      headers: {{
        "Content-Type": "application/json"
      }},
      body: JSON.stringify(payload)
    }});

    const data = await res.json();

    if (data.ok) {{
      okBox.textContent = "✅ Tabriklaymiz! Ma’lumotlaringiz saqlandi. Endi botga qaytib davom etishingiz mumkin.";
      okBox.style.display = "block";
    }} else {{
      errBox.textContent = data.error || "Xatolik yuz berdi";
      errBox.style.display = "block";
    }}
  }} catch (e) {{
    errBox.textContent = "Server bilan bog‘lanishda xatolik yuz berdi.";
    errBox.style.display = "block";
  }}
}});
</script>
</body>
</html>"""


async def handle_health(request: web.Request):
    return web.Response(text="OK")


async def handle_register_page(request: web.Request):
    try:
        uid = int(request.query.get("uid", "0"))
    except ValueError:
        return web.Response(text="Noto‘g‘ri uid", status=400)

    sig = request.query.get("sig", "")
    if not uid or not verify_uid(uid, sig):
        return web.Response(text="Ruxsat yo‘q", status=403)

    user = await get_user(uid)
    if not user:
        # foydalanuvchi /start bosmagan bo'lsa
        return web.Response(
            text="Foydalanuvchi topilmadi. Avval botda /start bosing va qayta urinib ko‘ring.",
            status=404
        )

    html_page = registration_html(
        uid,
        user["first_name"] or "",
        user["last_name"] or "",
        user["region"] or "",
        user["district"] or "",
        sig
    )
    return web.Response(text=html_page, content_type="text/html")


async def handle_register_api(request: web.Request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto‘g‘ri so‘rov"})

    uid = int(data.get("uid", 0))
    sig = data.get("sig", "")
    first_name = str(data.get("first_name", "")).strip()
    last_name = str(data.get("last_name", "")).strip()
    region = str(data.get("region", "")).strip()
    district = str(data.get("district", "")).strip()

    if not uid or not verify_uid(uid, sig):
        return web.json_response({"ok": False, "error": "Ruxsat yo‘q"})

    if not first_name:
        return web.json_response({"ok": False, "error": "Ism kiritilishi shart"})
    if not last_name:
        return web.json_response({"ok": False, "error": "Familiya kiritilishi shart"})
    if region not in DISTRICTS:
        return web.json_response({"ok": False, "error": "Viloyat noto‘g‘ri"})
    if district not in DISTRICTS[region]:
        return web.json_response({"ok": False, "error": "Tuman/Shahar noto‘g‘ri"})

    user = await get_user(uid)
    if not user:
        return web.json_response({"ok": False, "error": "Foydalanuvchi topilmadi. Avval botda /start bosing."})

    ok, msg = await register_user(
        uid,
        user["username"],
        first_name,
        last_name,
        region,
        district
    )
    if not ok:
        return web.json_response({"ok": False, "error": msg})

    return web.json_response({"ok": True})


async def setup_web_server():
    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_get("/register", handle_register_page)
    app.router.add_post("/api/register", handle_register_api)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logging.info("Web server ishlayapti: %s", PORT)


# =========================
# BOT HANDLERS
# =========================
@router.message(CommandStart())
async def start_handler(message: Message):
    await create_or_touch_user(message.from_user.id, message.from_user.username)

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("ref_"):
        ref = parts[1].replace("ref_", "").strip()
        if ref.isdigit():
            await set_referrer_if_empty(message.from_user.id, int(ref))

    await message.answer(WELCOME_TEXT, reply_markup=main_menu())


@router.message(Command("admin"))
async def admin_handler(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Sizda bu bo‘limga kirish huquqi yo‘q.")
        return
    await message.answer("🛠 <b>Admin panel</b>", reply_markup=admin_menu())


@router.message(F.text == "🏠 Asosiy menyu")
async def main_back_handler(message: Message):
    await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu())


@router.message(F.text == "🎉 Konkursda qatnashish")
async def contest_handler(message: Message):
    await create_or_touch_user(message.from_user.id, message.from_user.username)

    user = await get_user(message.from_user.id)
    if user and user["is_registered"] == 1:
        await message.answer(REGISTERED_TEXT, reply_markup=profile_actions_keyboard(message.from_user.id))
        return

    await message.answer(SUBSCRIBE_TEXT, reply_markup=subscribe_keyboard())


@router.callback_query(F.data == "check_sub")
async def check_sub_handler(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    if user and user["is_registered"] == 1:
        await callback.message.answer(REGISTERED_TEXT, reply_markup=profile_actions_keyboard(callback.from_user.id))
        await callback.answer()
        return

    subscribed = await is_subscribed_http(callback.from_user.id)
    if not subscribed:
        await callback.message.answer(
            f"❌ Siz hali <b>@{CHANNEL_USERNAME}</b> kanaliga a’zo bo‘lmagansiz.\n\n"
            f"Avval obuna bo‘lib, keyin yana <b>✅ Tekshirish</b> tugmasini bosing.",
            reply_markup=subscribe_keyboard()
        )
        await callback.answer("Obuna topilmadi", show_alert=True)
        return

    await callback.message.answer(SUBSCRIBE_OK_TEXT, reply_markup=register_keyboard(callback.from_user.id))
    await callback.answer("Obuna tasdiqlandi")


@router.callback_query(F.data == "my_invite")
async def my_invite_handler(callback: CallbackQuery, bot: Bot):
    link = await invite_link(bot, callback.from_user.id)
    await callback.message.answer(
        f"🔗 <b>Sizning maxsus taklif havolangiz:</b>\n\n{link}\n\n"
        f"Har bir muvaffaqiyatli ro‘yxatdan o‘tgan do‘st uchun sizga <b>+5 💎</b> yoziladi."
    )
    await callback.answer()


@router.message(F.text == "💎 Mening ballarim")
async def my_points_handler(message: Message):
    user = await get_user(message.from_user.id)
    if not user or user["is_registered"] != 1:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    await message.answer(
        f"💎 <b>Mening ballarim</b>\n\n"
        f"💠 Jami ball: <b>{user['diamonds']}</b>\n"
        f"👥 Taklif qilgan do‘stlar: <b>{user['referral_count']}</b>\n\n"
        f"Har bir muvaffaqiyatli do‘st uchun: <b>+5 💎</b>"
    )


@router.message(F.text == "🔗 Do‘st taklif qilish")
async def invite_handler(message: Message, bot: Bot):
    user = await get_user(message.from_user.id)
    if not user or user["is_registered"] != 1:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    link = await invite_link(bot, message.from_user.id)
    await message.answer(
        f"🚀 <b>Do‘st taklif qilish havolangiz:</b>\n\n{link}\n\n"
        f"Do‘stingiz ushbu havola orqali kirib ro‘yxatdan o‘tsa sizga <b>+5 💎</b> beriladi."
    )


@router.message(F.text == "ℹ️ Mening profilim")
async def profile_handler(message: Message):
    user = await get_user(message.from_user.id)
    if not user or user["is_registered"] != 1:
        await message.answer("Siz hali ro‘yxatdan o‘tmagansiz.")
        return

    await message.answer(
        f"👤 <b>Mening profilim</b>\n\n"
        f"Ism: <b>{esc(user['first_name'])}</b>\n"
        f"Familiya: <b>{esc(user['last_name'])}</b>\n"
        f"Viloyat: <b>{esc(user['region'])}</b>\n"
        f"Tuman/Shahar: <b>{esc(user['district'])}</b>\n"
        f"💎 Ball: <b>{user['diamonds']}</b>\n"
        f"👥 Takliflar: <b>{user['referral_count']}</b>",
        reply_markup=profile_actions_keyboard(message.from_user.id)
    )


@router.message(F.text == "🏆 Top ranking")
async def top_ranking_handler(message: Message):
    rows = await top_users(10)
    if not rows:
        await message.answer("Hozircha reyting shakllanmagan.")
        return

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    lines = ["🏆 <b>Top ranking — 💎 ball bo‘yicha</b>\n"]
    for i, row in enumerate(rows, start=1):
        full_name = f"{row['first_name'] or ''} {row['last_name'] or ''}".strip()
        lines.append(
            f"{medals[i-1]} <b>{esc(full_name)}</b> — <b>{row['diamonds']} 💎</b> | {row['referral_count']} ta"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == "🕘 Random tarixi")
async def random_history_handler(message: Message):
    rows = await get_random_history(15)
    if not rows:
        await message.answer("Hozircha random tarixi yo‘q.")
        return

    lines = ["🕘 <b>Random g‘oliblar tarixi</b>\n"]
    for idx, row in enumerate(rows, start=1):
        dt = datetime.fromtimestamp(row["created_at"]).strftime("%d.%m.%Y %H:%M")
        lines.append(
            f"{idx}. <b>{esc(row['winner_name'])}</b>\n"
            f"📅 {row['start_date']} — {row['end_date']}\n"
            f"👥 Ishtirokchilar: {row['participants_count']}\n"
            f"🕒 {dt}\n"
        )
    await message.answer("\n".join(lines))


# =========================
# SUPPORT
# =========================
@router.message(F.text == "📞 Bog‘lanish")
async def support_start_handler(message: Message, state: FSMContext):
    await state.set_state(SupportState.waiting_message)
    await message.answer(SUPPORT_TEXT, reply_markup=support_menu())


@router.message(F.text == "❌ Yakunlash")
async def support_end_handler(message: Message, state: FSMContext):
    current = await state.get_state()
    if current == SupportState.waiting_message:
        await state.clear()
        await message.answer("✅ Bog‘lanish bo‘limidan chiqdingiz.", reply_markup=main_menu())


@router.message(SupportState.waiting_message)
async def support_message_handler(message: Message, state: FSMContext, bot: Bot):
    user = await get_user(message.from_user.id)
    full_name = "Noma’lum"
    if user and user["first_name"]:
        full_name = f"{user['first_name']} {user['last_name'] or ''}".strip()

    user_text = message.text or message.caption or "[Media xabar]"
    text = (
        f"📩 <b>Yangi bog‘lanish xabari</b>\n\n"
        f"👤 User ID: <code>{message.from_user.id}</code>\n"
        f"🧑 Ism: <b>{esc(full_name)}</b>\n"
        f"💬 Xabar:\n{esc(user_text)}"
    )

    sent_count = 0
    for admin_id in ADMIN_IDS:
        try:
            sent = await bot.send_message(admin_id, text)
            await save_support_map(admin_id, sent.message_id, message.from_user.id, user_text)
            sent_count += 1
        except Exception:
            pass

    await message.answer(
        f"✅ Xabaringiz yuborildi. ({sent_count} ta admin)\n"
        f"Yana yozishingiz mumkin yoki <b>❌ Yakunlash</b> tugmasini bosing."
    )


@router.message(F.reply_to_message)
async def admin_reply_handler(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    reply_to = message.reply_to_message
    if not reply_to:
        return

    mapping = await get_support_map(message.from_user.id, reply_to.message_id)
    if not mapping:
        return

    admin_answer = message.text or message.caption or "[Javob]"
    original_question = mapping["user_text"] or "—"

    out = (
        f"📞 <b>Admin javobi</b>\n\n"
        f"📝 <b>Sizning savolingiz:</b>\n{esc(original_question)}\n\n"
        f"💬 <b>Admin javobi:</b>\n{esc(admin_answer)}"
    )

    try:
        await bot.send_message(mapping["user_id"], out)
        await message.reply("✅ Javob foydalanuvchiga yuborildi.")
    except Exception as e:
        await message.reply(f"❌ Xatolik: {e}")


# =========================
# ADMIN
# =========================
@router.message(F.text == "📊 Statistika")
async def admin_stats_handler(message: Message):
    if not is_admin(message.from_user.id):
        return

    s = await stats()
    await message.answer(
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Umumiy foydalanuvchilar: <b>{s['total_users']}</b>\n"
        f"✅ Ro‘yxatdan o‘tganlar: <b>{s['registered']}</b>\n"
        f"🔗 Referallar: <b>{s['referrals']}</b>\n"
        f"💎 Jami ballar: <b>{s['diamonds']}</b>"
    )


@router.message(F.text == "🏆 Admin top ranking")
async def admin_top_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    await top_ranking_handler(message)


@router.message(F.text == "📣 Broadcast")
async def broadcast_start_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(BroadcastState.waiting_content)
    await message.answer(
        "📣 Barcha foydalanuvchilarga yubormoqchi bo‘lgan xabaringizni yuboring.\n\n"
        "Bekor qilish uchun /cancel deb yozing."
    )


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    cur = await state.get_state()
    if cur:
        await state.clear()
        await message.answer(
            "✅ Bekor qilindi.",
            reply_markup=admin_menu() if is_admin(message.from_user.id) else main_menu()
        )


@router.message(BroadcastState.waiting_content)
async def broadcast_send_handler(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    users = await all_users()
    sent_count = 0
    failed_count = 0

    status = await message.answer("⏳ Broadcast yuborilmoqda...")

    for user in users:
        try:
            await bot.copy_message(
                chat_id=user["user_id"],
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            sent_count += 1
        except Exception:
            failed_count += 1

    await state.clear()
    await status.edit_text(
        f"✅ Broadcast tugadi.\n\n"
        f"📤 Yuborildi: <b>{sent_count}</b>\n"
        f"❌ Xato: <b>{failed_count}</b>"
    )
    await message.answer("🛠 Admin panel", reply_markup=admin_menu())


@router.message(F.text == "📥 Excel export")
async def excel_export_handler(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    rows = await all_users()

    wb = Workbook()
    ws = wb.active
    ws.title = "Users"
    ws.append([
        "User ID", "Username", "Ism", "Familiya",
        "Viloyat", "Tuman/Shahar", "Ro'yxatdan o'tganmi",
        "💎 Ball", "Takliflar", "Referrer ID", "Joined At", "Registered At"
    ])

    for row in rows:
        joined = datetime.fromtimestamp(row["joined_at"]).strftime("%Y-%m-%d %H:%M:%S") if row["joined_at"] else ""
        registered = datetime.fromtimestamp(row["registered_at"]).strftime("%Y-%m-%d %H:%M:%S") if row["registered_at"] else ""
        ws.append([
            row["user_id"],
            row["username"] or "",
            row["first_name"] or "",
            row["last_name"] or "",
            row["region"] or "",
            row["district"] or "",
            "ha" if row["is_registered"] else "yo‘q",
            row["diamonds"],
            row["referral_count"],
            row["referrer_id"] or "",
            joined,
            registered
        ])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    await bot.send_document(
        message.chat.id,
        BufferedInputFile(bio.read(), filename="aloo_users.xlsx"),
        caption="📥 Foydalanuvchilar ro‘yxati"
    )


# =========================
# RANDOM
# =========================
@router.message(F.text == "🎲 Random o‘yin")
async def random_start_handler(message: Message):
    if not is_admin(message.from_user.id):
        return

    RANDOM_STATE[message.from_user.id] = RandomPicker()
    await message.answer(
        "📅 <b>Random o‘yin</b>\n\n"
        "Avval <b>boshlanish sanasi</b>ni tanlang:",
        reply_markup=build_calendar(message.from_user.id)
    )


@router.callback_query(F.data == "cal_ignore")
async def cal_ignore_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "cal_prev")
async def cal_prev_handler(callback: CallbackQuery):
    admin_id = callback.from_user.id
    state = RANDOM_STATE.get(admin_id, RandomPicker())
    if state.month == 1:
        state.month = 12
        state.year -= 1
    else:
        state.month -= 1
    RANDOM_STATE[admin_id] = state
    await callback.message.edit_reply_markup(reply_markup=build_calendar(admin_id))
    await callback.answer()


@router.callback_query(F.data == "cal_next")
async def cal_next_handler(callback: CallbackQuery):
    admin_id = callback.from_user.id
    state = RANDOM_STATE.get(admin_id, RandomPicker())
    if state.month == 12:
        state.month = 1
        state.year += 1
    else:
        state.month += 1
    RANDOM_STATE[admin_id] = state
    await callback.message.edit_reply_markup(reply_markup=build_calendar(admin_id))
    await callback.answer()


@router.callback_query(F.data.startswith("cal_pick:"))
async def cal_pick_handler(callback: CallbackQuery):
    admin_id = callback.from_user.id
    if not is_admin(admin_id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return

    picked = callback.data.split(":", 1)[1]
    state = RANDOM_STATE.get(admin_id, RandomPicker())

    if not state.start_date:
        state.start_date = picked
        RANDOM_STATE[admin_id] = state
        await callback.message.edit_text(
            f"✅ Boshlanish sana: <b>{state.start_date}</b>\n\n"
            f"Endi <b>tugash sana</b>ni tanlang:",
            reply_markup=build_calendar(admin_id)
        )
        await callback.answer("Boshlanish sana tanlandi")
        return

    if not state.end_date:
        if picked < state.start_date:
            await callback.answer("Tugash sana boshlanish sanadan oldin bo‘lishi mumkin emas.", show_alert=True)
            return

        state.end_date = picked
        RANDOM_STATE[admin_id] = state
        await callback.message.edit_text(
            f"✅ Boshlanish sana: <b>{state.start_date}</b>\n"
            f"✅ Tugash sana: <b>{state.end_date}</b>\n\n"
            f"🎯 Endi g‘olibni aniqlash tugmasini bosing.",
            reply_markup=build_calendar(admin_id)
        )
        await callback.answer("Tugash sana tanlandi")
        return

    state.start_date = picked
    state.end_date = None
    RANDOM_STATE[admin_id] = state
    await callback.message.edit_text(
        f"✅ Yangi boshlanish sana: <b>{state.start_date}</b>\n\n"
        f"Endi tugash sanasini tanlang:",
        reply_markup=build_calendar(admin_id)
    )
    await callback.answer("Boshlanish sana yangilandi")


@router.callback_query(F.data == "random_cancel")
async def random_cancel_handler(callback: CallbackQuery):
    RANDOM_STATE.pop(callback.from_user.id, None)
    await callback.message.edit_text("❌ Random o‘yin bekor qilindi.")
    await callback.answer()


@router.callback_query(F.data == "random_draw")
async def random_draw_handler(callback: CallbackQuery, bot: Bot):
    admin_id = callback.from_user.id
    if not is_admin(admin_id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return

    state = RANDOM_STATE.get(admin_id)
    if not state or not state.start_date or not state.end_date:
        await callback.answer("Avval sana oralig‘ini tanlang", show_alert=True)
        return

    candidates = await random_candidates(state.start_date, state.end_date)

    eligible = []
    for user in candidates:
        if await is_subscribed_http(user["user_id"]):
            eligible.append(user)

    if not eligible:
        await callback.message.edit_text(
            f"😔 {state.start_date} dan {state.end_date} gacha ro‘yxatdan o‘tgan va "
            f"@{CHANNEL_USERNAME} kanaliga a’zo bo‘lgan ishtirokchilar topilmadi."
        )
        await callback.answer("Ishtirokchi topilmadi")
        return

    await callback.answer("Random boshlandi")

    progress_msg = await callback.message.edit_text(
        "🎲 <b>Random orqali g‘olib aniqlanmoqda...</b>\n\n"
        "⏳ Loading: <b>0%</b>"
    )

    steps = list(range(0, 101, 5))
    sleep_time = 45 / (len(steps) - 1)

    for p in steps[1:]:
        await asyncio.sleep(sleep_time)
        try:
            await progress_msg.edit_text(
                "🎲 <b>Random orqali g‘olib aniqlanmoqda...</b>\n\n"
                f"⏳ Loading: <b>{p}%</b>"
            )
        except TelegramBadRequest:
            pass

    winner = random.choice(eligible)

    full_name = f"{winner['first_name'] or ''} {winner['last_name'] or ''}".strip()
    if not full_name:
        full_name = "Noma’lum"

    phone = winner["phone"] or "Kiritilmagan"
    region = winner["region"] or "Kiritilmagan"
    district = winner["district"] or "Kiritilmagan"
    diamonds = winner["diamonds"] or 0

    await save_random_history(
        winner_user_id=winner["user_id"],
        winner_name=full_name,
        start_date=state.start_date,
        end_date=state.end_date,
        participants_count=len(eligible),
        admin_id=admin_id
    )

    winner_text = (
        "🏆 <b>G‘olib aniqlandi!</b>\n\n"
        f"👤 <b>Ism-familiya:</b> {esc(full_name)}\n"
        f"📞 <b>Telefon raqami:</b> {esc(phone)}\n"
        f"📍 <b>Hudud:</b> {esc(region)}, {esc(district)}\n"
        f"💎 <b>Balli:</b> {diamonds}\n\n"
        f"📅 <b>Davr:</b> {state.start_date} — {state.end_date}\n"
        f"👥 <b>Ishtirokchilar soni:</b> {len(eligible)}"
    )

    try:
        await progress_msg.edit_text(
            winner_text,
            reply_markup=winner_keyboard(phone, full_name)
        )
    except Exception as e:
        await callback.message.answer(
            f"❌ G‘olibni chiqarishda xatolik bo‘ldi:\n<code>{esc(str(e))}</code>"
        )
        return

    try:
        await bot.send_message(
            winner["user_id"],
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            "Siz aloo random o‘yinida g‘olib bo‘ldingiz!\n"
            "Tez orada siz bilan bog‘lanamiz. 📞"
        )
    except Exception:
        pass

    RANDOM_STATE.pop(admin_id, None)

# =========================
# FALLBACK
# =========================
@router.message()
async def fallback_handler(message: Message):
    await message.answer(
        "Kerakli bo‘limni menyudan tanlang.",
        reply_markup=admin_menu() if is_admin(message.from_user.id) else main_menu()
    )


# =========================
# MAIN
# =========================
async def main():
    await init_db()
    await setup_web_server()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logging.info("Bot polling bilan ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
