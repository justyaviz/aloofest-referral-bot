from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards import main_menu

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message):
    text = (
        "🎉 <b>aloo konkurs botiga xush kelibsiz!</b>\n\n"
        "Bu bot orqali siz konkursda qatnashishingiz, "
        "do‘stlaringizni taklif qilib 💎 ball yig‘ishingiz va "
        "random g‘oliblar qatoridan joy olishingiz mumkin.\n\n"
        "Quyidagi menyudan kerakli bo‘limni tanlang."
    )
    await message.answer(text, reply_markup=main_menu())
