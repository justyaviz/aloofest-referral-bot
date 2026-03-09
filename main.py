import asyncio
import html
import logging
import os
import random
import sqlite3
from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# =========================
# CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "aloo_uzb").replace("@", "").strip()
CHANNEL_LINK = f"https://t.me/{CHANNEL_USERNAME}"
DB_PATH = os.getenv("DB_PATH", "bot.db")
TIMEZONE = ZoneInfo("Asia/Tashkent")
BOT_USERNAME_CACHE = None

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Environment variable qo'ying.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

router = Router()


# =========================
# TEXTS
# =========================
WELCOME_TEXT = """
🎉 <b>Aloofest konkurs botiga xush kelibsiz!</b>

Bu yerda siz do‘stlaringizni taklif qilib, 2 xil usulda sovg‘a yutishingiz mumkin. Quyidagi menyudan kerakli bo‘limni tanlang.
""".strip()

RULES_TEXT = f"""
🎯 <b>Sizda 2 xil yutish imkoniyati bor:</b>

<b>1️⃣ TOP 5 ga kirish</b>
🎁 Eng ko‘p do‘st taklif qilgan TOP 5 ishtirokchi qimmatbaho sovg‘alar uchun da’vogar bo‘ladi.
Sovg‘alar ro‘yxati tez orada e’lon qilinadi.

<b>2️⃣ Random o‘yini</b>
🎲 Kamida <b>3 ta do‘st</b> taklif qilgan bo‘lishingiz kerak.
Shuningdek, <b>@{CHANNEL_USERNAME}</b> kanaliga obuna bo‘lgan bo‘lishingiz shart.

Har hafta <b>@{CHANNEL_USERNAME}</b> kanaliga obuna bo‘lgan va talabga javob bergan ishtirokchilar orasidan <b>random</b> orqali 1 nafar g‘olib aniqlanadi. 🤩

🚀 Qanchalik ko‘p do‘st taklif qilsangiz, yutish imkoniyatingiz shunchalik oshadi!
""".strip()

REGISTRATION_DONE_TEXT = """
✅ <b>Tabriklaymiz!</b>

Ma’lumotlaringiz muvaffaqiyatli qabul qilindi.
Endi siz Aloofest konkursining to‘liq ishtirokchisiz. Do‘stlaringizni taklif qilishni boshlashingiz mumkin. 🚀
""".strip()

NEED_SUB_TEXT = f"""
❌ <b>Random o‘yinda qatnashish uchun shart bajarilmagan.</b>

Avval <b>@{CHANNEL_USERNAME}</b> kanaliga obuna bo‘ling, so‘ng yana urinib ko‘ring.
""".strip()

ADMIN_PANEL_TEXT = """
🛠 <b>Admin panel</b>

Quyidagi bo‘limlardan birini tanlang.
""".strip()

SUPPORT_TEXT = """
📞 <b>Yordam</b>

Savol yoki muammo bo‘lsa, administrator bilan bog‘laning.
""".strip()


# =========================
# REGIONS / DISTRICTS
# =========================
REGIONS = [
    "Toshkent sh.",
    "Toshkent vil.",
    "Samarqand",
    "Buxoro",
    "Andijon",
    "Farg'ona",
    "Namangan",
    "Xorazm",
    "Qashqadaryo",
    "Surxondaryo",
    "Navoiy",
    "Jizzax",
    "Sirdaryo",
    "Qoraqalpog'iston",
]

