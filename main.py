from __future__ import annotations

import asyncio
import io
import logging
import random
import time
from dataclasses import dataclass

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from openpyxl import Workbook

from config import ADMIN_IDS, BOT_TOKEN, CHANNEL_USERNAME, CHANNEL_URL, SHOP_BOT_USERNAME
from database import db
from keyboards import (
    admin_menu,
    main_menu,
    profile_actions_keyboard,
    register_keyboard,
    subscribe_keyboard,
    support_menu,
    winner_keyboard,
)
from referral_card import generate_referral_card
from web_server import setup_web_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

router = Router()


class SupportState(StatesGroup):
    waiting_message = State()


class BroadcastState(StatesGroup):
    waiting_message = State()


class SearchState(StatesGroup):
    waiting_query = State()


@dataclass
class RandomPicker:
    start_date: str | None = None
    end_date: str | None = None
    year: int = time.localtime().tm_year
    month: int = time.localtime().tm_mon


RANDOM_STATE: dict[int, RandomPicker] = {}


def esc(value: str | None) -> str:
    import html
    return html.escape(value or "")


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def check_channel_subscription(user_id: int) -> bool:
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


async def get_invite_link(bot: Bot, user_id: int) -> str:
    me = await bot.get_me()
    return f"https://t.me/{me.username}?start=ref_{user_id}"


# =========================
# START
# =========================
@router.message(CommandStart())
async def start_handler(message: Message):
    await db.add_or_touch_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        tg_first_name=message.from_user.first_name
    )

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("ref_"):
        ref = parts[1].replace("ref_", "").strip()
        if ref.isdigit():
            await db.set_referrer_if_empty(message.from_user.id, int(ref))

    text = (
        "🎉 <b>aloo konkurs botiga xush kelibsiz!</b>\n\n"
        "Bu bot orqali siz konkursda qatnashishingiz, "
        "do‘stlaringizni taklif qilib 💎 ball yig‘ishingiz, "
        "top rankingga kirishingiz va random g‘oliblari qatoridan joy olishingiz mumkin.\n\n"
        "Quyidagi menyudan kerakli bo‘limni tanlang."
    )
    await message.answer(text, reply_markup=main_menu())


@router.message(Command("admin"))
async def admin_panel_handler(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Sizda bu bo‘limga kirish huquqi yo‘q.")
        return
    await message.answer("🛠 <b>Admin panel</b>", reply_markup=admin_menu())


@router.message(F.text == "🏠 Asosiy menyu")
async def back_main_handler(message: Message):
    await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=main_menu())


# =========================
# CONTEST ENTRY
# =========================
@router.message(F.text == "🎉 Konkursda qatnashish")
async def contest_handler(message: Message):
    user = await db.get_user(message.from_user.id)
    if user and user["is_registered"] == 1:
        await message.answer(
            "✅ <b>Siz allaqachon ro‘yxatdan o‘tgansiz.</b>\n\n"
            "Endi do‘stlaringizni taklif qilib 💎 ball yig‘ishingiz mumkin.",
            reply_markup=profile_actions_keyboard(message.from_user.id)
        )
        return

    text = (
        "📌 <b>Botdan foydalanish uchun quyidagilarni bajaring:</b>\n\n"
        "1️⃣ Kanalga a’zo bo‘ling\n"
        "2️⃣ Botga /start bosing\n\n"
        "Barchasini bajarganingizdan so‘ng <b>✅ Tekshirish</b> tugmasini bosing."
    )
    await message.answer(text, reply_markup=subscribe_keyboard())


