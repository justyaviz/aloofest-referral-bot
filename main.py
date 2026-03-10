import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN, CHANNEL_USERNAME
from database import db
from keyboards import start_keyboard, rules_keyboard, subscribe_keyboard, register_keyboard, main_menu
from web_server import setup_web_server


bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


START_TEXT = """
🎉 Kutib oling aloo'dan <b>MEGA KONKURS — aloofest</b>!

Keling, endi sovg'alar ro'yxati bilan tanishtiraman 👇

🎯 Sizda 2 xil yutish imkoniyati bor:

1️⃣ TOP 3 ga kirish
2️⃣ Random o'yini

🎁 <b>TOP 3 uchun sovg'alar:</b>
🥇 1-o‘rin — Tecno Spark Go 30C
🥈 2-o‘rin — Mini pech Artel
🥉 3-o‘rin — Ryugzak

🎲 <b>Random o'yin:</b>
Kamida 3 ta do‘stingizni taklif qiling va random o‘yinda ishtirok eting.

💎 Kanalimizga 3 ta odam qo‘shgan barcha ishtirokchilar orasidan random orqali 3 ta maxsus sovg‘a taqdim qilinadi:

1. AirPods Max Copy
2. AirPods Max Copy
3. AirPods Max Copy

📅 G‘oliblar jonli efir orqali aniqlanadi.
Sana bot orqali va @aloo_uzb kanalida e’lon qilinadi.

Hammaga omad! 🍀
"""

RULES_TEXT = """
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

Shunda foydalanuvchi random o‘yin ishtirokchisi bo‘ladi.

Random qanday ishlaydi:
• 3+ referal yig‘ganlar ro‘yxati olinadi
• ular orasidan random g‘olib tanlanadi
• har hafta 1 ta g‘olib

🥇 <b>2. Ramazon hayiti super konkursi (TOP)</b>

Bu asosiy katta konkurs.

TOP reyting:
Eng ko‘p ball yig‘ganlar yutadi.

Ko‘rinadi:
🏆 TOP 10 ishtirokchilar
1. Ali — FEST-014 — 240 ball
2. Bek — FEST-092 — 195 ball
3. Aziz — FEST-033 — 170 ball
4. ...

📋 <b>TOP konkurs shartlari</b>

1️⃣ Telegram
Ishtirokchi @aloo_uzb kanaliga obuna bo‘lishi kerak.
Bot avtomatik tekshiradi.

2️⃣ Instagram
Ishtirokchi @aloo.uz_ sahifasiga obuna bo‘lishi kerak.
Sahifa obuna bo‘lgan 15 ta profilga ham obuna bo‘lishi kerak.
Bu manual tekshiruv orqali amalga oshiriladi.
"""

ABOUT_TEXT = """
ℹ️ <b>aloofest haqida</b>

aloofest — bu aloo tomonidan tashkil etilgan maxsus yutuqli konkurs bo‘lib, unda siz:

• do‘stlaringizni taklif qilish
• ball to‘plash
• TOP reytingga kirish
• random o‘yinda ishtirok etish

orqali qimmatbaho sovg‘alarni yutib olishingiz mumkin.
"""


async def is_channel_member(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False


async def get_ref_link(user_id: int) -> str:
    me = await bot.get_me()
    return f"https://t.me/{me.username}?start=ref_{user_id}"


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

    await message.answer(START_TEXT, reply_markup=start_keyboard())


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
        "• Online do‘kon botga /start bosing\n"
        "• So‘ng Tekshirish tugmasini bosing",
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
        "✅ Zo‘r, obuna tasdiqlandi!\n\n"
        "Endi konkurs ishtirokchisi bo‘lish uchun ro‘yxatdan o‘ting 👇",
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
        text += f"{i}. {row['full_name'] or row['tg_name'] or row['username'] or 'Ishtirokchi'} — {row['fest_id'] or '-'} — {row['diamonds']} ball\n"
    await message.answer(text)


@dp.message(F.text == "🎲 Random o‘yin")
async def random_menu(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or not user["registered"]:
        await message.answer("Avval ro‘yxatdan o‘ting.")
        return

    refs = user["referral_count"] or 0
    balls = user["diamonds"] or 0

    if refs >= 3:
        status = "✅ Siz random o‘yinda ishtirok etish huquqiga egasiz."
    else:
        status = "❌ Siz hali random o‘yinga to‘liq qatnashish shartini bajarmadingiz."

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


@dp.message(F.text == "ℹ️ Konkurs haqida")
async def about_menu(message: Message):
    await message.answer(ABOUT_TEXT)


@dp.message()
async def fallback(message: Message):
    user = await db.get_user(message.from_user.id)
    if user and user["registered"]:
        await message.answer("Quyidagi menyulardan foydalaning 👇", reply_markup=main_menu())


async def main():
    await db.init()
    await setup_web_server()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
