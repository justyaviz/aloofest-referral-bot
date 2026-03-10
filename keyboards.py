from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import CHANNEL_URL, SHOP_BOT_URL, BASE_URL, WEBAPP_SECRET
import hmac
import hashlib


def _sign_uid(uid: int) -> str:
    return hmac.new(
        WEBAPP_SECRET.encode(),
        str(uid).encode(),
        hashlib.sha256
    ).hexdigest()


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎉 Konkursda qatnashish")],
            [KeyboardButton(text="💎 Mening ballarim"), KeyboardButton(text="🔗 Do‘st taklif qilish")],
            [KeyboardButton(text="🏆 Top ranking"), KeyboardButton(text="🕘 Random tarixi")],
            [KeyboardButton(text="📞 Bog‘lanish"), KeyboardButton(text="ℹ️ Mening profilim")],
        ],
        resize_keyboard=True
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎲 Random o‘yin")],
            [KeyboardButton(text="📣 Broadcast"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="📥 Excel export"), KeyboardButton(text="🏆 Admin top ranking")],
            [KeyboardButton(text="🏠 Asosiy menyu")],
        ],
        resize_keyboard=True
    )


def subscribe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga a’zo bo‘lish", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="🤖 Botga /start bosish", url=SHOP_BOT_URL)],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")],
        ]
    )


def register_keyboard(user_id: int) -> InlineKeyboardMarkup:
    sig = _sign_uid(user_id)
    register_url = f"{BASE_URL}/register?uid={user_id}&sig={sig}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Ro‘yxatdan o‘tish", url=register_url)]
        ]
    )
