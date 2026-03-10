import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties

from database import db
from config import BOT_TOKEN, ADMIN_IDS

bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


# START
@dp.message(CommandStart())
async def start(message: Message):

    await db.add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    await message.answer(
        "🎉 Aloofest konkurs botiga xush kelibsiz!"
    )


# ADMIN ADD BALL
@dp.message(Command("addball"))
async def add_ball(message: Message):

    if message.from_user.id not in ADMIN_IDS:
        return

    parts = message.text.split()

    if len(parts) != 3:

        await message.answer(
            "❌ Format noto‘g‘ri\n\n"
            "/addball USER_ID BALL"
        )

        return

    user_id = parts[1]
    ball = parts[2]

    if not user_id.isdigit() or not ball.isdigit():

        await message.answer("❌ ID va BALL raqam bo‘lishi kerak")

        return

    user_id = int(user_id)
    ball = int(ball)

    await db.add_points(user_id, ball)

    await message.answer(
        f"✅ {user_id} userga {ball} ball qo‘shildi"
    )


# TEST RANDOM USERS
@dp.message(Command("seedtest"))
async def seed_test(message: Message):

    if message.from_user.id not in ADMIN_IDS:
        return

    await db.set_test_random_user(8124320409, 25, 5)
    await db.set_test_random_user(7803701344, 25, 5)

    await message.answer(
        "✅ Test random userlar tayyor\n\n"
        "8124320409\n"
        "7803701344\n\n"
        "Ball: 25\n"
        "Referal: 5"
    )


# TOP
@dp.message(Command("top"))
async def top(message: Message):

    users = await db.top_users()

    text = "🏆 TOP 10\n\n"

    i = 1

    for u in users:

        name = u["tg_name"] or "user"

        text += f"{i}. {name} — {u['diamonds']} ball\n"

        i += 1

    await message.answer(text)


async def main():

    await db.init()

    print("Bot ishga tushdi")

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
