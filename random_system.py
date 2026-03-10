from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from database import db
from keyboards import winner_keyboard
from utils import esc, is_channel_member


@dataclass
class RandomPicker:
    start_date: str | None = None
    end_date: str | None = None
    year: int = 2026
    month: int = 1


RANDOM_STATE: dict[int, RandomPicker] = {}

STATUS_MAP = {
    'pending': '🟡 Bog‘lanilmadi',
    'contacted': '🟢 Bog‘lanildi',
    'delivered': '🎁 Sovg‘a topshirildi',
    'cancelled': '❌ Bekor qilindi',
}


async def run_random_draw(callback: CallbackQuery, bot: Bot) -> None:
    admin_id = callback.from_user.id
    state = RANDOM_STATE.get(admin_id)
    if not state or not state.start_date or not state.end_date:
        await callback.answer('Avval sana oralig‘ini tanlang', show_alert=True)
        return

    candidates = await db.get_random_candidates(state.start_date, state.end_date)
    eligible = []
    for user in candidates:
        if await is_channel_member(user['user_id']):
            eligible.append(user)

    if not eligible:
        await callback.message.edit_text(
            f'😔 {state.start_date} dan {state.end_date} gacha ro‘yxatdan o‘tgan va kanalga a’zo bo‘lgan ishtirokchilar topilmadi.'
        )
        await callback.answer('Ishtirokchi topilmadi')
        return

    await callback.answer('Random boshlandi')
    progress_msg = await callback.message.edit_text(
        '🎲 <b>G‘olib random orqali aniqlanmoqda...</b>\n\n⏳ Loading: <b>0%</b>'
    )

    steps = list(range(0, 101, 5))
    sleep_time = 45 / (len(steps) - 1)
    for p in steps[1:]:
        await asyncio.sleep(sleep_time)
        try:
            await progress_msg.edit_text(
                '🎲 <b>G‘olib random orqali aniqlanmoqda...</b>\n\n'
                f'⏳ Loading: <b>{p}%</b>'
            )
        except TelegramBadRequest:
            pass

    winner = random.choice(eligible)
    full_name = f"{winner['first_name'] or ''} {winner['last_name'] or ''}".strip() or 'Noma’lum'
    phone = winner['phone'] or 'Kiritilmagan'
    region = winner['region'] or 'Kiritilmagan'
    district = winner['district'] or 'Kiritilmagan'
    diamonds = winner['diamonds'] or 0

    history_id = await db.save_random_history(
        winner_user_id=winner['user_id'],
        winner_name=full_name,
        winner_phone=phone,
        winner_region=region,
        winner_district=district,
        winner_diamonds=diamonds,
        start_date=state.start_date,
        end_date=state.end_date,
        participants_count=len(eligible),
        admin_id=admin_id,
    )

    text = (
        '🏆 <b>G‘olib aniqlandi!</b>\n\n'
        f'👤 <b>Ism-familiya:</b> {esc(full_name)}\n'
        f'📞 <b>Telefon raqami:</b> {esc(phone)}\n'
        f'📍 <b>Hudud:</b> {esc(region)}, {esc(district)}\n'
        f'💎 <b>Balli:</b> {diamonds}\n\n'
        f'📅 <b>Davr:</b> {state.start_date} — {state.end_date}\n'
        f'👥 <b>Ishtirokchilar soni:</b> {len(eligible)}\n'
        f'📦 <b>Status:</b> {STATUS_MAP["pending"]}'
    )

    await progress_msg.edit_text(
        text,
        reply_markup=winner_keyboard(phone, full_name, history_id),
    )

    try:
        await bot.send_message(
            winner['user_id'],
            '🎉 <b>Tabriklaymiz!</b>\n\nSiz aloo random o‘yinida g‘olib bo‘ldingiz. Tez orada siz bilan bog‘lanamiz. 📞',
        )
    except Exception:
        pass

    await db.add_admin_log(admin_id, 'random_draw', f'winner={winner["user_id"]}; range={state.start_date}:{state.end_date}')
    RANDOM_STATE.pop(admin_id, None)
