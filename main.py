from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from config import settings
from database import db
from handlers import admin, contest, profile, ranking, referral, start, support
from keyboards import admin_menu, main_menu
from web.server import setup_web_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

fallback_router = Router(name="fallback")


@fallback_router.message()
async def fallback(message: Message):
    await message.answer(
        "Kerakli bo‘limni menyudan tanlang.",
        reply_markup=admin_menu() if message.from_user.id in settings.admin_ids else main_menu(),
    )


async def main() -> None:
    await db.init()
    await setup_web_server()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(contest.router)
    dp.include_router(referral.router)
    dp.include_router(profile.router)
    dp.include_router(ranking.router)
    dp.include_router(support.router)
    dp.include_router(admin.router)
    dp.include_router(fallback_router)

    logging.info("Bot polling bilan ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