# Professional ishlashi uchun tuzilma tayyor.
# Kerak bo'lsa keyin juda oson kengaytiriladi.
DISTRICTS = {
    "Toshkent sh.": [
        "Yunusobod", "Chilonzor", "Olmazor", "Sergeli",
        "Yakkasaroy", "Mirzo Ulug'bek", "Shayxontohur",
        "Uchtepa", "Bektemir", "Yashnobod", "Mirobod",
        "Boshqa"
    ],
    "Toshkent vil.": [
        "Chirchiq", "Angren", "Olmaliq", "Bekobod",
        "Yangiyo'l", "Parkent", "Bo'stonliq", "Zangiota",
        "Qibray", "Ohangaron", "G'azalkent", "Boshqa"
    ],
    "Samarqand": [
        "Samarqand sh.", "Urgut", "Kattaqo'rg'on", "Pastdarg'om",
        "Ishtixon", "Bulung'ur", "Nurobod", "Toyloq", "Boshqa"
    ],
    "Buxoro": [
        "Buxoro sh.", "Kogon", "G'ijduvon", "Vobkent",
        "Qorako'l", "Jondor", "Romitan", "Boshqa"
    ],
    "Andijon": [
        "Andijon sh.", "Asaka", "Xonobod", "Shahrixon",
        "Baliqchi", "Bo'z", "Marhamat", "Boshqa"
    ],
    "Farg'ona": [
        "Farg'ona sh.", "Qo'qon", "Marg'ilon", "Quva",
        "Rishton", "Oltiariq", "Beshariq", "Boshqa"
    ],
    "Namangan": [
        "Namangan sh.", "Chust", "Kosonsoy", "Pop",
        "To'raqo'rg'on", "Uychi", "Chortoq", "Boshqa"
    ],
    "Xorazm": [
        "Urganch", "Xiva", "Hazorasp", "Qo'shko'pir",
        "Shovot", "Yangiariq", "Bog'ot", "Boshqa"
    ],
    "Qashqadaryo": [
        "Qarshi", "Shahrisabz", "Koson", "Kitob",
        "Yakkabog'", "Chiroqchi", "Muborak", "Boshqa"
    ],
    "Surxondaryo": [
        "Termiz", "Denov", "Sherobod", "Jarqo'rg'on",
        "Qumqo'rg'on", "Boysun", "Sho'rchi", "Boshqa"
    ],
    "Navoiy": [
        "Navoiy sh.", "Zarafshon", "Karmana", "Qiziltepa",
        "Nurota", "Konimex", "Xatirchi", "Boshqa"
    ],
    "Jizzax": [
        "Jizzax sh.", "Zomin", "G'allaorol", "Baxmal",
        "Paxtakor", "Do'stlik", "Forish", "Boshqa"
    ],
    "Sirdaryo": [
        "Guliston", "Shirin", "Yangiyer", "Boyovut",
        "Sardoba", "Sirdaryo", "Xovos", "Boshqa"
    ],
    "Qoraqalpog'iston": [
        "Nukus", "To'rtko'l", "Beruniy", "Xo'jayli",
        "Chimboy", "Qo'ng'irot", "Mo'ynoq", "Boshqa"
    ],
}


# =========================
# FSM
# =========================
class Registration(StatesGroup):
    full_name = State()
    phone = State()
    region = State()
    district = State()
    other_district = State()


# =========================
# IN-MEMORY ADMIN RANDOM STATE
# =========================
@dataclass
class RandomSelectionState:
    start_date: str | None = None
    end_date: str | None = None
    year: int = datetime.now(TIMEZONE).year
    month: int = datetime.now(TIMEZONE).month


ADMIN_RANDOM_STATE: dict[int, RandomSelectionState] = {}


# =========================
# DB
# =========================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            phone TEXT,
            region TEXT,
            district TEXT,
            referrer_id INTEGER,
            referral_confirmed INTEGER DEFAULT 0,
            referred_count INTEGER DEFAULT 0,
            registered_at INTEGER,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER NOT NULL,
            invited_id INTEGER NOT NULL UNIQUE,
            created_at INTEGER NOT NULL
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS random_draws (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            winner_user_id INTEGER NOT NULL,
            start_ts INTEGER NOT NULL,
            end_ts INTEGER NOT NULL,
            participant_count INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            admin_id INTEGER NOT NULL
        )
        """)
        await db.commit()


async def upsert_basic_user(user_id: int, username: str | None):
    now_ts = int(datetime.now(TIMEZONE).timestamp())
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET username = ?, updated_at = ? WHERE user_id = ?",
                (username, now_ts, user_id),
            )
        else:
            await db.execute("""
                INSERT INTO users (user_id, username, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, now_ts, now_ts))
        await db.commit()


async def set_referrer_if_empty(user_id: int, referrer_id: int):
    if user_id == referrer_id:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT referrer_id FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cur.fetchone()
        if row and row[0] is None:
            await db.execute(
                "UPDATE users SET referrer_id = ?, updated_at = ? WHERE user_id = ?",
                (referrer_id, int(datetime.now(TIMEZONE).timestamp()), user_id),
            )
            await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()


