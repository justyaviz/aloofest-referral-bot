from __future__ import annotations

import hashlib
import hmac

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from config import BASE_URL, CHANNEL_URL, SHOP_BOT_URL, WEBAPP_SECRET


def sign_uid(uid: int) -> str:
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
            [KeyboardButton(text="🏆 Top ranking"), KeyboardButton(text="📊 Mening o‘rnim")],
            [KeyboardButton(text="💎 Ball tarixi"), KeyboardButton(text="🎁 Sovg‘alar")],
            [KeyboardButton(text="🪪 Referral card"), KeyboardButton(text="🕘 Random tarixi")],
            [KeyboardButton(text="📞 Bog‘lanish"), KeyboardButton(text="ℹ️ Mening profilim")],
        ],
        resize_keyboard=True
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎲 Random o‘yin")],
            [KeyboardButton(text="📣 Broadcast"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🔎 User qidirish"), KeyboardButton(text="📥 Excel export")],
            [KeyboardButton(text="🏆 Admin top ranking"), KeyboardButton(text="🏠 Asosiy menyu")],
        ],
        resize_keyboard=True
    )


def support_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Yakunlash")]],
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
    sig = sign_uid(user_id)
    url = f"{BASE_URL}/register?uid={user_id}&sig={sig}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Ro‘yxatdan o‘tish", url=url)]
        ]
    )


def profile_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    sig = sign_uid(user_id)
    url = f"{BASE_URL}/register?uid={user_id}&sig={sig}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Ma’lumotlarni yangilash", url=url)],
            [InlineKeyboardButton(text="🔗 Taklif havolam", callback_data="my_invite_link")],
        ]
    )


def winner_keyboard(phone: str, full_name: str) -> InlineKeyboardMarkup:
    share_text = f"🎉 aloo random g‘olibi:\n\n👤 {full_name}\n📞 {phone}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📞 {phone}", callback_data="winner_phone")],
            [InlineKeyboardButton(text="📤 Ulashish", url=f"https://t.me/share/url?url=&text={share_text}")],
        ]
    )
