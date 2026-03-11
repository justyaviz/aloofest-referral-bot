import asyncio
import io
import random
import calendar
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from openpyxl import Workbook

from config import (
    BOT_TOKEN,
    CHANNEL_USERNAME,
    ADMIN_IDS,
    INSTAGRAM_RULE_TEXT,
    INSTAGRAM_MAIN_URL,
)
from database import db
from keyboards import (
    start_keyboard,
    rules_keyboard,
    subscribe_keyboard,
    register_keyboard,
    after_registration_keyboard,
    main_menu,
    admin_menu,
    phone_keyboard,
)
from web_server import setup_web_server


bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


class BanState(StatesGroup):
    waiting_user = State()


class UnbanState(StatesGroup):
    waiting_user = State()


class SearchState(StatesGroup):
    waiting_query = State()


class DirectMessageState(StatesGroup):
    waiting_user = State()
    waiting_message = State()


class BroadcastState(StatesGroup):
    waiting_message = State()


class AdState(StatesGroup):
    waiting_title = State()
    waiting_body = State()


class PrizeState(StatesGroup):
    waiting_id = State()
    waiting_place = State()
    waiting_title = State()
    waiting_desc = State()


class RandomState(StatesGroup):
    waiting_start = State()
    waiting_end = State()
    ready_confirm = State()


START_TEXT = """
🎉 Kutib oling, “aloo”dan navbatdagi yirik yutuqli loyiha — <b>“aloofest” MEGA KONKURSI</b>!

Ushbu mega konkurs kirib kelayotgan <b>Ramazon Hayiti</b> munosabati bilan “aloo” tomonidan siz azizlar uchun hayitlik tuhfa sifatida tashkil etilmoqda. 💙

Sizda <b>2 xil usulda g‘olib bo‘lish</b> imkoniyati bor:

1️⃣ <b>TOP 3 mega konkurs</b>
2️⃣ <b>Haftalik random o‘yinlari</b>

🎁 <b>Hayit bayrami mega konkurs sovg‘alari:</b>

🥇 1-o‘rin — <b>Redmi Robot Mop 2</b>  
🥈 2-o‘rin — <b>Novey Senat SC1 Red</b> telefoni  
🥉 3-o‘rin — <b>Zamonaviy elektr choynak</b>

🎲 <b>Haftalik random o‘yinlari:</b>  
Har hafta davomida kamida <b>3+ do‘stingizni taklif qilib</b>, <b>15+ ball</b> to‘plash orqali random o‘yinida ishtirok eta olasiz.

Haftalik o‘yinlarda quyidagi qimmatbaho sovg‘alar o‘ynaladi:

• AirPods  
• Telefon  
• Smartwatch  
• Planshet  
• va boshqa qimmatbaho sovg‘alar

📅 G‘oliblar bot orqali hamda <b>@aloo_uzb</b> kanalida e’lon qilinadi.

🍀 Omad sizga yor bo‘lsin!
"""

RULES_TEXT = f"""
🏆 <b>“aloofest” MEGA KONKURSI qoidalari</b>

Ushbu konkursda g‘olib bo‘lishning <b>2 xil turi</b> mavjud:

1️⃣ <b>TOP 3 mega konkurs</b>  
2️⃣ <b>Haftalik random o‘yinlari</b>

🎯 <b>Ball tizimi:</b>  
Har bir taklif qilingan do‘st uchun sizga <b>+5 ball</b> beriladi.

Misollar:  
1 do‘st = 5 ball  
3 do‘st = 15 ball  
5 do‘st = 25 ball  
10 do‘st = 50 ball

🥇 <b>TOP 3 mega konkurs</b>  
Eng ko‘p ball to‘plagan ishtirokchilar hayit bayrami mega konkursining asosiy g‘oliblari bo‘ladi.

🎁 Sovg‘alar:  
1-o‘rin — Redmi Robot Mop 2  
2-o‘rin — Novey Senat SC1 Red telefoni  
3-o‘rin — Zamonaviy elektr choynak

🎲 <b>Haftalik random o‘yinlari</b>  
Har hafta davomida <b>kamida 3+ do‘st taklif qilib</b>, <b>15+ ball</b> to‘plagan ishtirokchilar random o‘yinida qatnasha oladi.

Haftalik random sovg‘alariga quyidagilar kiradi:  
• AirPods  
• Telefon  
• Smartwatch  
• Planshet  
• va boshqa qimmatbaho sovg‘alar

📋 <b>Ishtirok etish uchun:</b>  
• Telegram kanalga obuna bo‘ling  
• Ro‘yxatdan o‘ting  
• Do‘stlaringizni taklif qiling  
• Ball to‘plang va g‘olib bo‘ling

❗ Instagram bo‘yicha shartlar ham majburiy hisoblanadi. Agar ishtirokchi Instagram shartlarini bajarmagan bo‘lsa, g‘oliblik tasdiqlanmaydi.

📸 Instagram bo‘yicha shart:
{INSTAGRAM_RULE_TEXT}
"""

