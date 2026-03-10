from __future__ import annotations

from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config import settings
from utils import sign_uid


def main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text='🎉 Konkursda qatnashish'))
    kb.row(
        KeyboardButton(text='💎 Mening ballarim'),
        KeyboardButton(text='🔗 Do‘st taklif qilish'),
    )
    kb.row(
        KeyboardButton(text='🏆 Top ranking'),
        KeyboardButton(text='📊 Mening o‘rnim'),
    )
    kb.row(
        KeyboardButton(text='💎 Ball tarixi'),
        KeyboardButton(text='🎁 Sovg‘alar'),
    )
    kb.row(
        KeyboardButton(text='🪪 Referral card'),
        KeyboardButton(text='🕘 Random tarixi'),
    )
    kb.row(
        KeyboardButton(text='📞 Bog‘lanish'),
        KeyboardButton(text='ℹ️ Mening profilim'),
    )
    return kb.as_markup(resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text='🎲 Random o‘yin'))
    kb.row(
        KeyboardButton(text='📣 Broadcast'),
        KeyboardButton(text='📊 Statistika'),
    )
    kb.row(
        KeyboardButton(text='📥 Excel export'),
        KeyboardButton(text='🏆 Admin top ranking'),
    )
    kb.row(
        KeyboardButton(text='🔎 User qidirish'),
        KeyboardButton(text='📦 G‘oliblar'),
    )
    kb.row(KeyboardButton(text='🏠 Asosiy menyu'))
    return kb.as_markup(resize_keyboard=True)


def support_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text='❌ Yakunlash'))
    return kb.as_markup(resize_keyboard=True)


def subscribe_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text='📢 Kanalga a’zo bo‘lish', url=settings.channel_url))
    kb.row(InlineKeyboardButton(text='🤖 Botga /start bosish', url=settings.shop_bot_url))
    kb.row(InlineKeyboardButton(text='✅ Tekshirish', callback_data='check_sub'))
    return kb.as_markup()


def register_keyboard(user_id: int) -> InlineKeyboardMarkup:
    sig = sign_uid(user_id)
    url = f'{settings.base_url}/register?uid={user_id}&sig={sig}'
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text='📝 Ro‘yxatdan o‘tish', url=url))
    return kb.as_markup()


def profile_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    sig = sign_uid(user_id)
    url = f'{settings.base_url}/register?uid={user_id}&sig={sig}'
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text='✏️ Ma’lumotlarni yangilash', url=url))
    kb.row(InlineKeyboardButton(text='🔗 Taklif havolam', callback_data='my_invite'))
    return kb.as_markup()


def winner_keyboard(phone: str | None, full_name: str, history_id: int) -> InlineKeyboardMarkup:
    clean_phone = ''.join(ch for ch in (phone or '') if ch.isdigit() or ch == '+')
    share_text = f'🎉 aloo random g‘olibi:\n\n👤 {full_name}\n📞 {phone or "Kiritilmagan"}'
    kb = InlineKeyboardBuilder()
    row = []
    if clean_phone:
        row.append(InlineKeyboardButton(text='📞 Qo‘ng‘iroq qilish', url=f'tel:{clean_phone}'))
    row.append(InlineKeyboardButton(text='📤 Ulashish', url=f'https://t.me/share/url?url=&text={share_text}'))
    kb.row(*row)
    kb.row(InlineKeyboardButton(text='🟡 Bog‘lanilmadi', callback_data=f'winner_status:{history_id}:pending'))
    kb.row(
        InlineKeyboardButton(text='🟢 Bog‘lanildi', callback_data=f'winner_status:{history_id}:contacted'),
        InlineKeyboardButton(text='🎁 Sovg‘a topshirildi', callback_data=f'winner_status:{history_id}:delivered'),
    )
    kb.row(InlineKeyboardButton(text='❌ Bekor qilindi', callback_data=f'winner_status:{history_id}:cancelled'))
    return kb.as_markup()


def month_name(month: int) -> str:
    return {
        1: 'Yanvar', 2: 'Fevral', 3: 'Mart', 4: 'Aprel', 5: 'May', 6: 'Iyun',
        7: 'Iyul', 8: 'Avgust', 9: 'Sentabr', 10: 'Oktabr', 11: 'Noyabr', 12: 'Dekabr',
    }[month]


def build_calendar(state) -> InlineKeyboardMarkup:
    year, month = state.year, state.month
    first_day = datetime(year, month, 1)
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    days_in_month = (next_month - first_day).days
    first_weekday = first_day.isoweekday()

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text='◀️', callback_data='cal_prev'),
        InlineKeyboardButton(text=f'{month_name(month)} {year}', callback_data='cal_ignore'),
        InlineKeyboardButton(text='▶️', callback_data='cal_next'),
    )
    kb.row(*[InlineKeyboardButton(text=d, callback_data='cal_ignore') for d in ['Du', 'Se', 'Cho', 'Pa', 'Ju', 'Sha', 'Ya']])

    row = []
    for _ in range(1, first_weekday):
        row.append(InlineKeyboardButton(text=' ', callback_data='cal_ignore'))

    for day in range(1, days_in_month + 1):
        date_str = f'{year:04d}-{month:02d}-{day:02d}'
        label = str(day)
        if state.start_date == date_str:
            label = f'🟢 {day}'
        elif state.end_date == date_str:
            label = f'🔴 {day}'
        row.append(InlineKeyboardButton(text=label, callback_data=f'cal_pick:{date_str}'))
        if len(row) == 7:
            kb.row(*row)
            row = []

    if row:
        while len(row) < 7:
            row.append(InlineKeyboardButton(text=' ', callback_data='cal_ignore'))
        kb.row(*row)

    if state.start_date and state.end_date:
        kb.row(InlineKeyboardButton(text='🎯 G‘olibni random orqali aniqlash', callback_data='random_draw'))
    kb.row(InlineKeyboardButton(text='❌ Bekor qilish', callback_data='random_cancel'))
    return kb.as_markup()
