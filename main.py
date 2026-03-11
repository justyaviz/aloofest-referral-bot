import asyncio
import io
import random
import calendar
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    BufferedInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from openpyxl import Workbook

from config import (
    BOT_TOKEN,
    CHANNEL_USERNAME,
    ADMIN_IDS,
    INSTAGRAM_RULE_TEXT,
    INSTAGRAM_MAIN_URL,
)
from database import db
from keyboards import (
    start_keyboard,
    rules_keyboard,
    subscribe_keyboard,
    register_keyboard,
    main_menu,
    admin_menu,
    phone_keyboard,
)
from web_server import setup_web_server


bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Shu joyga o'zingizning referral video file_id ni yozing
REFERRAL_VIDEO_FILE_ID = "BU_YERGA_VIDEO_FILE_ID"


class BanState(StatesGroup):
    waiting_user = State()


class UnbanState(StatesGroup):
    waiting_user = State()


class SearchState(StatesGroup):
    waiting_query = State()


class DirectMessageState(StatesGroup):
    waiting_user = State()
    waiting_message = State()


class BroadcastState(StatesGroup):
    waiting_message = State()


class AdState(StatesGroup):
    waiting_title = State()
    waiting_body = State()


class PrizeState(StatesGroup):
    waiting_id = State()
    waiting_place = State()
    waiting_title = State()
    waiting_desc = State()


class RandomState(StatesGroup):
    waiting_start = State()
    waiting_end = State()
    ready_confirm = State()


START_TEXT = """
🎉 Kutib oling, “aloo”dan navbatdagi yirik yutuqli loyiha — <b>“aloofest” MEGA KONKURSI</b>!

Ushbu mega konkurs kirib kelayotgan <b>Ramazon Hayiti</b> munosabati bilan “aloo” tomonidan siz azizlar uchun hayitlik tuhfa sifatida tashkil etilmoqda. 💙

Sizda <b>2 xil usulda g‘olib bo‘lish</b> imkoniyati bor:

1️⃣ <b>TOP 3 mega konkurs</b>
2️⃣ <b>Haftalik random o‘yinlari</b>

🎁 <b>Hayit bayrami mega konkurs sovg‘alari:</b>

🥇 1-o‘rin — <b>Redmi Robot Mop 2</b>
🥈 2-o‘rin — <b>Novey Senat SC1 Red</b> telefoni
🥉 3-o‘rin — <b>Zamonaviy elektr choynak</b>

🎲 <b>Haftalik random o‘yinlari:</b>
Har hafta davomida kamida <b>3+ do‘stingizni taklif qilib</b>, <b>15+ ball</b> to‘plash orqali random o‘yinida ishtirok eta olasiz.

Haftalik o‘yinlarda quyidagi qimmatbaho sovg‘alar o‘ynaladi:

• AirPods
• Telefon
• Smartwatch
• Planshet
• va boshqa qimmatbaho sovg‘alar

📅 G‘oliblar bot orqali hamda <b>@aloo_uzb</b> kanalida e’lon qilinadi.

🍀 Omad sizga yor bo‘lsin!
"""

RULES_TEXT = f"""
🏆 <b>“aloofest” MEGA KONKURSI qoidalari</b>

Ushbu konkursda g‘olib bo‘lishning <b>2 xil turi</b> mavjud:

1️⃣ <b>TOP 3 mega konkurs</b>
2️⃣ <b>Haftalik random o‘yinlari</b>

🎯 <b>Ball tizimi:</b>
Har bir taklif qilingan do‘st uchun sizga <b>+5 ball</b> beriladi.

Misollar:
1 do‘st = 5 ball
3 do‘st = 15 ball
5 do‘st = 25 ball
10 do‘st = 50 ball

🥇 <b>TOP 3 mega konkurs</b>
Eng ko‘p ball to‘plagan ishtirokchilar hayit bayrami mega konkursining asosiy g‘oliblari bo‘ladi.

🎁 Sovg‘alar:
1-o‘rin — Redmi Robot Mop 2
2-o‘rin — Novey Senat SC1 Red telefoni
3-o‘rin — Zamonaviy elektr choynak

🎲 <b>Haftalik random o‘yinlari</b>
Har hafta davomida <b>kamida 3+ do‘st taklif qilib</b>, <b>15+ ball</b> to‘plagan ishtirokchilar random o‘yinida qatnasha oladi.

Haftalik random sovg‘alariga quyidagilar kiradi:
• AirPods
• Telefon
• Smartwatch
• Planshet
• va boshqa qimmatbaho sovg‘alar

📋 <b>Ishtirok etish uchun:</b>
• Telegram kanalga obuna bo‘ling
• Ro‘yxatdan o‘ting
• Do‘stlaringizni taklif qiling
• Ball to‘plang va g‘olib bo‘ling

❗ Instagram bo‘yicha shartlar ham majburiy hisoblanadi. Agar ishtirokchi Instagram shartlarini bajarmagan bo‘lsa, g‘oliblik tasdiqlanmaydi.

📸 Instagram bo‘yicha shart:
{INSTAGRAM_RULE_TEXT}
"""

ABOUT_TEXT = f"""
ℹ️ <b>“aloofest” MEGA KONKURSI haqida</b>

“aloofest” — bu kirib kelayotgan <b>Ramazon Hayiti</b> munosabati bilan “aloo” tomonidan tashkil etilgan maxsus hayitlik mega konkursdir.

Bu konkursda siz 2 xil usulda g‘olib bo‘lishingiz mumkin:

1️⃣ <b>TOP 3 mega konkurs</b>
Eng ko‘p ball to‘plagan ishtirokchilar asosiy hayit sovg‘alarini yutadi.

2️⃣ <b>Haftalik random o‘yinlari</b>
Har hafta 3+ do‘st taklif qilib, 15+ ball yig‘ganlar random o‘yinida qatnashadi.

🎁 Sovg‘alar orasida:
• Redmi Robot Mop 2
• Novey Senat SC1 Red telefoni
• Zamonaviy elektr choynak
• AirPods
• Telefon
• Smartwatch
• Planshet
• va boshqa qimmatbaho sovg‘alar mavjud

📢 Barcha yangiliklar bot orqali va @aloo_uzb kanalida e’lon qilinadi.
"""

GUIDE_TEXT = """
🎉 <b>Tabriklaymiz!</b>

Siz “aloofest” mega konkursida muvaffaqiyatli ro‘yxatdan o‘tdingiz va boshlang‘ich <b>ball</b> qo‘lga kiritdingiz. ✅

📌 Endi keyingi bosqich juda muhim:
quyidagi <b>qisqa yo‘riqnoma</b> orqali konkursda qanday qatnashish, ball yig‘ish va g‘olib bo‘lish tartibini ko‘rib chiqing.

🎯 Sizda 2 xil imkoniyat bor:
• TOP 3 mega konkursda g‘olib bo‘lish
• Haftalik random o‘yinlarida sovg‘a yutish

📹 <b>Qisqa yo‘riqnoma:</b>
• konkursda qanday ishtirok etish
• do‘st taklif qilib ball yig‘ish
• TOP 3 ga chiqish
• haftalik random o‘yinida qatnashish

👥 Endi do‘stlaringizni taklif qiling