ABOUT_TEXT = f"""
ℹ️ <b>“aloofest” MEGA KONKURSI haqida</b>

“aloofest” — bu kirib kelayotgan <b>Ramazon Hayiti</b> munosabati bilan “aloo” tomonidan tashkil etilgan maxsus hayitlik mega konkursdir.

Bu konkursda siz 2 xil usulda g‘olib bo‘lishingiz mumkin:

1️⃣ <b>TOP 3 mega konkurs</b>  
Eng ko‘p ball to‘plagan ishtirokchilar asosiy hayit sovg‘alarini yutadi.

2️⃣ <b>Haftalik random o‘yinlari</b>  
Har hafta 3+ do‘st taklif qilib, 15+ ball yig‘ganlar random o‘yinida qatnashadi.

🎁 Sovg‘alar orasida:  
• Redmi Robot Mop 2  
• Novey Senat SC1 Red telefoni  
• Zamonaviy elektr choynak  
• AirPods  
• Telefon  
• Smartwatch  
• Planshet  
• va boshqa qimmatbaho sovg‘alar mavjud

📢 Barcha yangiliklar bot orqali va @aloo_uzb kanalida e’lon qilinadi.
"""

GUIDE_TEXT = """
🎉 <b>Tabriklaymiz!</b>

Siz “aloofest” mega konkursida muvaffaqiyatli ro‘yxatdan o‘tdingiz va boshlang‘ich <b>ball</b> qo‘lga kiritdingiz. ✅

📌 Endi keyingi bosqich juda muhim:  
quyidagi <b>qisqa yo‘riqnoma</b> orqali konkursda qanday qatnashish, ball yig‘ish va g‘olib bo‘lish tartibini ko‘rib chiqing.

🎯 Sizda 2 xil imkoniyat bor:  
• TOP 3 mega konkursda g‘olib bo‘lish  
• Haftalik random o‘yinlarida sovg‘a yutish

📹 <b>Qisqa yo‘riqnoma:</b>  
• konkursda qanday ishtirok etish  
• do‘st taklif qilib ball yig‘ish  
• TOP 3 ga chiqish  
• haftalik random o‘yinida qatnashish

👥 Endi do‘stlaringizni taklif qiling, ko‘proq ball yig‘ing va hayit oldidan “aloo”dan qimmatbaho sovg‘alarni yutib oling!

👇 Quyidagi menyular orqali davom eting
"""


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def is_channel_member(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


async def get_ref_link(user_id: int) -> str:
    me = await bot.get_me()
    return f"https://t.me/{me.username}?start=ref_{user_id}"


def parse_date_to_ts(text: str, end_of_day: bool = False) -> int | None:
    try:
        if end_of_day:
            dt = datetime.strptime(text + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.strptime(text, "%Y-%m-%d")
        return int(dt.timestamp())
    except Exception:
        return None


def build_calendar(year: int, month: int, prefix: str) -> InlineKeyboardMarkup:
    kb = []
    month_name = f"{year}-{month:02d}"
    kb.append([
        InlineKeyboardButton(text="◀️", callback_data=f"{prefix}:nav:{year}:{month}:prev"),
        InlineKeyboardButton(text=month_name, callback_data="noop"),
        InlineKeyboardButton(text="▶️", callback_data=f"{prefix}:nav:{year}:{month}:next"),
    ])
    kb.append([
        InlineKeyboardButton(text="Du", callback_data="noop"),
        InlineKeyboardButton(text="Se", callback_data="noop"),
        InlineKeyboardButton(text="Ch", callback_data="noop"),
        InlineKeyboardButton(text="Pa", callback_data="noop"),
        InlineKeyboardButton(text="Ju", callback_data="noop"),
        InlineKeyboardButton(text="Sh", callback_data="noop"),
        InlineKeyboardButton(text="Ya", callback_data="noop"),
    ])

    cal = calendar.monthcalendar(year, month)
    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
            else:
                row.append(
                    InlineKeyboardButton(
                        text=str(day),
                        callback_data=f"{prefix}:pick:{year}:{month}:{day}"
                    )
                )
        kb.append(row)

    return InlineKeyboardMarkup(inline_keyboard=kb)


@dp.message(CommandStart())
async def start_cmd(message: Message):
    await db.add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        tg_name=message.from_user.first_name
    )

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("ref_"):
        ref = parts[1].replace("ref_", "").strip()
        if ref.isdigit():
            await db.set_referrer_if_empty(message.from_user.id, int(ref))

    user = await db.get_user(message.from_user.id)
    if user and user["registered"]:
        if user["phone_verified"]:
            await message.answer(
                f"🎉 Xush kelibsiz, {user['full_name'] or user['tg_name']}!\n\n"
                f"Quyidagi menyulardan foydalaning 👇",
                reply_markup=main_menu()
            )
        else:
            await message.answer(
                "📱 Ro‘yxatdan o‘tish yakunlanishi uchun telefon raqamingizni ulashing.",
                reply_markup=phone_keyboard()
            )
        return

    await message.answer(START_TEXT, reply_markup=start_keyboard())


@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Siz admin emassiz.")
        return
    await message.answer("🛠 <b>Admin panel</b>", reply_markup=admin_menu())


@dp.message(Command("seedtest"))
async def seed_test(message: Message):
    if not is_admin(message.from_user.id):
        return
    await db.seed_test_random_users()
    await message.answer(
        "✅ Test random userlar tayyorlandi:\n"
        "• 8124320409\n"
        "• 7803701344\n"
        "• FEST-002\n"
        "hammasiga 25 ball va 5 referal berildi."
    )


@dp.message(Command("addball"))
async def add_ball(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()

    if len(parts) != 3:
        await message.answer(
            "❌ Format noto‘g‘ri.\n\n"
            "To‘g‘ri format:\n"
            "/addball USER_ID BALL\n\n"
            "Misol:\n"
            "/addball 8124320409 50"
        )
        return

    user_id_raw = parts[1].strip()
    points_raw = parts[2].strip()

    if not user_id_raw.isdigit() or not points_raw.lstrip("-").isdigit():
        await message.answer("❌ USER_ID va BALL raqam bo‘lishi kerak.")
        return

    user_id = int(user_id_raw)
    points = int(points_raw)

    user = await db.get_user(user_id)
    if not user:
        await message.answer("❌ User topilmadi.")
        return

    await db.add_points(user_id, points)
    updated_user = await db.get_user(user_id)

    await message.answer(
        f"✅ Ball qo‘shildi.\n\n"
        f"🆔 User: {user_id}\n"
        f"👤 Ism: {updated_user['full_name'] or updated_user['tg_name'] or updated_user['username'] or '-'}\n"
        f"💎 Qo‘shildi: {points}\n"
        f"💎 Jami: {updated_user['diamonds']}"
    )


@dp.message(Command("addref"))
async def add_ref(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()

    if len(parts) != 3:
        await message.answer(
            "❌ Format noto‘g‘ri.\n\n"
            "To‘g‘ri format:\n"
            "/addref USER_ID REF_SONI\n\n"
            "Misol:\n"
            "/addref 8124320409 3"
        )
        return

    user_id_raw = parts[1].strip()
    refs_raw = parts[2].strip()

    if not user_id_raw.isdigit() or not refs_raw.isdigit():
        await message.answer("❌ USER_ID va REF_SONI raqam bo‘lishi kerak.")
        return

    user_id = int(user_id_raw)
    refs = int(refs_raw)

    user = await db.get_user(user_id)
    if not user:
        await message.answer("❌ User topilmadi.")
        return

    await db.add_referrals(user_id, refs)
    updated_user = await db.get_user(user_id)

    await message.answer(
        f"✅ Referral qo‘shildi.\n\n"
        f"🆔 User: {user_id}\n"
        f"👤 Ism: {updated_user['full_name'] or updated_user['tg_name'] or updated_user['username'] or '-'}\n"
        f"👥 Qo‘shildi: {refs}\n"
        f"👥 Jami: {updated_user['referral_count']}"
    )


@dp.message(Command("setready"))
async def set_ready(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = (message.text or "").split()

    if len(parts) != 4:
        await message.answer(
            "❌ Format noto‘g‘ri.\n\n"
            "To‘g‘ri format:\n"
            "/setready USER_ID BALL REF\n\n"
            "Misol:\n"
            "/setready 8124320409 25 5"
        )
        return

    user_id_raw = parts[1].strip()
    diamonds_raw = parts[2].strip()
    refs_raw = parts[3].strip()

    if not user_id_raw.isdigit() or not diamonds_raw.isdigit() or not refs_raw.isdigit():
        await message.answer("❌ USER_ID, BALL va REF raqam bo‘lishi kerak.")
        return

    user_id = int(user_id_raw)
    diamonds = int(diamonds_raw)
    refs = int(refs_raw)

    user = await db.get_user(user_id)
    if not user:
        await message.answer("❌ User topilmadi.")
        return

    await db.set_ready_user(user_id, diamonds, refs)
    updated_user = await db.get_user(user_id)

    await message.answer(
        f"✅ User random uchun tayyorlandi.\n\n"
        f"🆔 User: {user_id}\n"
        f"👤 Ism: {updated_user['full_name'] or updated_user['tg_name'] or updated_user['username'] or '-'}\n"
        f"💎 Ball: {updated_user['diamonds']}\n"
        f"👥 Referral: {updated_user['referral_count']}\n"
        f"✅ Registered: {updated_user['registered']}"
    )


@dp.callback_query(F.data == "open_main_menu")
async def open_main_menu(call: CallbackQuery):
    user = await db.get_user(call.from_user.id)
    if not user or not user["registered"]:
        await call.message.answer("Avval ro‘yxatdan o‘ting.")
        await call.answer()
        return

    if not user["phone_verified"]:
        await call.message.answer(
            "📱 Endi ro‘yxatdan o‘tish jarayonini yakunlash uchun telefon raqamingizni ulashing.",
            reply_markup=phone_keyboard()
        )
        await call.answer("Raqamni ulashing")
        return

    await call.message.answer(GUIDE_TEXT, reply_markup=main_menu())
    await call.answer("Menyu ochildi")


@dp.message(F.contact)
async def save_contact(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user["registered"]:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    phone = message.contact.phone_number
    await db.save_phone(message.from_user.id, phone)

    await message.answer(
        GUIDE_TEXT,
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "join_now")
async def join_now(call: CallbackQuery):
    await call.message.answer(
        "1️⃣ Birinchi qadam: konkurs shartlari bilan tanishing 👇",
        reply_markup=rules_keyboard()
    )
    await call.answer()


@dp.callback_query(F.data == "show_rules")
async def show_rules(call: CallbackQuery):
    await call.message.answer(
        RULES_TEXT + "\n\n"
        "Davom etish uchun quyidagilarni bajaring:\n"
        "• Telegram kanalga obuna bo‘ling\n"
        "• Instagram profilga o‘ting\n"
        "• online do‘kon botga /start bosing\n"
        "• so‘ng Tekshirish tugmasini bosing",
        reply_markup=subscribe_keyboard()
    )
    await call.answer()


@dp.callback_query(F.data == "check_subscription")
async def check_subscription(call: CallbackQuery):
    if not await is_channel_member(call.from_user.id):
        await call.message.answer(
            f"❌ Siz hali <b>@{CHANNEL_USERNAME}</b> kanaliga obuna bo‘lmagansiz.\n"
            "Avval obuna bo‘ling, keyin qayta tekshiring.",
            reply_markup=subscribe_keyboard()
        )
        await call.answer("Obuna topilmadi", show_alert=True)
        return

    await call.message.answer(
        "✅ Zo‘r, Telegram obunangiz tasdiqlandi!\n\n"
        "Endi konkurs ishtirokchisi bo‘lish uchun ro‘yxatdan o‘ting 👇\n\n"
        "❗ Eslatma: Instagramdagi obuna ham majburiy hisoblanadi. "
        "Agar Instagram shartlari bajarilmagan bo‘lsa, g‘oliblik tasdiqlanmaydi.",
        reply_markup=register_keyboard(call.from_user.id)
    )
    await call.answer("Tasdiqlandi")


@dp.message(F.text == "👥 Do‘stlarni taklif qilish")
async def referrals_menu(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user["registered"]:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    link = await get_ref_link(message.from_user.id)
    await message.answer(
        "🔥 <b>Hayit oldidan super imkoniyat!</b>\n\n"
        "“aloo” siz uchun <b>“aloofest” MEGA KONKURSI</b>ni taqdim etadi!\n\n"
        "Do‘stlaringizni taklif qiling, ball to‘plang va quyidagi qimmatbaho sovg‘alarni yutib oling:\n\n"
        "🏆 <b>Asosiy mega sovg‘alar:</b>\n"
        "🥇 Redmi Robot Mop 2\n"
        "🥈 Novey Senat SC1 Red telefoni\n"
        "🥉 Zamonaviy elektr choynak\n\n"
        "🎲 <b>Haftalik random sovg‘alari:</b>\n"
        "AirPods, telefon, smartwatch, planshet va boshqa ko‘plab sovg‘alar!\n\n"
        "💎 Har bir taklif qilgan do‘stingiz uchun sizga <b>+5 ball</b> beriladi.\n\n"
        "📌 Sizning maxsus havolangiz orqali ro‘yxatdan o‘tgan har bir ishtirokchi sizni g‘alabaga yanada yaqinlashtiradi.\n\n"
        f"🚀 Hoziroq ulashing va hayit oldidan omadni qo‘ldan boy bermang:\n\n{link}"
    )


@dp.message(F.text == "🏆 Reyting (TOP 10)")
async def top_menu(message: Message):
    rows = await db.top_users(10)
    if not rows:
        await message.answer("Hozircha reyting shakllanmagan.")
        return

    text = "🏆 <b>TOP 10 ishtirokchilar</b>\n\n"
    for i, row in enumerate(rows, start=1):
        title = row["full_name"] or row["tg_name"] or row["username"] or "Ishtirokchi"
        text += f"{i}. {title} — {row['fest_id'] or '-'} — {row['diamonds']} ball\n"
    await message.answer(text)


@dp.message(F.text == "🎲 Random o‘yin")
async def random_menu(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user["registered"]:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    refs = user["referral_count"] or 0
    balls = user["diamonds"] or 0
    status = "✅ Siz haftalik random o‘yinida qatnasha olasiz!" if refs >= 3 else "❌ Siz hali random uchun yetarli shartni bajarmadingiz. Kamida 3 do‘st taklif qiling."

    await message.answer(
        f"🎲 <b>Haftalik random o‘yinlari</b>\n\n"
        f"Har hafta davomida kamida <b>3+ do‘st</b> taklif qilib, <b>15+ ball</b> to‘plagan ishtirokchilar random o‘yinida qatnasha oladi.\n\n"
        f"🎁 Haftalik o‘yinlarda quyidagi sovg‘alar o‘ynaladi:\n"
        f"• AirPods\n"
        f"• Telefon\n"
        f"• Smartwatch\n"
        f"• Planshet\n"
        f"• va boshqa qimmatbaho sovg‘alar\n\n"
        f"📊 Sizning holatingiz:\n"
        f"👥 Taklif qilingan do‘stlar: {refs}\n"
        f"💎 Ballar: {balls}\n\n"
        f"{status}"
    )


@dp.message(F.text == "💎 Mening ballarim")
async def my_points(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user["registered"]:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    await message.answer(
        f"💎 <b>Mening ballarim</b>\n\n"
        f"Ballar: {user['diamonds']}\n"
        f"Referallar: {user['referral_count']}\n"
        f"FEST ID: {user['fest_id'] or '-'}"
    )


@dp.message(F.text == "📊 Statistikam")
async def my_stats(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user["registered"]:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    rank_data = await db.get_rank(message.from_user.id)
    await message.answer(
        f"📊 <b>Statistikam</b>\n\n"
        f"👤 Ism: {user['full_name']}\n"
        f"🆔 FEST ID: {user['fest_id']}\n"
        f"💎 Ball: {user['diamonds']}\n"
        f"👥 Taklif qilingan do‘stlar: {user['referral_count']}\n"
        f"🏆 Reytingdagi o‘rningiz: {rank_data['rank']}/{rank_data['total']}"
    )


@dp.message(F.text == "🎁 Sovg‘alar")
async def prizes_menu(message: Message):
    await message.answer(
        "🎁 <b>“aloofest” mega konkurs sovg‘alari</b>\n\n"
        "🏆 <b>Hayit bayrami mega konkursi:</b>\n"
        "🥇 1-o‘rin — Redmi Robot Mop 2\n"
        "🥈 2-o‘rin — Novey Senat SC1 Red telefoni\n"
        "🥉 3-o‘rin — Zamonaviy elektr choynak\n\n"
        "🎲 <b>Haftalik random sovg‘alari:</b>\n"
        "• AirPods\n"
        "• Telefon\n"
        "• Smartwatch\n"
        "• Planshet\n"
        "• va boshqa qimmatbaho sovg‘alar\n\n"
        "🍀 Har bir ball sizni sovg‘alarga yaqinlashtiradi!"
    )


@dp.message(F.text == "🆘 Yordam")
async def help_menu(message: Message):
    await message.answer(
        "🆘 <b>Yordam bo‘limi</b>\n\n"
        "Savolingiz yoki murojaatingizni shu chatga yozib yuboring.\n"
        "Adminlar imkon qadar tez javob berishadi.\n\n"
        "Qo‘shimcha aloqa: @aloouz_chat"
    )


@dp.message(F.text == "ℹ️ konkurs haqida")
async def about_menu(message: Message):
    await message.answer(ABOUT_TEXT)


@dp.message(F.text == "🏠 Oddiy menyu")
async def back_user_menu(message: Message):
    await message.answer("🏠 Oddiy menyuga qaytdingiz.", reply_markup=main_menu())


@dp.message(F.text == "📋 Mijozlar ro‘yxati")
async def admin_users_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = await db.get_recent_users(40)
    if not users:
        await message.answer("Mijozlar topilmadi.")
        return
    text = "📋 <b>So‘nggi mijozlar ro‘yxati</b>\n\n"
    for user in users:
        text += (
            f"🆔 {user['user_id']} | "
            f"{user['full_name'] or user['tg_name'] or '-'} | "
            f"{user['fest_id'] or '-'}\n"
        )
    await message.answer(text)


@dp.message(F.text == "🏆 TOP 10 admin")
async def admin_top(message: Message):
    if not is_admin(message.from_user.id):
        return
    await top_menu(message)


@dp.message(F.text == "📊 Statistika")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    stats = await db.get_stats()
    await message.answer(
        f"📊 <b>Umumiy statistika</b>\n\n"
        f"👥 Foydalanuvchilar: {stats['total_users']}\n"
        f"✅ Ro‘yxatdan o‘tganlar: {stats['registered']}\n"
        f"⛔ Ban userlar: {stats['banned']}\n"
        f"💎 Umumiy ball: {stats['diamonds']}\n"
        f"🎲 Randomga tayyorlar: {stats['random_ready']}"
    )


@dp.message(F.text == "🌍 Hududiy statistika")
async def admin_region_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    rows = await db.get_region_stats()
    if not rows:
        await message.answer("Hududiy statistika topilmadi.")
        return
    text = "🌍 <b>Hududiy statistika</b>\n\n"
    for row in rows:
        text += f"{row['region'] or 'Noma’lum'} — {row['total']} ta | {row['diamonds']} ball\n"
    await message.answer(text)


@dp.message(F.text == "🎟 PROMO")
async def promo_stats(message: Message):
    if not is_admin(message.from_user.id):
        return

    rows = await db.get_promo_stats()
    if not rows:
        await message.answer("PROMO statistika hozircha bo‘sh.")
        return

    text = "🎟 <b>PROMO statistika</b>\n\n"
    for idx, row in enumerate(rows, start=1):
        text += f"{idx}. {row['promo_branch']} — {row['promo_code']} — {row['total']} ta\n"

    await message.answer(text)


@dp.message(F.text == "⛔ Ban user")
async def ban_user_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(BanState.waiting_user)
    await message.answer("Ban qilish uchun user ID yoki FEST ID yuboring.")


@dp.message(BanState.waiting_user)
async def ban_user_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    query = message.text.strip()
    user = await db.get_user(int(query)) if query.isdigit() else await db.get_user_by_fest(query)
    if not user:
        await message.answer("User topilmadi.")
        await state.clear()
        return
    await db.ban_user(user["user_id"])
    await message.answer(f"⛔ User ban qilindi: {user['full_name'] or user['tg_name']}")
    await state.clear()


@dp.message(F.text == "✅ Unban user")
async def unban_user_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(UnbanState.waiting_user)
    await message.answer("Unban qilish uchun user ID yoki FEST ID yuboring.")


@dp.message(UnbanState.waiting_user)
async def unban_user_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    query = message.text.strip()
    user = await db.get_user(int(query)) if query.isdigit() else await db.get_user_by_fest(query)
    if not user:
        await message.answer("User topilmadi.")
        await state.clear()
        return
    await db.unban_user(user["user_id"])
    await message.answer(f"✅ User unban qilindi: {user['full_name'] or user['tg_name']}")
    await state.clear()


@dp.message(F.text == "🔎 User qidirish")
async def search_user_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(SearchState.waiting_query)
    await message.answer("Qidirish uchun user ID, FEST ID, username yoki instagram yuboring.")


@dp.message(SearchState.waiting_query)
async def search_user_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    rows = await db.search_users(message.text.strip())
    if not rows:
        await message.answer("User topilmadi.")
        await state.clear()
        return
    text = "🔎 <b>Qidiruv natijalari</b>\n\n"
    for user in rows:
        text += (
            f"🆔 {user['user_id']}\n"
            f"👤 {user['full_name'] or user['tg_name'] or '-'}\n"
            f"📸 @{user['instagram'] or '-'}\n"
            f"📱 {user['phone'] or '-'}\n"
            f"🎫 {user['fest_id'] or '-'}\n"
            f"💎 {user['diamonds']} | 👥 {user['referral_count']}\n\n"
        )
    await message.answer(text)
    await state.clear()


@dp.message(F.text == "💬 Userga xabar yuborish")
async def direct_msg_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(DirectMessageState.waiting_user)
    await message.answer("Xabar yuboriladigan user ID yoki FEST ID ni yuboring.")


@dp.message(DirectMessageState.waiting_user)
async def direct_msg_pick_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    query = message.text.strip()
    user = await db.get_user(int(query)) if query.isdigit() else await db.get_user_by_fest(query)
    if not user:
        await message.answer("User topilmadi.")
        await state.clear()
        return
    await state.update_data(target_user_id=user["user_id"])
    await state.set_state(DirectMessageState.waiting_message)
    await message.answer(f"Endi {user['full_name'] or user['tg_name']} uchun xabar yuboring.")


@dp.message(DirectMessageState.waiting_message)
async def direct_msg_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    user_id = data["target_user_id"]
    try:
        await bot.send_message(user_id, f"📩 <b>Admin xabari</b>\n\n{message.text}")
        await message.answer("Xabar yuborildi.")
    except Exception as e:
        await message.answer(f"Xabar yuborilmadi: {e}")
    await state.clear()


@dp.message(F.text == "📣 Broadcast")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(BroadcastState.waiting_message)
    await message.answer("Hammaga yuboriladigan xabarni yuboring.")


@dp.message(BroadcastState.waiting_message)
async def broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    users = await db.all_users()
    sent = 0
    for user in users:
        try:
            await bot.send_message(user["user_id"], f"📢 <b>aloo yangiligi</b>\n\n{message.text}")
            sent += 1
        except Exception:
            pass
    await message.answer(f"Broadcast yakunlandi. Yuborildi: {sent}")
    await state.clear()


@dp.message(F.text == "📢 Reklama joylash")
async def ad_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AdState.waiting_title)
    await message.answer("Reklama sarlavhasini yuboring.")


@dp.message(AdState.waiting_title)
async def ad_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AdState.waiting_body)
    await message.answer("Reklama matnini yuboring.")


@dp.message(AdState.waiting_body)
async def ad_body(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.save_ad(data["title"], message.text.strip())
    await message.answer("✅ Reklama saqlandi.")
    await state.clear()


@dp.message(F.text == "📢 Reklamalar ro‘yxati")
async def ads_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    ads = await db.get_ads()
    if not ads:
        await message.answer("Reklamalar yo‘q.")
        return
    text = "📢 <b>Reklamalar ro‘yxati</b>\n\n"
    for ad in ads:
        text += f"#{ad['id']} — <b>{ad['title']}</b>\n{ad['body']}\n\n"
    await message.answer(text)


@dp.message(F.text == "🎁 Sovg‘alarni o‘zgartirish")
async def prize_edit_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    prizes = await db.get_prizes()
    text = "🎁 O‘zgartiriladigan prize ID ni yuboring:\n\n"
    for p in prizes:
        text += f"{p['id']}. {p['place_name']} — {p['title']}\n"
    await state.set_state(PrizeState.waiting_id)
    await message.answer(text)


@dp.message(PrizeState.waiting_id)
async def prize_edit_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Prize ID raqam bo‘lishi kerak.")
        return
    await state.update_data(prize_id=int(message.text.strip()))
    await state.set_state(PrizeState.waiting_place)
    await message.answer("Yangi place nomini yuboring. Masalan: 🥇 1-o‘rin")


@dp.message(PrizeState.waiting_place)
async def prize_edit_place(message: Message, state: FSMContext):
    await state.update_data(place_name=message.text.strip())
    await state.set_state(PrizeState.waiting_title)
    await message.answer("Yangi prize nomini yuboring.")


@dp.message(PrizeState.waiting_title)
async def prize_edit_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(PrizeState.waiting_desc)
    await message.answer("Yangi izohni yuboring.")


@dp.message(PrizeState.waiting_desc)
async def prize_edit_desc(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_prize(
        data["prize_id"],
        data["place_name"],
        data["title"],
        message.text.strip()
    )
    await message.answer("✅ Sovg‘a yangilandi.")
    await state.clear()


@dp.message(F.text == "📤 Excel export")
async def excel_export(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = await db.all_users()

    wb = Workbook()
    ws = wb.active
    ws.title = "Users"
    ws.append([
        "Telegram ID", "Ism", "Instagram", "Telefon", "FEST ID",
        "Viloyat", "Tuman", "Ball", "Referallar", "Promokod", "Filial", "Ban"
    ])

    for user in users:
        ws.append([
            user["user_id"],
            user["full_name"] or user["tg_name"] or "",
            user["instagram"] or "",
            user["phone"] or "",
            user["fest_id"] or "",
            user["region"] or "",
            user["district"] or "",
            user["diamonds"] or 0,
            user["referral_count"] or 0,
            user["promo_code"] or "",
            user["promo_branch"] or "",
            "ha" if user["banned"] else "yo‘q",
        ])

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    await message.answer_document(
        BufferedInputFile(bio.read(), filename="aloofest_users.xlsx")
    )


@dp.message(F.text == "🎲 Random admin")
async def random_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    now = datetime.now()
    await state.clear()
    await message.answer(
        "🎲 <b>RANDOM ORQALI G‘OLIBNI ANIQLASH</b>\n\n📅 BOSHLANISH SANASINI TANLANG",
        reply_markup=build_calendar(now.year, now.month, "rnd_start")
    )


@dp.callback_query(F.data == "noop")
async def noop_handler(call: CallbackQuery):
    await call.answer()


@dp.callback_query(F.data.startswith("rnd_start:nav:"))
async def rnd_start_nav(call: CallbackQuery):
    _, _, y, m, direction = call.data.split(":")
    y = int(y)
    m = int(m)

    if direction == "prev":
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    else:
        m += 1
        if m == 13:
            m = 1
            y += 1

    await call.message.edit_reply_markup(reply_markup=build_calendar(y, m, "rnd_start"))
    await call.answer()


@dp.callback_query(F.data.startswith("rnd_start:pick:"))
async def rnd_start_pick(call: CallbackQuery, state: FSMContext):
    _, _, y, m, d = call.data.split(":")
    start_date = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    await state.update_data(start_date=start_date)

    now = datetime.now()
    await call.message.edit_text(
        f"✅ Boshlanish sanasi: <b>{start_date}</b>\n\n📅 Endi <b>TUGASH SANASINI TANLANG</b>",
        reply_markup=build_calendar(now.year, now.month, "rnd_end")
    )
    await call.answer()


@dp.callback_query(F.data.startswith("rnd_end:nav:"))
async def rnd_end_nav(call: CallbackQuery):
    _, _, y, m, direction = call.data.split(":")
    y = int(y)
    m = int(m)

    if direction == "prev":
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    else:
        m += 1
        if m == 13:
            m = 1
            y += 1

    await call.message.edit_reply_markup(reply_markup=build_calendar(y, m, "rnd_end"))
    await call.answer()


@dp.callback_query(F.data.startswith("rnd_end:pick:"))
async def rnd_end_pick(call: CallbackQuery, state: FSMContext):
    _, _, y, m, d = call.data.split(":")
    end_date = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    data = await state.get_data()
    start_date = data.get("start_date")

    await state.update_data(end_date=end_date)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 G‘OLIBNI ANIQLASH", callback_data="rnd_confirm")]
        ]
    )

    await call.message.edit_text(
        f"✅ Boshlanish: <b>{start_date}</b>\n"
        f"✅ Tugash: <b>{end_date}</b>\n\n"
        f"Endi g‘olibni aniqlash tugmasini bosing.",
        reply_markup=kb
    )
    await call.answer()


@dp.callback_query(F.data == "rnd_confirm")
async def random_confirm(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return

    data = await state.get_data()
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    start_ts = parse_date_to_ts(start_date, end_of_day=False)
    end_ts = parse_date_to_ts(end_date, end_of_day=True)

    if start_ts is None or end_ts is None or end_ts < start_ts:
        await call.message.edit_text("❌ Sana oralig‘i noto‘g‘ri.")
        await state.clear()
        await call.answer()
        return

    users = await db.get_random_candidates(start_ts, end_ts)
    if not users:
        await call.message.edit_text("❌ Bu oralig‘da 3+ referal (15+ ball) ishtirokchilar topilmadi.")
        await state.clear()
        await call.answer()
        return

    await call.message.edit_text("🎲 Random boshlandi...\n\n✨ G‘olib aniqlanmoqda...\nLoading: 0%")
    for p in [10, 25, 40, 55, 70, 85, 100]:
        await asyncio.sleep(1.2)
        await call.message.edit_text(
            f"🎲 Random boshlandi...\n\n"
            f"🔍 Ishtirokchilar tekshirilmoqda...\n"
            f"🏆 G‘olib aniqlanmoqda...\n"
            f"Loading: {p}%"
        )

    winner = random.choice(users)
    winner_name = winner["full_name"] or winner["tg_name"] or "Ishtirokchi"

    await db.save_random_history(
        winner_user_id=winner["user_id"],
        winner_name=winner_name,
        telegram_id=winner["user_id"],
        instagram=winner["instagram"] or "",
        fest_id=winner["fest_id"] or "",
        diamonds=winner["diamonds"] or 0,
        start_date=start_date,
        end_date=end_date,
    )

    ig_url = f"https://instagram.com/{winner['instagram']}" if winner["instagram"] else INSTAGRAM_MAIN_URL
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 Instagram tekshirish", url=ig_url)],
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_last_random")]
        ]
    )

    await call.message.edit_text(
        f"🏆 <b>Random g‘olibi aniqlandi!</b>\n\n"
        f"👤 Ism: {winner_name}\n"
        f"🆔 Telegram ID: {winner['user_id']}\n"
        f"📸 Instagram: @{winner['instagram'] or '-'}\n"
        f"🎫 FEST ID: {winner['fest_id'] or '-'}\n"
        f"💎 Ball: {winner['diamonds'] or 0}\n\n"
        f"📅 Oralig‘: {start_date} → {end_date}",
        reply_markup=kb
    )

    await state.clear()
    await call.answer()


@dp.callback_query(F.data == "confirm_last_random")
async def confirm_last_random(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Ruxsat yo‘q", show_alert=True)
        return
    row = await db.get_last_random()
    if not row:
        await call.answer("Tasdiqlanadigan random topilmadi.", show_alert=True)
        return
    await db.confirm_last_random()
    try:
        await bot.send_message(
            row["winner_user_id"],
            f"🎉 <b>Tabriklaymiz!</b>\n\n"
            f"Siz <b>{row['start_date']} - {row['end_date']}</b> oralig‘idagi random o‘yinida g‘olib bo‘ldingiz.\n"
            f"Tez orada operatorlar siz bilan bog‘lanishadi."
        )
    except Exception:
        pass
    await call.answer("G‘olib tasdiqlandi", show_alert=True)


@dp.message()
async def fallback(message: Message):
    if is_admin(message.from_user.id):
        pending = await db.get_pending_reply(message.from_user.id)
        if pending:
            await bot.send_message(
                pending,
                f"📩 <b>Admin javobi</b>\n\n{message.text}"
            )
            await db.clear_pending_reply(message.from_user.id)
            await message.answer("✅ Javob foydalanuvchiga yuborildi.", reply_markup=admin_menu())
            return

    user = await db.get_user(message.from_user.id)
    if user and user["registered"] and not is_admin(message.from_user.id):
        await db.save_support_message(
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=user["full_name"] or user["tg_name"],
            message_text=message.text
        )

        text = (
            f"🆘 <b>Yangi yordam xabari</b>\n\n"
            f"👤 {user['full_name'] or user['tg_name']}\n"
            f"🆔 {message.from_user.id}\n"
            f"🎫 {user['fest_id'] or '-'}\n"
            f"📸 @{user['instagram'] or '-'}\n\n"
            f"💬 {message.text}\n\n"
            f"Javob yozish uchun /reply_{message.from_user.id}"
        )
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, text)
            except Exception:
                pass

        await message.answer("✅ Xabaringiz adminlarga yuborildi. Tez orada javob berishadi.")
        return

    await message.answer("Kerakli bo‘limni tanlang.")


@dp.message(Command(commands=["reply"]))
async def reply_help(message: Message):
    await message.answer("To‘g‘ri format: /reply_123456789")


@dp.message(F.text.regexp(r"^/reply_\d+$"))
async def reply_dynamic(message: Message):
    if not is_admin(message.from_user.id):
        return
    target_id = int(message.text.split("_")[1])
    await db.set_pending_reply(message.from_user.id, target_id)
    await message.answer(f"Endi {target_id} foydalanuvchiga yuboriladigan javob matnini yozing.")


async def main():
    await db.init()
    await setup_web_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