async def save_full_name(user_id: int, full_name: str):
    now_ts = int(datetime.now(TIMEZONE).timestamp())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET full_name = ?, updated_at = ? WHERE user_id = ?",
            (full_name, now_ts, user_id),
        )
        await db.commit()


async def save_phone(user_id: int, phone: str):
    now_ts = int(datetime.now(TIMEZONE).timestamp())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET phone = ?, updated_at = ? WHERE user_id = ?",
            (phone, now_ts, user_id),
        )
        await db.commit()


async def save_region(user_id: int, region: str):
    now_ts = int(datetime.now(TIMEZONE).timestamp())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET region = ?, updated_at = ? WHERE user_id = ?",
            (region, now_ts, user_id),
        )
        await db.commit()


async def complete_registration(user_id: int, district: str, username: str | None):
    now_ts = int(datetime.now(TIMEZONE).timestamp())
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await cur.fetchone()
        if not user:
            return

        await db.execute("""
            UPDATE users
            SET district = ?, username = ?, registered_at = ?, updated_at = ?
            WHERE user_id = ?
        """, (district, username, now_ts, now_ts, user_id))

        if user["referrer_id"] and not user["referral_confirmed"]:
            # invited_id UNIQUE, shuning uchun bir user bir marta count bo'ladi
            await db.execute("""
                INSERT OR IGNORE INTO referrals (inviter_id, invited_id, created_at)
                VALUES (?, ?, ?)
            """, (user["referrer_id"], user_id, now_ts))

            await db.execute("""
                UPDATE users
                SET referred_count = (
                    SELECT COUNT(*) FROM referrals WHERE inviter_id = ?
                )
                WHERE user_id = ?
            """, (user["referrer_id"], user["referrer_id"]))

            await db.execute("""
                UPDATE users
                SET referral_confirmed = 1
                WHERE user_id = ?
            """, (user_id,))

        await db.commit()


async def get_top_users(limit: int = 5):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = await db.execute("""
            SELECT * FROM users
            WHERE full_name IS NOT NULL AND phone IS NOT NULL
            ORDER BY referred_count DESC, registered_at ASC
            LIMIT ?
        """, (limit,))
        return await cur.fetchall()


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cur.fetchone())[0]

        cur = await db.execute("""
            SELECT COUNT(*) FROM users
            WHERE full_name IS NOT NULL AND phone IS NOT NULL AND region IS NOT NULL AND district IS NOT NULL
        """)
        registered_users = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM referrals")
        referrals = (await cur.fetchone())[0]

        return {
            "total_users": total_users,
            "registered_users": registered_users,
            "referrals": referrals,
        }


async def get_eligible_users_for_random(start_date_str: str, end_date_str: str):
    start_dt = datetime.combine(datetime.strptime(start_date_str, "%Y-%m-%d").date(), time(0, 0, 0), TIMEZONE)
    end_dt = datetime.combine(datetime.strptime(end_date_str, "%Y-%m-%d").date(), time(23, 59, 59), TIMEZONE)
    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        cur = await db.execute("""
            SELECT inviter_id, COUNT(DISTINCT invited_id) AS invite_count
            FROM referrals
            WHERE created_at BETWEEN ? AND ?
            GROUP BY inviter_id
            HAVING COUNT(DISTINCT invited_id) >= 3
        """, (start_ts, end_ts))
        rows = await cur.fetchall()

        result = []
        for row in rows:
            cur2 = await db.execute("SELECT * FROM users WHERE user_id = ?", (row["inviter_id"],))
            user = await cur2.fetchone()
            if user:
                result.append({
                    "user_id": user["user_id"],
                    "full_name": user["full_name"],
                    "phone": user["phone"],
                    "region": user["region"],
                    "district": user["district"],
                    "invite_count": row["invite_count"],
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                })
        return result


async def save_random_draw(winner_user_id: int, start_ts: int, end_ts: int, participant_count: int, admin_id: int):
    now_ts = int(datetime.now(TIMEZONE).timestamp())
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO random_draws (winner_user_id, start_ts, end_ts, participant_count, created_at, admin_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (winner_user_id, start_ts, end_ts, participant_count, now_ts, admin_id))
        await db.commit()


