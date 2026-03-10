import asyncio
import io
import random
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
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
    main_menu,
    admin_menu,
)
from web_server import setup_web_server


bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


class AdminReplyState(StatesGroup):
    waiting_text = State()


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


START_TEXT = """
🎉 Kutib oling aloo'dan <b>MEGA KONKURS — aloofest</b>!

Keling, endi sovg'alar ro'yxati bilan tanishtiraman 👇

🎯 Sizda 2 xil yutish imkoniyati bor:

1. TOP 3 ga kirish
2. Random o'yini

🎁 <b>TOP 3 uchun sovg'alar:</b>
🥇 1-o‘rin — Tecno Spark Go 30C
🥈 2-o‘rin — Mini pech Artel
🥉 3-o‘rin — Ryugzak

🎲 <b>Random o'yini:</b>
Kamida 3 ta do‘stingizni taklif qiling va random o‘yinda ishtirok eting.

💎 Kanalimizga 3 ta odam qo‘shgan barcha ishtirokchilar orasidan random orqali 3 ta maxsus sovg‘a taqdim qilinadi:
1. AirPods Max Copy
2. AirPods Max Copy
3. AirPods Max Copy

📅 G‘oliblar jonli efir orqali aniqlanadi.
Sana bot orqali va @aloo_uzb kanalida e’lon qilinadi.

Hammaga omad! 🍀
"""

RULES_TEXT = f"""
🏆 <b>aloofest konkurs tizimi (final model)</b>

🎯 <b>Ball tizimi</b>
1 ta do‘st taklif qilish = 5 ball

Ball random o‘yinda ham, TOP reytingda ham ishlatiladi.

Misol:
1 referal = 5 ball
5 referal = 25 ball
10 referal = 50 ball

🎲 <b>1. Har hafta random o‘yini</b>

Ishtirok sharti:
Kamida 3 ta do‘st taklif qilish kerak.
3 referal = 15 ball

3 va undan ko‘p referal to‘plagan ishtirokchilar random o‘yinda qatnashadi.

🥇 <b>2. Ramazon hayiti super konkursi (TOP)</b>

TOP reyting:
Eng ko‘p ball yig‘ganlar yutadi.

📋 <b>Ishtirok shartlari</b>
1️⃣ Telegram — @{CHANNEL_USERNAME} kanaliga obuna bo‘lish
2️⃣ Instagram — asosiy profilga va u obuna bo‘lgan 15 ta profilga obuna bo‘lish
3️⃣ Web sahifa orqali ro‘yxatdan o‘tish

❗ Instagram obunasi majburiy.
Agar foydalanuvchi Instagram shartlarini bajarmagan bo‘lsa, u g‘olib deb tasdiqlanmaydi.

📸 Instagram bo‘yicha shart:
{INSTAGRAM_RULE_TEXT}
"""

