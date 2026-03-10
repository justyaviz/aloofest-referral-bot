from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from keyboards import subscribe_keyboard, register_keyboard

router = Router()

SUBSCRIBE_TEXT = (
    "📌 <b>Botdan foydalanish uchun quyidagilarni bajaring:</b>\n\n"
    "1️⃣ Kanalga a’zo bo‘ling\n"
    "2️⃣ Botga /start bosing\n\n"
    "Barchasini bajarganingizdan so‘ng <b>✅ Tekshirish</b> tugmasini bosing."
)

SUBSCRIBE_OK_TEXT = (
    "✅ <b>Zo‘r, obuna tasdiqlandi!</b>\n\n"
    "Endi konkurs ishtirokchisi bo‘lish uchun ro‘yxatdan o‘ting."
)


@router.message(F.text == "🎉 Konkursda qatnashish")
async def contest_handler(message: Message):
    await message.answer(SUBSCRIBE_TEXT, reply_markup=subscribe_keyboard())


@router.callback_query(F.data == "check_sub")
async def check_sub_handler(callback: CallbackQuery):
    await callback.message.answer(
        SUBSCRIBE_OK_TEXT,
        reply_markup=register_keyboard(callback.from_user.id)
    )
    await callback.answer("Tasdiqlandi")