# =========================
# HELPERS
# =========================
def esc(text: str | None) -> str:
    return html.escape(text or "")


async def is_user_subscribed(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except (TelegramBadRequest, TelegramForbiddenError):
        return False
    except Exception:
        return False


def phone_for_tel_url(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit() or ch == "+")


async def get_bot_username(bot: Bot) -> str:
    global BOT_USERNAME_CACHE
    if BOT_USERNAME_CACHE:
        return BOT_USERNAME_CACHE
    me = await bot.get_me()
    BOT_USERNAME_CACHE = me.username
    return BOT_USERNAME_CACHE


async def build_invite_link(bot: Bot, user_id: int) -> str:
    username = await get_bot_username(bot)
    return f"https://t.me/{username}?start=ref_{user_id}"


def user_main_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🎉 Konkursda qatnashish"))
    builder.row(
        KeyboardButton(text="👤 Mening profilim"),
        KeyboardButton(text="🔗 Do'st taklif qilish"),
    )
    builder.row(
        KeyboardButton(text="🏆 TOP 5"),
        KeyboardButton(text="🎲 Random holati"),
    )
    builder.row(
        KeyboardButton(text="📜 Qoidalar"),
        KeyboardButton(text="📞 Yordam"),
    )
    return builder.as_markup(resize_keyboard=True)


def admin_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🎲 Random o'yin"))
    builder.row(
        KeyboardButton(text="📊 Statistika"),
        KeyboardButton(text="🏆 TOP 5 admin"),
    )
    builder.row(KeyboardButton(text="🏠 Asosiy menyu"))
    return builder.as_markup(resize_keyboard=True)


def region_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for region in REGIONS:
        builder.add(KeyboardButton(text=region))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def district_keyboard(region: str) -> ReplyKeyboardMarkup:
    items = DISTRICTS.get(region, ["Boshqa"])
    builder = ReplyKeyboardBuilder()
    for item in items:
        builder.add(KeyboardButton(text=item))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def phone_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def winner_keyboard(phone: str, full_name: str, invite_count: int) -> InlineKeyboardMarkup:
    cleaned = phone_for_tel_url(phone)
    share_text = (
        f"🎉 Aloofest random g'olibi!\n\n"
        f"👤 {full_name}\n"
        f"📞 {phone}\n"
        f"👥 Takliflar soni: {invite_count}"
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📞 Qo'ng'iroq qilish", url=f"tel:{cleaned}"),
        InlineKeyboardButton(
            text="📤 Ulashish",
            url=f"https://t.me/share/url?url=&text={share_text}"
        ),
    )
    return builder.as_markup()


def month_name_uz(month: int) -> str:
    names = {
        1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
        5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
        9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr",
    }
    return names[month]


def build_calendar(admin_id: int) -> InlineKeyboardMarkup:
    state = ADMIN_RANDOM_STATE.get(admin_id, RandomSelectionState())
    year = state.year
    month = state.month

    first_day = datetime(year, month, 1, tzinfo=TIMEZONE)
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=TIMEZONE)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=TIMEZONE)
    days_in_month = (next_month - first_day).days

    # Monday=1..Sunday=7
    first_weekday = first_day.isoweekday()

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️", callback_data="cal_prev"),
        InlineKeyboardButton(text=f"{month_name_uz(month)} {year}", callback_data="cal_ignore"),
        InlineKeyboardButton(text="▶️", callback_data="cal_next"),
    )

    week_head = ["Du", "Se", "Cho", "Pa", "Ju", "Sha", "Ya"]
    builder.row(*[InlineKeyboardButton(text=d, callback_data="cal_ignore") for d in week_head])

    row = []
    for _ in range(1, first_weekday):
        row.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))

    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        label = str(day)
        if state.start_date == date_str:
            label = f"🟢 {day}"
        elif state.end_date == date_str:
            label = f"🔴 {day}"

        row.append(InlineKeyboardButton(text=label, callback_data=f"cal_pick:{date_str}"))
        if len(row) == 7:
            builder.row(*row)
            row = []

    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))
        builder.row(*row)

    if state.start_date and state.end_date:
        builder.row(
            InlineKeyboardButton(
                text="🎯 G'olibni random orqali aniqlash",
                callback_data="random_draw"
            )
        )

    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="random_cancel")
    )

    return builder.as_markup()