@router.callback_query(F.data == "check_sub")
async def check_sub_handler(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if user and user["is_registered"] == 1:
        await callback.message.answer(
            "✅ Siz ro‘yxatdan o‘tib bo‘lgansiz.",
            reply_markup=profile_actions_keyboard(callback.from_user.id)
        )
        await callback.answer()
        return

    is_subscribed = await check_channel_subscription(callback.from_user.id)
    if not is_subscribed:
        await callback.message.answer(
            f"❌ Siz hali <b>@{CHANNEL_USERNAME}</b> kanaliga a’zo bo‘lmagansiz.\n\n"
            f"Avval kanalga qo‘shilib, keyin yana <b>✅ Tekshirish</b> tugmasini bosing.",
            reply_markup=subscribe_keyboard()
        )
        await callback.answer("Obuna topilmadi", show_alert=True)
        return

    await callback.message.answer(
        "✅ <b>Zo‘r, obuna tasdiqlandi!</b>\n\n"
        "Endi konkurs ishtirokchisi bo‘lish uchun ro‘yxatdan o‘ting.",
        reply_markup=register_keyboard(callback.from_user.id)
    )
    await callback.answer("Tasdiqlandi")


@router.callback_query(F.data == "my_invite_link")
async def my_invite_link_handler(callback: CallbackQuery, bot: Bot):
    link = await get_invite_link(bot, callback.from_user.id)
    await callback.message.answer(
        f"🔗 <b>Sizning maxsus taklif havolangiz:</b>\n\n{link}\n\n"
        f"Har bir muvaffaqiyatli referal uchun sizga <b>+5 💎</b> yoziladi."
    )
    await callback.answer()


# =========================
# PROFILE / POINTS
# =========================
@router.message(F.text == "ℹ️ Mening profilim")
async def my_profile_handler(message: Message):
    user = await db.get_user(message.from_user.id)
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


@router.message(F.text == "💎 Mening ballarim")
async def my_points_handler(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or user["is_registered"] != 1:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    await message.answer(
        f"💎 <b>Mening ballarim</b>\n\n"
        f"Jami ball: <b>{user['diamonds']} 💎</b>\n"
        f"Taklif qilgan do‘stlar: <b>{user['referral_count']}</b>\n\n"
        f"Ro‘yxatdan o‘tganda: <b>+5 💎</b>\n"
        f"Har bir referal uchun: <b>+5 💎</b>"
    )


@router.message(F.text == "📊 Mening o‘rnim")
async def my_rank_handler(message: Message):
    rank_data = await db.get_user_rank(message.from_user.id)
    if not rank_data:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    await message.answer(
        f"📊 <b>Mening o‘rnim</b>\n\n"
        f"🏅 O‘rin: <b>{rank_data['rank']}</b> / <b>{rank_data['total']}</b>\n"
        f"💎 Ball: <b>{rank_data['diamonds']}</b>"
    )


@router.message(F.text == "💎 Ball tarixi")
async def diamond_history_handler(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or user["is_registered"] != 1:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    rows = await db.get_diamond_history(message.from_user.id)
    if not rows:
        await message.answer("💎 Ball tarixingiz hozircha bo‘sh.")
        return

    lines = ["💎 <b>Ball tarixi</b>\n"]
    for row in rows:
        sign = "+" if row["amount"] >= 0 else ""
        lines.append(f"{sign}{row['amount']} 💎 — {esc(row['reason'])}")
    await message.answer("\n".join(lines))


# =========================
# REFERRAL / CARD
# =========================
@router.message(F.text == "🔗 Do‘st taklif qilish")
async def invite_handler(message: Message, bot: Bot):
    user = await db.get_user(message.from_user.id)
    if not user or user["is_registered"] != 1:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    link = await get_invite_link(bot, message.from_user.id)
    await message.answer(
        f"🚀 <b>Do‘st taklif qilish havolangiz:</b>\n\n{link}\n\n"
        f"Har bir muvaffaqiyatli ro‘yxatdan o‘tgan referal uchun <b>+5 💎</b> olasiz."
    )


@router.message(F.text == "🪪 Referral card")
async def referral_card_handler(message: Message, bot: Bot):
    user = await db.get_user(message.from_user.id)
    if not user or user["is_registered"] != 1:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    link = await get_invite_link(bot, message.from_user.id)
    full_name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip() or "Foydalanuvchi"
    path = generate_referral_card(
        full_name=full_name,
        diamonds=user["diamonds"],
        referral_count=user["referral_count"],
        invite_link=link
    )

    with open(path, "rb") as f:
        await message.answer_photo(
            BufferedInputFile(f.read(), filename="referral_card.png"),
            caption="🪪 Sizning referral card'ingiz"
        )


# =========================
# RANKING / PRIZES / RANDOM HISTORY
# =========================
@router.message(F.text == "🏆 Top ranking")
async def top_ranking_handler(message: Message):
    rows = await db.get_top_users(10)
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


@router.message(F.text == "🎁 Sovg‘alar")
async def prizes_handler(message: Message):
    rows = await db.get_prizes()
    if not rows:
        await message.answer("Sovg‘alar hali kiritilmagan.")
        return

    lines = ["🎁 <b>aloofest sovg‘alari</b>\n"]
    for row in rows:
        lines.append(
            f"{esc(row['place_name'])} — <b>{esc(row['prize_title'])}</b>\n"
            f"{esc(row['prize_description'] or '')}\n"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == "🕘 Random tarixi")
async def random_history_handler(message: Message):
    rows = await db.get_random_history(15)
    if not rows:
        await message.answer("Hozircha random tarixi yo‘q.")
        return

    lines = ["🕘 <b>Random g‘oliblar tarixi</b>\n"]
    for idx, row in enumerate(rows, start=1):
        dt = time.strftime("%d.%m.%Y %H:%M", time.localtime(row["created_at"]))
        lines.append(
            f"{idx}. <b>{esc(row['winner_name'])}</b>\n"
            f"📞 {esc(row['winner_phone'] or '')}\n"
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
    await message.answer(
        "📞 <b>Bog‘lanish</b>\n\n"
        "Iltimos, savolingiz yoki xabaringizni yuboring.\n"
        "Xabaringiz adminlarga jo‘natiladi.\n\n"
        "Chiqish uchun <b>❌ Yakunlash</b> tugmasini bosing.",
        reply_markup=support_menu()
    )


@router.message(F.text == "❌ Yakunlash")
async def support_end_handler(message: Message, state: FSMContext):
    if await state.get_state() == SupportState.waiting_message:
        await state.clear()
        await message.answer("✅ Bog‘lanish bo‘limidan chiqdingiz.", reply_markup=main_menu())


@router.message(SupportState.waiting_message)
async def support_message_handler(message: Message, state: FSMContext, bot: Bot):
    user = await db.get_user(message.from_user.id)
    full_name = (
        f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
        if user and user["first_name"]
        else (user["tg_first_name"] if user else "Noma’lum")
    )

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
            await db.save_support_thread(admin_id, sent.message_id, message.from_user.id, user_text)
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
    mapping = await db.get_support_thread(message.from_user.id, reply_to.message_id)
    if not mapping:
        return

    answer_text = message.text or message.caption or "[Javob]"
    out = (
        "📞 <b>Admin javobi</b>\n\n"
        f"📝 <b>Sizning savolingiz:</b>\n{esc(mapping['user_text'])}\n\n"
        f"💬 <b>Admin javobi:</b>\n{esc(answer_text)}"
    )

    try:
        await bot.send_message(mapping["user_id"], out)
        await message.reply("✅ Javob yuborildi.")
    except Exception as e:
        await message.reply(f"❌ Yuborilmadi: {e}")


# =========================
# ADMIN
# =========================
@router.message(F.text == "📊 Statistika")
async def stats_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    s = await db.get_stats()
    await message.answer(
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{s['total_users']}</b>\n"
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
    await state.set_state(BroadcastState.waiting_message)
    await message.answer(
        "📣 Hamma foydalanuvchilarga yubormoqchi bo‘lgan xabaringizni yuboring.\n\n"
        "Bekor qilish uchun /cancel yozing."
    )


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer(
            "✅ Bekor qilindi.",
            reply_markup=admin_menu() if is_admin(message.from_user.id) else main_menu()
        )


@router.message(BroadcastState.waiting_message)
async def broadcast_send_handler(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    users = await db.get_all_users()
    sent_count = 0
    failed_count = 0

    status_msg = await message.answer("⏳ Broadcast yuborilmoqda...")

    for row in users:
        try:
            await bot.copy_message(
                chat_id=row["user_id"],
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            sent_count += 1
        except Exception:
            failed_count += 1

    await state.clear()
    await status_msg.edit_text(
        f"✅ Broadcast yakunlandi.\n\n"
        f"📤 Yuborildi: <b>{sent_count}</b>\n"
        f"❌ Xato: <b>{failed_count}</b>"
    )
    await message.answer("🛠 Admin panel", reply_markup=admin_menu())


@router.message(F.text == "🔎 User qidirish")
async def search_start_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(SearchState.waiting_query)
    await message.answer("🔎 User ID, username yoki telefon kiriting.")


@router.message(SearchState.waiting_query)
async def search_query_handler(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    query = (message.text or "").strip()
    rows = await db.search_users(query)
    if not rows:
        await message.answer("Foydalanuvchi topilmadi.")
        return

    lines = ["🔎 <b>Qidiruv natijasi</b>\n"]
    for row in rows:
        full_name = f"{row['first_name'] or ''} {row['last_name'] or ''}".strip()
        lines.append(
            f"🆔 <code>{row['user_id']}</code>\n"
            f"👤 {esc(full_name) or esc(row['tg_first_name'])}\n"
            f"📞 {esc(row['phone'] or '')}\n"
            f"💎 {row['diamonds']} | 👥 {row['referral_count']}\n"
        )
    await message.answer("\n".join(lines[:20]))
    await state.clear()


@router.message(F.text == "📥 Excel export")
async def excel_export_handler(message: Message, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    rows = await db.get_all_users()
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"

    ws.append([
        "User ID", "Username", "Telegram Name", "Ism", "Familiya",
        "Telefon", "Viloyat", "Tuman", "Registered",
        "Diamonds", "Referral Count", "Referrer ID", "Joined At", "Registered At"
    ])

    for row in rows:
        joined_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row["joined_at"])) if row["joined_at"] else ""
        registered_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(row["registered_at"])) if row["registered_at"] else ""
        ws.append([
            row["user_id"],
            row["username"] or "",
            row["tg_first_name"] or "",
            row["first_name"] or "",
            row["last_name"] or "",
            row["phone"] or "",
            row["region"] or "",
            row["district"] or "",
            "ha" if row["is_registered"] else "yo‘q",
            row["diamonds"],
            row["referral_count"],
            row["referrer_id"] or "",
            joined_at,
            registered_at,
        ])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    await bot.send_document(
        message.chat.id,
        BufferedInputFile(buffer.read(), filename="aloo_users.xlsx"),
        caption="📥 Foydalanuvchilar eksporti"
    )


# =========================
# RANDOM
# =========================
def month_name(month: int) -> str:
    names = {
        1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel", 5: "May", 6: "Iyun",
        7: "Iyul", 8: "Avgust", 9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"
    }
    return names[month]


def build_calendar(admin_id: int):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    state = RANDOM_STATE.get(admin_id, RandomPicker())
    year, month = state.year, state.month

    import calendar
    month_data = calendar.monthcalendar(year, month)

    keyboard = [
        [
            InlineKeyboardButton(text="◀️", callback_data="cal_prev"),
            InlineKeyboardButton(text=f"{month_name(month)} {year}", callback_data="cal_ignore"),
            InlineKeyboardButton(text="▶️", callback_data="cal_next"),
        ],
        [
            InlineKeyboardButton(text="Du", callback_data="cal_ignore"),
            InlineKeyboardButton(text="Se", callback_data="cal_ignore"),
            InlineKeyboardButton(text="Cho", callback_data="cal_ignore"),
            InlineKeyboardButton(text="Pa", callback_data="cal_ignore"),
            InlineKeyboardButton(text="Ju", callback_data="cal_ignore"),
            InlineKeyboardButton(text="Sha", callback_data="cal_ignore"),
            InlineKeyboardButton(text="Ya", callback_data="cal_ignore"),
        ],
    ]

    for week in month_data:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                label = str(day)
                if state.start_date == date_str:
                    label = f"🟢 {day}"
                elif state.end_date == date_str:
                    label = f"🔴 {day}"
                row.append(InlineKeyboardButton(text=label, callback_data=f"cal_pick:{date_str}"))
        keyboard.append(row)

    if state.start_date and state.end_date:
        keyboard.append([InlineKeyboardButton(text="🎯 G‘olibni random orqali aniqlash", callback_data="random_draw")])

    keyboard.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="random_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(F.text == "🎲 Random o‘yin")
async def random_start_handler(message: Message):
    if not is_admin(message.from_user.id):
        return

    RANDOM_STATE[message.from_user.id] = RandomPicker()
    await message.answer(
        "📅 <b>Random o‘yin</b>\n\n"
        "Avval boshlanish sanasini tanlang:",
        reply_markup=build_calendar(message.from_user.id)
    )


@router.callback_query(F.data == "cal_ignore")
async def cal_ignore_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "cal_prev")
async def cal_prev_handler(callback: CallbackQuery):
    state = RANDOM_STATE.get(callback.from_user.id, RandomPicker())
    if state.month == 1:
        state.month = 12
        state.year -= 1
    else:
        state.month -= 1
    RANDOM_STATE[callback.from_user.id] = state
    await callback.message.edit_reply_markup(reply_markup=build_calendar(callback.from_user.id))
    await callback.answer()


@router.callback_query(F.data == "cal_next")
async def cal_next_handler(callback: CallbackQuery):
    state = RANDOM_STATE.get(callback.from_user.id, RandomPicker())
    if state.month == 12:
        state.month = 1
        state.year += 1
    else:
        state.month += 1
    RANDOM_STATE[callback.from_user.id] = state
    await callback.message.edit_reply_markup(reply_markup=build_calendar(callback.from_user.id))
    await callback.answer()


@router.callback_query(F.data.startswith("cal_pick:"))
async def cal_pick_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return

    picked = callback.data.split(":", 1)[1]
    state = RANDOM_STATE.get(callback.from_user.id, RandomPicker())

    if not state.start_date:
        state.start_date = picked
        RANDOM_STATE[callback.from_user.id] = state
        await callback.message.edit_text(
            f"✅ Boshlanish sana: <b>{state.start_date}</b>\n\n"
            "Endi tugash sanasini tanlang:",
            reply_markup=build_calendar(callback.from_user.id)
        )
        await callback.answer("Boshlanish sana tanlandi")
        return

    if not state.end_date:
        if picked < state.start_date:
            await callback.answer("Tugash sana boshlanish sanadan oldin bo‘lishi mumkin emas.", show_alert=True)
            return
        state.end_date = picked
        RANDOM_STATE[callback.from_user.id] = state
        await callback.message.edit_text(
            f"✅ Boshlanish sana: <b>{state.start_date}</b>\n"
            f"✅ Tugash sana: <b>{state.end_date}</b>\n\n"
            "Endi randomni ishga tushiring.",
            reply_markup=build_calendar(callback.from_user.id)
        )
        await callback.answer("Tugash sana tanlandi")
        return

    state.start_date = picked
    state.end_date = None
    RANDOM_STATE[callback.from_user.id] = state
    await callback.message.edit_text(
        f"✅ Yangi boshlanish sana: <b>{state.start_date}</b>\n\n"
        "Endi tugash sanasini tanlang:",
        reply_markup=build_calendar(callback.from_user.id)
    )
    await callback.answer("Boshlanish sana yangilandi")


@router.callback_query(F.data == "random_cancel")
async def random_cancel_handler(callback: CallbackQuery):
    RANDOM_STATE.pop(callback.from_user.id, None)
    await callback.message.edit_text("❌ Random o‘yin bekor qilindi.")
    await callback.answer()


@router.callback_query(F.data == "winner_phone")
async def winner_phone_handler(callback: CallbackQuery):
    await callback.answer("Telefon raqami yuqorida ko‘rsatilgan.", show_alert=True)


@router.callback_query(F.data == "random_draw")
async def random_draw_handler(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return

    state = RANDOM_STATE.get(callback.from_user.id)
    if not state or not state.start_date or not state.end_date:
        await callback.answer("Avval sana oralig‘ini tanlang.", show_alert=True)
        return

    candidates = await db.get_random_candidates(state.start_date, state.end_date)

    eligible = []
    for user in candidates:
        if await check_channel_subscription(user["user_id"]):
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
    full_name = f"{winner['first_name'] or ''} {winner['last_name'] or ''}".strip() or "Noma’lum"
    phone = winner["phone"] or "Telefon kiritilmagan"
    region = winner["region"] or "Viloyat kiritilmagan"
    district = winner["district"] or "Tuman kiritilmagan"
    diamonds = winner["diamonds"] or 0

    await db.save_random_history(
        winner_user_id=winner["user_id"],
        winner_name=full_name,
        winner_phone=phone,
        winner_region=region,
        winner_district=district,
        winner_diamonds=diamonds,
        start_date=state.start_date,
        end_date=state.end_date,
        participants_count=len(eligible),
        admin_id=callback.from_user.id
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

    await progress_msg.edit_text(
        winner_text,
        reply_markup=winner_keyboard(phone, full_name)
    )

    try:
        await bot.send_message(
            winner["user_id"],
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            "Siz aloo random o‘yinida g‘olib bo‘ldingiz.\n"
            "Tez orada siz bilan bog‘lanamiz."
        )
    except Exception:
        pass

    RANDOM_STATE.pop(callback.from_user.id, None)


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
    await db.init()
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
