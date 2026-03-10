import hmac
import hashlib
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from config import (
    CHANNEL_URL,
    SHOP_BOT_URL,
    BASE_URL,
    WEBAPP_SECRET,
    INSTAGRAM_MAIN_URL,
)


def sign_uid(uid: int) -> str:
    return hmac.new(
        WEBAPP_SECRET.encode(),
        str(uid).encode(),
        hashlib.sha256
    ).hexdigest()


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ ISHTIROK ETAMAN", callback_data="join_now")]
        ]
    )


def rules_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 konkurs shartlari", callback_data="show_rules")]
        ]
    )


def subscribe_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Telegram kanal", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="📸 Instagram profil", url=INSTAGRAM_MAIN_URL)],
            [InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")],
        ]
    )


def register_keyboard(user_id: int) -> InlineKeyboardMarkup:
    sig = sign_uid(user_id)
    register_url = f"{BASE_URL}/register?uid={user_id}&sig={sig}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 RO‘YXATDAN O‘TISH", url=register_url)]
        ]
    )


def after_registration_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 BOSHLASH", callback_data="open_main_menu")]
        ]
    )


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Do‘stlarni taklif qilish")],
            [KeyboardButton(text="🏆 Reyting (TOP 10)"), KeyboardButton(text="🎲 Random o‘yin")],
            [KeyboardButton(text="💎 Mening ballarim"), KeyboardButton(text="📊 Statistikam")],
            [KeyboardButton(text="🎁 Sovg‘alar"), KeyboardButton(text="ℹ️ konkurs haqida")],
            [KeyboardButton(text="🆘 Yordam")],
        ],
        resize_keyboard=True
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Mijozlar ro‘yxati"), KeyboardButton(text="🎲 Random admin")],
            [KeyboardButton(text="🏆 TOP 10 admin"), KeyboardButton(text="📤 Excel export")],
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🌍 Hududiy statistika")],
            [KeyboardButton(text="🎟 PROMO"), KeyboardButton(text="⛔ Ban user")],
            [KeyboardButton(text="✅ Unban user"), KeyboardButton(text="🎁 Sovg‘alarni o‘zgartirish")],
            [KeyboardButton(text="📣 Broadcast"), KeyboardButton(text="🔎 User qidirish")],
            [KeyboardButton(text="💬 Userga xabar yuborish"), KeyboardButton(text="📢 Reklama joylash")],
            [KeyboardButton(text="📢 Reklamalar ro‘yxati"), KeyboardButton(text="🏠 Oddiy menyu")],
        ],
        resize_keyboard=True
    )