async def send_or_edit_calendar(target, text: str, admin_id: int):
    kb = build_calendar(admin_id)
    if isinstance(target, Message):
        await target.answer(text, reply_markup=kb)
    elif isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=kb)


def admin_only(message: Message) -> bool:
    return message.from_user.id in ADMIN_IDS


# =========================
# START / MENU
# =========================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await upsert_basic_user(message.from_user.id, message.from_user.username)

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("ref_"):
        raw = parts[1].replace("ref_", "").strip()
        if raw.isdigit():
            referrer_id = int(raw)
            await set_referrer_if_empty(message.from_user.id, referrer_id)

    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=user_main_keyboard())


@router.message(F.text == "🏠 Asosiy menyu")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=user_main_keyboard())


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Sizda bu bo‘limga kirish huquqi yo‘q.")
        return
    await message.answer(ADMIN_PANEL_TEXT, reply_markup=admin_keyboard())


# =========================
# RULES / SUPPORT
# =========================
@router.message(F.text == "📜 Qoidalar")
async def show_rules(message: Message):
    await message.answer(RULES_TEXT)


@router.message(F.text == "📞 Yordam")
async def show_support(message: Message):
    await message.answer(SUPPORT_TEXT)


# =========================
# REGISTRATION
# =========================
@router.message(F.text == "🎉 Konkursda qatnashish")
async def start_registration(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    if user and user["full_name"] and user["phone"] and user["region"] and user["district"]:
        await message.answer(
            "✅ Siz allaqachon ro‘yxatdan o‘tgansiz.\n\n"
            "Do‘stlaringizni taklif qilishni davom ettirishingiz mumkin.",
            reply_markup=user_main_keyboard()
        )
        return

    await state.set_state(Registration.full_name)
    await message.answer(
        "📝 <b>Ro‘yxatdan o‘tish</b>\n\n"
        "Iltimos, <b>ism va familiyangizni</b> yuboring.",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(Registration.full_name)
async def registration_full_name(message: Message, state: FSMContext):
    full_name = (message.text or "").strip()
    if len(full_name.split()) < 2:
        await message.answer("Iltimos, ism va familiyangizni to‘liq kiriting.")
        return

    await save_full_name(message.from_user.id, full_name)
    await state.set_state(Registration.phone)
    await message.answer(
        "✅ <b>Tabriklaymiz!</b>\n"
        "Ma’lumotingiz qabul qilindi.\n\n"
        "Endi <b>telefon raqamingizni</b> yuboring:",
        reply_markup=phone_keyboard()
    )


@router.message(Registration.phone, F.contact)
async def registration_phone_contact(message: Message, state: FSMContext):
    if not message.contact or not message.contact.phone_number:
        await message.answer("Iltimos, tugma orqali telefon raqam yuboring.")
        return

    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    await save_phone(message.from_user.id, phone)
    await state.set_state(Registration.region)
    await message.answer(
        "📍 Endi <b>viloyatingizni</b> tanlang:",
        reply_markup=region_keyboard()
    )


@router.message(Registration.phone)
async def registration_phone_text(message: Message):
    await message.answer(
        "Iltimos, telefon raqamingizni tugma orqali yuboring.",
        reply_markup=phone_keyboard()
    )


@router.message(Registration.region)
async def registration_region(message: Message, state: FSMContext):
    region = (message.text or "").strip()
    if region not in REGIONS:
        await message.answer("Iltimos, viloyatni tugmalardan tanlang.")
        return

    await save_region(message.from_user.id, region)
    await state.update_data(region=region)
    await state.set_state(Registration.district)
    await message.answer(
        "🏙 Endi <b>tuman yoki shaharingizni</b> tanlang:",
        reply_markup=district_keyboard(region)
    )


@router.message(Registration.district)
async def registration_district(message: Message, state: FSMContext):
    district = (message.text or "").strip()
    data = await state.get_data()
    region = data.get("region")

    allowed = DISTRICTS.get(region, ["Boshqa"])
    if district not in allowed:
        await message.answer("Iltimos, tuman yoki shaharni tugmalardan tanlang.")
        return

    if district == "Boshqa":
        await state.set_state(Registration.other_district)
        await message.answer(
            "✍️ Tuman yoki shaharingiz nomini qo‘lda kiriting:",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    await complete_registration(message.from_user.id, district, message.from_user.username)
    await state.clear()
    await message.answer(REGISTRATION_DONE_TEXT, reply_markup=user_main_keyboard())


@router.message(Registration.other_district)
async def registration_other_district(message: Message, state: FSMContext):
    district = (message.text or "").strip()
    if len(district) < 2:
        await message.answer("Iltimos, tuman yoki shahar nomini to‘g‘ri kiriting.")
        return

    await complete_registration(message.from_user.id, district, message.from_user.username)
    await state.clear()
    await message.answer(REGISTRATION_DONE_TEXT, reply_markup=user_main_keyboard())


# =========================
# USER PROFILE / INVITE / STATUS
# =========================
@router.message(F.text == "👤 Mening profilim")
async def my_profile(message: Message, bot: Bot):
    user = await get_user(message.from_user.id)
    if not user or not user["full_name"]:
        await message.answer(
            "ℹ️ Siz hali ro‘yxatdan o‘tmagansiz.\n\n"
            "Davom etish uchun <b>🎉 Konkursda qatnashish</b> tugmasini bosing."
        )
        return

    subscribed = await is_user_subscribed(bot, message.from_user.id)
    random_status = "✅ Qatnashyapsiz" if (user["referred_count"] >= 3 and subscribed) else "⏳ Shart bajarilmagan"

    await message.answer(
        f"👤 <b>Mening profilim</b>\n\n"
        f"📝 Ism-familiya: <b>{esc(user['full_name'])}</b>\n"
        f"📞 Telefon: <b>{esc(user['phone'])}</b>\n"
        f"📍 Viloyat: <b>{esc(user['region'])}</b>\n"
        f"🏙 Tuman/Shahar: <b>{esc(user['district'])}</b>\n"
        f"👥 Takliflar soni: <b>{user['referred_count']}</b>\n"
        f"🎲 Random holati: <b>{random_status}</b>"
    )


@router.message(F.text == "🔗 Do'st taklif qilish")
async def invite_friends(message: Message, bot: Bot):
    user = await get_user(message.from_user.id)
    if not user or not user["full_name"]:
        await message.answer(
            "Avval ro‘yxatdan o‘ting, keyin do‘st taklif qilish havolasi chiqadi."
        )
        return

    link = await build_invite_link(bot, message.from_user.id)
    await message.answer(
        f"🔗 <b>Sizning maxsus taklif havolangiz:</b>\n\n"
        f"{link}\n\n"
        f"Do‘stlaringiz shu havola orqali botga kirib ro‘yxatdan o‘tsa, hisobingizga yoziladi. 🚀"
    )


@router.message(F.text == "🎲 Random holati")
async def random_status(message: Message, bot: Bot):
    user = await get_user(message.from_user.id)
    if not user or not user["full_name"]:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    subscribed = await is_user_subscribed(bot, message.from_user.id)
    count = user["referred_count"]

    if count >= 3 and subscribed:
        await message.answer(
            f"✅ Siz random o‘yinda qatnashish uchun barcha shartlarni bajargansiz.\n\n"
            f"👥 Taklif qilgan do‘stlaringiz: <b>{count}</b>\n"
            f"📡 Kanal obunasi: <b>tasdiqlandi</b>"
        )
    else:
        left = max(0, 3 - count)
        sub_text = "✅" if subscribed else "❌"
        await message.answer(
            f"🎲 <b>Random holati</b>\n\n"
            f"👥 Taklif qilgan do‘stlaringiz: <b>{count}</b>\n"
            f"📡 Kanal obunasi: <b>{sub_text}</b>\n\n"
            f"Randomga to‘liq qatnashish uchun yana <b>{left}</b> ta do‘st taklif qilishingiz kerak."
        )


@router.message(F.text == "🏆 TOP 5")
async def top_5(message: Message):
    top_users = await get_top_users(5)
    if not top_users:
        await message.answer("Hozircha TOP 5 ro‘yxati shakllanmagan.")
        return

    lines = ["🏆 <b>TOP 5 yetakchilar</b>\n"]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for idx, user in enumerate(top_users, start=1):
        lines.append(
            f"{medals[idx-1]} <b>{esc(user['full_name'])}</b> — "
            f"<b>{user['referred_count']}</b> ta taklif"
        )
    await message.answer("\n".join(lines))


# =========================
# ADMIN STATS
# =========================
@router.message(F.text == "📊 Statistika")
async def admin_stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    stats = await get_stats()
    now_str = datetime.now(TIMEZONE).strftime("%d.%m.%Y %H:%M")
    await message.answer(
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Umumiy foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"✅ To‘liq ro‘yxatdan o‘tganlar: <b>{stats['registered_users']}</b>\n"
        f"🔗 Umumiy takliflar: <b>{stats['referrals']}</b>\n\n"
        f"🕒 Yangilangan vaqt: <b>{now_str}</b>"
    )


@router.message(F.text == "🏆 TOP 5 admin")
async def admin_top5(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await top_5(message)


# =========================
# ADMIN RANDOM
# =========================
@router.message(F.text == "🎲 Random o'yin")
async def admin_random_menu(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    ADMIN_RANDOM_STATE[message.from_user.id] = RandomSelectionState()
    await send_or_edit_calendar(
        message,
        "📅 <b>Random o‘yin</b>\n\nAvval <b>boshlanish sanasi</b>ni tanlang:",
        message.from_user.id
    )


@router.callback_query(F.data == "cal_ignore")
async def calendar_ignore(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "cal_prev")
async def calendar_prev(callback: CallbackQuery):
    admin_id = callback.from_user.id
    state = ADMIN_RANDOM_STATE.get(admin_id, RandomSelectionState())
    if state.month == 1:
        state.month = 12
        state.year -= 1
    else:
        state.month -= 1
    ADMIN_RANDOM_STATE[admin_id] = state
    await send_or_edit_calendar(
        callback,
        "📅 Sana tanlang:",
        admin_id
    )
    await callback.answer()


@router.callback_query(F.data == "cal_next")
async def calendar_next(callback: CallbackQuery):
    admin_id = callback.from_user.id
    state = ADMIN_RANDOM_STATE.get(admin_id, RandomSelectionState())
    if state.month == 12:
        state.month = 1
        state.year += 1
    else:
        state.month += 1
    ADMIN_RANDOM_STATE[admin_id] = state
    await send_or_edit_calendar(
        callback,
        "📅 Sana tanlang:",
        admin_id
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cal_pick:"))
async def calendar_pick(callback: CallbackQuery):
    admin_id = callback.from_user.id
    if admin_id not in ADMIN_IDS:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    date_str = callback.data.split(":", 1)[1]
    state = ADMIN_RANDOM_STATE.get(admin_id, RandomSelectionState())

    if not state.start_date:
        state.start_date = date_str
        ADMIN_RANDOM_STATE[admin_id] = state
        await send_or_edit_calendar(
            callback,
            f"✅ Boshlanish sana tanlandi: <b>{state.start_date}</b>\n\n"
            f"Endi <b>tugash sanasi</b>ni tanlang:",
            admin_id
        )
        await callback.answer("Boshlanish sana tanlandi")
        return

    if not state.end_date:
        if date_str < state.start_date:
            await callback.answer(
                "Tugash sana boshlanish sanadan oldin bo‘lishi mumkin emas.",
                show_alert=True
            )
            return

        state.end_date = date_str
        ADMIN_RANDOM_STATE[admin_id] = state
        await send_or_edit_calendar(
            callback,
            f"✅ Boshlanish sana: <b>{state.start_date}</b>\n"
            f"✅ Tugash sana: <b>{state.end_date}</b>\n\n"
            f"Endi <b>G'olibni random orqali aniqlash</b> tugmasini bosing.",
            admin_id
        )
        await callback.answer("Tugash sana tanlandi")
        return

    # qayta bosilsa startni yangidan o'rnatadi
    state.start_date = date_str
    state.end_date = None
    ADMIN_RANDOM_STATE[admin_id] = state
    await send_or_edit_calendar(
        callback,
        f"✅ Yangi boshlanish sana: <b>{state.start_date}</b>\n\n"
        f"Endi tugash sanasini tanlang:",
        admin_id
    )
    await callback.answer("Boshlanish sana yangilandi")


@router.callback_query(F.data == "random_cancel")
async def random_cancel(callback: CallbackQuery):
    admin_id = callback.from_user.id
    if admin_id in ADMIN_RANDOM_STATE:
        del ADMIN_RANDOM_STATE[admin_id]

    await callback.message.edit_text("❌ Random o‘yin bekor qilindi.")
    await callback.answer("Bekor qilindi")


@router.callback_query(F.data == "random_draw")
async def random_draw(callback: CallbackQuery, bot: Bot):
    admin_id = callback.from_user.id
    if admin_id not in ADMIN_IDS:
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    state = ADMIN_RANDOM_STATE.get(admin_id)
    if not state or not state.start_date or not state.end_date:
        await callback.answer("Avval sana oralig‘ini to‘liq tanlang.", show_alert=True)
        return

    participants = await get_eligible_users_for_random(state.start_date, state.end_date)

    # kanal obunasi bo'yicha filtr
    final_participants = []
    for item in participants:
        if await is_user_subscribed(bot, item["user_id"]):
            final_participants.append(item)

    if not final_participants:
        await callback.message.edit_text(
            f"😔 <b>Natija topilmadi</b>\n\n"
            f"{state.start_date} dan {state.end_date} gacha bo‘lgan davrda "
            f"3+ do‘st taklif qilgan va <b>@{CHANNEL_USERNAME}</b> kanaliga obuna bo‘lgan ishtirokchilar topilmadi."
        )
        await callback.answer("Ishtirokchi topilmadi")
        return

    await callback.answer("Random ishga tushdi")

    # 45 sekundlik loading
    loading_message = await callback.message.edit_text(
        "🎲 <b>Random orqali g‘olib aniqlanmoqda...</b>\n\n"
        "⏳ Loading: <b>0%</b>"
    )

    progress_values = list(range(0, 101, 5))  # 0..100
    total_duration = 45
    sleep_time = total_duration / max(1, (len(progress_values) - 1))

    for p in progress_values[1:]:
        await asyncio.sleep(sleep_time)
        try:
            await loading_message.edit_text(
                "🎲 <b>Random orqali g‘olib aniqlanmoqda...</b>\n\n"
                f"⏳ Loading: <b>{p}%</b>"
            )
        except TelegramBadRequest:
            pass

    winner = random.choice(final_participants)

    await save_random_draw(
        winner_user_id=winner["user_id"],
        start_ts=winner["start_ts"],
        end_ts=winner["end_ts"],
        participant_count=len(final_participants),
        admin_id=admin_id,
    )

    text = (
        "🏆 <b>G‘olib aniqlandi!</b>\n\n"
        f"👤 Ism-familiya: <b>{esc(winner['full_name'])}</b>\n"
        f"📞 Telefon: <b>{esc(winner['phone'])}</b>\n"
        f"📍 Hudud: <b>{esc(winner['region'])}, {esc(winner['district'])}</b>\n"
        f"👥 Takliflar soni: <b>{winner['invite_count']}</b>\n\n"
        f"📆 Davr: <b>{state.start_date}</b> — <b>{state.end_date}</b>\n"
        f"👤 Ishtirokchilar soni: <b>{len(final_participants)}</b>"
    )

    await loading_message.edit_text(
        text,
        reply_markup=winner_keyboard(
            phone=winner["phone"],
            full_name=winner["full_name"],
            invite_count=winner["invite_count"],
        )
    )

    try:
        await bot.send_message(
            winner["user_id"],
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            "Siz Aloofest random o‘yinida g‘olib bo‘ldingiz.\n"
            "Tez orada siz bilan bog‘lanamiz. 📞"
        )
    except Exception:
        pass

    ADMIN_RANDOM_STATE.pop(admin_id, None)


# =========================
# FALLBACKS
# =========================
@router.message()
async def fallback_handler(message: Message):
    await message.answer(
        "Kerakli bo‘limni menyudan tanlang.",
        reply_markup=user_main_keyboard()
    )


# =========================
# MAIN
# =========================
async def main():
    await init_db()

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(router)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
