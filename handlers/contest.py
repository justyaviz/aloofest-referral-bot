from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message(lambda m: m.text == "🎉 Konkurs")
async def contest(message: Message):
    await message.answer("Konkurs bo'limi")