ABOUT_TEXT = f"""
ℹ️ <b>aloofest haqida</b>

aloofest — bu aloo tomonidan tashkil etilgan maxsus yutuqli konkurs bo‘lib, unda siz:
• do‘stlaringizni taklif qilish
• ball to‘plash
• TOP reytingga kirish
• random o‘yinda ishtirok etish

orqali qimmatbaho sovg‘alarni yutib olishingiz mumkin.

📸 Instagram sharti:
{INSTAGRAM_RULE_TEXT}

Asosiy profil:
{INSTAGRAM_MAIN_URL}
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
        await message.answer(
            f"🎉 Xush kelibsiz, {user['full_name'] or user['tg_name']}!\n\n"
            f"Quyidagi menyulardan foydalaning 👇",
            reply_markup=main_menu()
        )
        return

    await message.answer(START_TEXT, reply_markup=start_keyboard())


@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Siz admin emassiz.")
        return
    await message.answer("🛠 <b>Admin panel</b>", reply_markup=admin_menu())


@dp.callback_query(F.data == "open_main_menu")
async def open_main_menu(call: CallbackQuery):
    user = await db.get_user(call.from_user.id)
    if not user or not user["registered"]:
        await call.message.answer("Avval ro‘yxatdan o‘ting.")
        await call.answer()
        return

    await call.message.answer(
        f"🚀 Zo‘r, {user['full_name'] or user['tg_name']}!\n\n"
        f"Quyidagi menyulardan foydalaning 👇",
        reply_markup=main_menu()
    )
    await call.answer("Menyu ochildi")


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
        f"👥 <b>Do‘stlarni taklif qilish</b>\n\n"
        f"Har bir muvaffaqiyatli taklif uchun sizga 5 ball beriladi.\n\n"
        f"🔗 Sizning maxsus havolangiz:\n{link}"
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
    status = "✅ Siz random o‘yinda ishtirok etish huquqiga egasiz." if refs >= 3 else "❌ Siz hali random o‘yinga to‘liq qatnashish shartini bajarmadingiz."

    await message.answer(
        f"🎲 <b>Random o‘yin</b>\n\n"
        f"👥 Referallar: {refs}\n"
        f"💎 Ball: {balls}\n\n"
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
    prizes = await db.get_prizes()
    if not prizes:
        await message.answer("Sovg‘alar hali kiritilmagan.")
        return

    text = "🎁 <b>aloofest sovg‘alari</b>\n\n"
    for item in prizes:
        text += f"{item['place_name']} — <b>{item['title']}</b>\n{item['description']}\n\n"
    await message.answer(text)


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


# Admin panel handlers
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
        text += f"🆔 {user['user_id']} | {user['full_name'] or user['tg_name'] or '-'} | {user['fest_id'] or '-'}\n"
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
    await bot.send_message(user_id, f"📩 <b>Admin xabari</b>\n\n{message.text}")
    await message.answer("Xabar yuborildi.")
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
    ws.append(["Telegram ID", "Ism", "Instagram", "FEST ID", "Viloyat", "Tuman", "Ball", "Referallar", "Ban"])

    for user in users:
        ws.append([
            user["user_id"],
            user["full_name"] or user["tg_name"] or "",
            user["instagram"] or "",
            user["fest_id"] or "",
            user["region"] or "",
            user["district"] or "",
            user["diamonds"] or 0,
            user["referral_count"] or 0,
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
    await state.set_state(RandomState.waiting_start)
    await message.answer(
        "🎲 Random admin panel\n\n"
        "Boshlanish sanasini yuboring.\n"
        "Format: YYYY-MM-DD\n"
        "Masalan: 2026-03-01"
    )


@dp.message(RandomState.waiting_start)
async def random_start_date(message: Message, state: FSMContext):
    start_ts = parse_date_to_ts(message.text.strip(), end_of_day=False)
    if start_ts is None:
        await message.answer("Sana noto‘g‘ri. Format: YYYY-MM-DD")
        return
    await state.update_data(start_date=message.text.strip(), start_ts=start_ts)
    await state.set_state(RandomState.waiting_end)
    await message.answer("Tugash sanasini yuboring. Format: YYYY-MM-DD")


@dp.message(RandomState.waiting_end)
async def random_end_date(message: Message, state: FSMContext):
    end_ts = parse_date_to_ts(message.text.strip(), end_of_day=True)
    if end_ts is None:
        await message.answer("Sana noto‘g‘ri. Format: YYYY-MM-DD")
        return

    data = await state.get_data()
    start_ts = data["start_ts"]
    start_date = data["start_date"]
    end_date = message.text.strip()

    if end_ts < start_ts:
        await message.answer("Tugash sanasi boshlanish sanasidan oldin bo‘lishi mumkin emas.")
        return

    users = await db.get_random_candidates(start_ts, end_ts)
    if not users:
        await message.answer("Bu oralig‘da 3+ referal (15+ ball) ishtirokchilar topilmadi.")
        await state.clear()
        return

    loading = await message.answer("🎲 Random ishga tushdi...\n\n🌀 G‘olib aniqlanmoqda...\nLoading: 0%")
    for p in [10, 25, 40, 55, 70, 85, 100]:
        await asyncio.sleep(1.2)
        await loading.edit_text(
            f"🎲 Random ishga tushdi...\n\n"
            f"✨ Ishtirokchilar tekshirilmoqda...\n"
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

    await loading.edit_text(
        f"🏆 <b>Random g‘olibi aniqlandi!</b>\n\n"
        f"👤 Ism: {winner_name}\n"
        f"🆔 Telegram ID: {winner['user_id']}\n"
        f"📸 Instagram: @{winner['instagram'] or '-'}\n"
        f"🎫 FEST ID: {winner['fest_id'] or '-'}\n"
        f"💎 Ball: {winner['diamonds'] or 0}\n\n"
        f"📅 Oralig‘: {start_date} → {end_date}\n\n"
        f"❗ Instagram obunasi va 15 ta profil sharti manual tekshiriladi.",
        reply_markup=kb
    )
    await state.clear()


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
