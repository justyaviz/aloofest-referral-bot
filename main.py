import os
import json
import hmac
import hashlib
import csv
import io
from typing import Optional

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, PlainTextResponse
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# ENV
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # masalan: @aloo_uzb
BASE_URL = os.getenv("BASE_URL")  # masalan: https://xxx.up.railway.app
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")

DATA_FILE = "data.json"

# =========================
# ADMIN
# =========================
DEFAULT_ADMIN_IDS = {5465377318}
ADMIN_IDS = set(DEFAULT_ADMIN_IDS)

ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "")
for x in ADMIN_IDS_RAW.split(","):
    x = x.strip()
    if x.isdigit():
        ADMIN_IDS.add(int(x))


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# =========================
# REGIONS / DISTRICTS
# =========================
REGION_DISTRICTS = {
    "Toshkent shahri": [
        "Bektemir", "Chilonzor", "Yakkasaroy", "Mirobod", "Mirzo Ulug‘bek",
        "Olmazor", "Sergeli", "Shayxontohur", "Uchtepa", "Yunusobod", "Yashnobod"
    ],
    "Toshkent вилояти": [
        "Bekobod", "Bo‘ka", "Bo‘stonliq", "Chinoz", "Qibray", "Ohangaron",
        "Oqqo‘rg‘on", "Parkent", "Piskent", "Quyi Chirchiq", "O‘rta Chirchiq",
        "Yangiyo‘l", "Yuqori Chirchiq", "Zangiota", "Angren", "Olmaliq", "Chirchiq",
        "Nurafshon", "Bekobod shahri", "Ohangaron shahri", "Yangiyo‘l shahri"
    ],
    "Andijon": [
        "Andijon shahri", "Andijon tumani", "Asaka", "Baliqchi", "Bo‘z",
        "Buloqboshi", "Izboskan", "Jalaquduq", "Xo‘jaobod", "Marhamat",
        "Oltinko‘l", "Paxtaobod", "Qo‘rg‘ontepa", "Shahrixon", "Ulug‘nor"
    ],
    "Farg‘ona": [
        "Farg‘ona shahri", "Qo‘qon", "Marg‘ilon", "Oltiariq", "Bag‘dod",
        "Beshariq", "Buvayda", "Dang‘ara", "Farg‘ona tumani", "Furqat",
        "O‘zbekiston", "Quva", "Quvasoy", "Rishton", "So‘x", "Toshloq",
        "Uchko‘prik", "Yozyovon"
    ],
    "Namangan": [
        "Namangan shahri", "Chortoq", "Chust", "Kosonsoy", "Mingbuloq",
        "Namangan tumani", "Norin", "Pop", "To‘raqo‘rg‘on", "Uchqo‘rg‘on",
        "Uychi", "Yangiqo‘rg‘on"
    ],
    "Samarqand": [
        "Samarqand shahri", "Bulung‘ur", "Ishtixon", "Jomboy", "Kattaqo‘rg‘on",
        "Kattaqo‘rg‘on shahri", "Narpay", "Nurobod", "Oqdaryo", "Paxtachi",
        "Payariq", "Pastdarg‘om", "Qo‘shrabot", "Samarqand tumani", "Toyloq",
        "Urgut"
    ],
    "Buxoro": [
        "Buxoro shahri", "Buxoro tumani", "G‘ijduvon", "Jondor", "Kogon",
        "Kogon shahri", "Olot", "Peshku", "Qorako‘l", "Qorovulbozor",
        "Romitan", "Shofirkon", "Vobkent"
    ],
    "Qashqadaryo": [
        "Qarshi shahri", "Chiroqchi", "Dehqonobod", "G‘uzor", "Kasbi",
        "Kitob", "Koson", "Mirishkor", "Muborak", "Nishon",
        "Qamashi", "Qarshi tumani", "Shahrisabz", "Shahrisabz tumani",
        "Yakkabog‘"
    ],
    "Surxondaryo": [
        "Termiz shahri", "Angor", "Bandixon", "Boysun", "Denov",
        "Jarqo‘rg‘on", "Muzrabot", "Oltinsoy", "Qiziriq", "Qumqo‘rg‘on",
        "Sariosiyo", "Sherobod", "Sho‘rchi", "Termiz tumani", "Uzun"
    ],
    "Xorazm": [
        "Urganch shahri", "Bog‘ot", "Gurlan", "Hazorasp", "Xiva",
        "Xiva shahri", "Xonqa", "Qo‘shko‘pir", "Shovot", "Urganch tumani",
        "Yangiariq", "Yangibozor"
    ],
    "Navoiy": [
        "Navoiy shahri", "Zarafshon", "Konimex", "Karmana", "Navbahor",
        "Nurota", "Qiziltepa", "Tomdi", "Uchquduq", "Xatirchi"
    ],
    "Jizzax": [
        "Jizzax shahri", "Arnasoy", "Baxmal", "Do‘stlik", "Forish",
        "G‘allaorol", "Jizzax tumani", "Mirzacho‘l", "Paxtakor",
        "Yangiobod", "Zafarobod", "Zarbdor", "Zomin"
    ],
    "Sirdaryo": [
        "Guliston shahri", "Boyovut", "Guliston tumani", "Mirzaobod",
        "Oqoltin", "Sardoba", "Sayxunobod", "Shirin", "Sirdaryo",
        "Xovos", "Yangiyer"
    ],
    "Qoraqalpog‘iston": [
        "Nukus shahri", "Amudaryo", "Beruniy", "Chimboy", "Ellikqal’a",
        "Kegeyli", "Mo‘ynoq", "Nukus tumani", "Qanliko‘l", "Qo‘ng‘irot",
        "Qorao‘zak", "Shumanay", "Taxtako‘pir", "To‘rtko‘l", "Xo‘jayli"
    ]
}

REGION_OPTIONS = sorted(REGION_DISTRICTS.keys())


# =========================
# STORAGE
# =========================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(data, user_id: int):
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "ref_by": None,
            "refs": 0,
            "joined": False,
            "name": "",
            "surname": "",
            "phone": "",
            "region": "",
            "district": "",
        }
    return data["users"][uid]


# =========================
# HELPERS
# =========================
def sign_uid(uid: int) -> str:
    msg = str(uid).encode()
    return hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()


def verify_uid(uid: int, sig: str) -> bool:
    return hmac.compare_digest(sign_uid(uid), sig or "")


def full_name(info: dict, fallback: str = "Ishtirokchi") -> str:
    name = (info.get("name") or "").strip()
    surname = (info.get("surname") or "").strip()
    full = (name + " " + surname).strip()
    return full if full else fallback


def is_registered(u: dict) -> bool:
    return bool(
        (u.get("name") or "").strip()
        and (u.get("surname") or "").strip()
        and (u.get("phone") or "").strip()
    )


def build_sorted_items(data):
    users = data.get("users", {})
    items = []
    for uid, info in users.items():
        refs = int(info.get("refs", 0) or 0)
        items.append(
            (
                int(uid),
                full_name(info, fallback=f"ID:{uid}"),
                refs,
                (info.get("phone") or "").strip(),
            )
        )
    items.sort(key=lambda x: x[2], reverse=True)
    return items


# =========================
# UI TEXTS
# =========================
RULES_TEXT = (
    "🎯 Sizda 2 xil yutish imkoniyati bor:\n\n"
    "1️⃣ TOP 5 ga kirish\n"
    "🎁 TOP 5 talik uchun sovg‘alar keyinroq e'lon qilinadi.\n"
    "Ko‘proq do‘st taklif qiling va qimmatbaho sovg‘alardan birini yutib oling!\n\n"
    "2️⃣ Random o‘yini\n"
    "Kamida 5 ta do‘st taklif qiling va random o‘yinda ishtirok eting.\n\n"
    "📊 Kanalimizga 5 ta odam qo‘shgan barcha ishtirokchilar orasidan "
    "har hafta RANDOM orqali 1 ta sovg‘a taqdim qilinadi 🤩\n\n"
    "📌 Konkurs qoidalari:\n"
    "• Do‘stlaringiz sizning linkingiz orqali botga kirishi kerak\n"
    "• Kanalga obuna bo‘lishi shart\n"
    "• Kanalni tark etganlar hisobga olinmaydi\n\n"
    "👇 Quyidagi tugmalar orqali konkursni kuzatib boring"
)

GIFTS_TEXT = (
    "🎯 Sizda 2 xil yutish imkoniyati bor:\n\n"
    "1️⃣ TOP 5 ga kirish\n"
    "🎁 TOP 5 talik uchun sovg‘alar keyinroq e'lon qilinadi.\n"
    "Ko‘proq do‘st taklif qiling va qimmatbaho sovg‘alardan birini yutib oling!\n\n"
    "2️⃣ Random o‘yini\n"
    "Kamida 5 ta do‘st taklif qiling va random o‘yinda ishtirok eting.\n\n"
    "📊 Kanalimizga 5 ta odam qo‘shgan barcha ishtirokchilar orasidan "
    "har hafta RANDOM orqali 1 ta sovg‘a taqdim qilinadi 🤩"
)

MENU_KB = ReplyKeyboardMarkup(
    [
        ["Mening shaxsiy linkim 🔗", "Sovg'alar 🎁"],
        ["TOP 10🏆", "Mening hisobim 📑"],
        ["Qo'llanma 🗂"],
    ],
    resize_keyboard=True
)

ADMIN_KB = ReplyKeyboardMarkup(
    [
        ["📊 Statistika", "🏆 TOP 10 (admin)"],
        ["🏅 TOP 50 (admin)", "🔎 User qidirish"],
        ["📢 Broadcast", "📥 Export CSV"],
        ["⬅️ Oddiy menyu"],
    ],
    resize_keyboard=True
)


# =========================
# TELEGRAM COMMANDS
# =========================
async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Sizning ID: {update.effective_user.id}")


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Siz admin emassiz.")
        return
    await update.message.reply_text("👑 Admin panel", reply_markup=ADMIN_KB)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["admin_wait_broadcast"] = False
    context.user_data["admin_wait_search"] = False
    await update.message.reply_text(
        "✅ Bekor qilindi.",
        reply_markup=ADMIN_KB if is_admin(update.effective_user.id) else MENU_KB
    )


# =========================
# USER FLOW
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()
    u = get_user(data, user.id)

    if context.args:
        ref_id = context.args[0]
        if ref_id.isdigit() and int(ref_id) != user.id and u["ref_by"] is None:
            u["ref_by"] = int(ref_id)
            save_data(data)

    if is_admin(user.id):
        await update.message.reply_text("👑 Admin panel", reply_markup=ADMIN_KB)
        return

    if is_registered(u):
        await update.message.reply_text(RULES_TEXT, reply_markup=MENU_KB)
        return

    kb = [
        [InlineKeyboardButton("✅📺 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check")],
    ]

    text = (
        "🎉 Kutib oling aloo'dan MEGA KONKURS - aloofest\n\n"
        "🎯 Sizda 2 xil yutish imkoniyati bor:\n\n"
        "1️⃣ TOP 5 ga kirish\n"
        "🎁 TOP 5 talik uchun sovg‘alar keyinroq e'lon qilinadi.\n"
        "Ko‘proq do‘st taklif qiling va qimmatbaho sovg‘alardan birini yutib oling!\n\n"
        "2️⃣ Random o‘yini\n"
        "Kamida 5 ta do‘st taklif qiling va random o‘yinda ishtirok eting.\n\n"
        "📊 Kanalimizga 5 ta odam qo‘shgan barcha ishtirokchilar orasidan "
        "har hafta RANDOM orqali 1 ta sovg‘a taqdim qilinadi 🤩\n\n"
        "📺 Birinchi qadam: kanalimizga obuna bo'ling 👇"
    )

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))


async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user

    data = load_data()
    u = get_user(data, user.id)

    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user.id)
        is_joined = member.status in ("member", "administrator", "creator")
    except Exception:
        is_joined = False

    if not is_joined:
        kb = [
            [InlineKeyboardButton("✅📺 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check")],
        ]
        await q.edit_message_text(
            "❌ Hali kanalga a’zo bo‘lmagansiz.\n\nAvval kanalga a’zo bo‘ling, keyin yana tekshiring 👇",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return

    if not u["joined"]:
        u["joined"] = True
        if u["ref_by"]:
            ref_user = get_user(data, u["ref_by"])
            ref_user["refs"] += 1
        save_data(data)

    sig = sign_uid(user.id)
    reg_link = f"{BASE_URL}/register?uid={user.id}&sig={sig}"
    kb2 = [[InlineKeyboardButton("📝 Ro‘yxatdan o‘tish", url=reg_link)]]

    await q.edit_message_text(
        "✅ Obuna tasdiqlandi!\n\n📝 Endi konkursga ro‘yxatdan o‘tish uchun tugmani bosing 👇",
        reply_markup=InlineKeyboardMarkup(kb2),
    )


async def got_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.contact:
        return

    user_id = update.effective_user.id
    contact = update.message.contact

    if contact.user_id and contact.user_id != user_id:
        await update.message.reply_text(
            "❌ Iltimos, faqat o‘zingizning raqamingizni yuboring.",
            reply_markup=MENU_KB
        )
        return

    phone = contact.phone_number

    data = load_data()
    u = get_user(data, user_id)
    u["phone"] = phone
    save_data(data)

    await update.message.reply_text(RULES_TEXT, reply_markup=MENU_KB)


# =========================
# USER MENU
# =========================
async def my_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    me = await context.bot.get_me()
    personal_link = f"https://t.me/{me.username}?start={user_id}"

    caption = (
        "🎯 Sizda 2 xil yutish imkoniyati bor:\n\n"
        "1️⃣ TOP 5 ga kirish\n"
        "🎁 TOP 5 talik uchun sovg‘alar keyinroq e'lon qilinadi.\n"
        "Ko‘proq do‘st taklif qiling va qimmatbaho sovg‘alardan birini yutib oling!\n\n"
        "2️⃣ Random o‘yini\n"
        "Kamida 5 ta do‘st taklif qiling va random o‘yinda ishtirok eting.\n\n"
        "📊 Kanalimizga 5 ta odam qo‘shgan barcha ishtirokchilar orasidan "
        "har hafta RANDOM orqali 1 ta sovg‘a taqdim qilinadi 🤩\n\n"
        "Konkursda qatnashish uchun quyidagi havola orqali o'ting 👇👇\n\n"
        f"{personal_link}"
    )

    photo_path = "static/post.jpg"
    if os.path.exists(photo_path):
        with open(photo_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, caption=caption, reply_markup=MENU_KB)
    else:
        await update.message.reply_text(caption, reply_markup=MENU_KB)


async def my_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    u = get_user(data, user_id)

    me = await context.bot.get_me()
    personal_link = f"https://t.me/{me.username}?start={user_id}"

    refs = int(u.get("refs", 0) or 0)
    if refs >= 5:
        random_status = "✅ Siz RANDOM o'yinda qatnashyapsiz"
    else:
        random_status = f"❌ Random uchun yana {5 - refs} ta do'st kerak"

    text = (
        "📑 Mening hisobim\n\n"
        f"👤 Ism: {(u.get('name') or '').strip() or '-'}\n"
        f"👤 Familiya: {(u.get('surname') or '').strip() or '-'}\n"
        f"📞 Tel: {(u.get('phone') or '').strip() or '-'}\n"
        f"📍 Viloyat: {(u.get('region') or '').strip() or '-'}\n"
        f"🏙 Tuman/Shahar: {(u.get('district') or '').strip() or '-'}\n\n"
        f"👥 Taklif qilganlar: {refs} ta\n"
        f"🎲 Random holati: {random_status}\n"
        f"🔗 Shaxsiy link: {personal_link}"
    )
    await update.message.reply_text(text, reply_markup=MENU_KB)


async def top10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = load_data()
    users = data.get("users", {})

    items = []
    for uid, info in users.items():
        refs = int(info.get("refs", 0) or 0)
        items.append((int(uid), full_name(info, fallback=f"ID:{uid}"), refs))

    items.sort(key=lambda x: x[2], reverse=True)

    top = items[:10]
    medals = ["🥇", "🥈", "🥉"]
    nums = ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    lines = ["🏆 TOP 10 ISHTIROKCHILAR\n"]
    for i, (uid, name, refs) in enumerate(top):
        prefix = medals[i] if i < 3 else nums[i - 3]
        lines.append(f"{prefix} {name} - {refs} ta")

    my_rank = None
    my_refs = 0
    for idx, (uid, name, refs) in enumerate(items, start=1):
        if uid == user_id:
            my_rank = idx
            my_refs = refs
            break

    if my_rank is None:
        my_rank = len(items) + 1
        my_refs = 0

    lines.append("\n")
    lines.append(f"Sizning o'rningiz: {my_rank}-o'rin ({my_refs} ta)\n")
    lines.append(
        "Sizning urinishingiz yomon emas yanada teparoq ko'tarilish uchun "
        "shaxsiy linkingizni tanishlaringizga yuboring va ular kanalga qo'shilishi kerak, OMAD sizga 😊"
    )

    await update.message.reply_text("\n".join(lines), reply_markup=MENU_KB)


async def gifts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(GIFTS_TEXT, reply_markup=MENU_KB)


async def guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_TEXT, reply_markup=MENU_KB)


# =========================
# ADMIN ACTIONS
# =========================
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    data = load_data()
    users = data.get("users", {})

    total = len(users)
    joined = sum(1 for _, u in users.items() if u.get("joined"))
    registered = sum(1 for _, u in users.items() if (u.get("name") or "").strip() and (u.get("surname") or "").strip())
    with_phone = sum(1 for _, u in users.items() if (u.get("phone") or "").strip())
    random_ready = sum(1 for _, u in users.items() if int(u.get("refs", 0) or 0) >= 5)

    text = (
        "📊 Admin Statistika\n\n"
        f"👥 Jami user: {total}\n"
        f"✅ Kanalga a’zo bo‘lgan: {joined}\n"
        f"📝 Ro‘yxatdan o‘tgan: {registered}\n"
        f"📞 Telefon yuborgan: {with_phone}\n"
        f"🎲 Randomga chiqqanlar (5+): {random_ready}\n"
    )
    await update.message.reply_text(text, reply_markup=ADMIN_KB)


async def admin_top10(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    data = load_data()
    items = build_sorted_items(data)[:10]
    lines = ["🏆 TOP 10 (admin)\n"]
    for i, (uid, name, refs, phone) in enumerate(items, start=1):
        extra = f" | 📞 {phone}" if phone else ""
        lines.append(f"{i}) {name} — {refs} ta{extra}")
    await update.message.reply_text("\n".join(lines), reply_markup=ADMIN_KB)


async def admin_top50(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    data = load_data()
    items = build_sorted_items(data)[:50]
    lines = ["🏅 TOP 50 (admin)\n"]
    for i, (uid, name, refs, phone) in enumerate(items, start=1):
        lines.append(f"{i}) {name} — {refs} ta")
    await update.message.reply_text("\n".join(lines), reply_markup=ADMIN_KB)


async def admin_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["admin_wait_search"] = True
    await update.message.reply_text(
        "🔎 Qidirish uchun ID yoki ism/familiya yoki telefon yozing.\nBekor qilish: /cancel",
        reply_markup=ADMIN_KB
    )


async def admin_search_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.user_data.get("admin_wait_search"):
        return
    if not update.message or not update.message.text:
        return

    q = update.message.text.strip().lower()
    context.user_data["admin_wait_search"] = False

    data = load_data()
    users = data.get("users", {})

    found = []
    for uid, info in users.items():
        uid_s = str(uid)
        name = (info.get("name") or "").strip()
        surname = (info.get("surname") or "").strip()
        phone = (info.get("phone") or "").strip()
        refs = int(info.get("refs", 0) or 0)
        region = (info.get("region") or "").strip()
        district = (info.get("district") or "").strip()

        hay = f"{uid_s} {name} {surname} {phone} {region} {district}".lower()
        if q in hay:
            found.append((uid_s, name, surname, phone, refs, region, district))

    if not found:
        await update.message.reply_text("❌ Hech narsa topilmadi.", reply_markup=ADMIN_KB)
        return

    found = found[:15]
    lines = ["✅ Topilganlar (max 15):\n"]
    for uid_s, name, surname, phone, refs, region, district in found:
        full = (name + " " + surname).strip() or f"ID:{uid_s}"
        lines.append(
            f"• {full} | 📞 {phone or '-'} | 🔥 {refs} ta | 📍 {region or '-'} / {district or '-'} | 🆔 {uid_s}"
        )

    await update.message.reply_text("\n".join(lines), reply_markup=ADMIN_KB)


async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["admin_wait_broadcast"] = True
    await update.message.reply_text(
        "📢 Hammaga yuboriladigan MATNni yozing.\n\nBekor qilish: /cancel",
        reply_markup=ADMIN_KB,
    )


async def admin_broadcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.user_data.get("admin_wait_broadcast"):
        return
    if not update.message or not update.message.text:
        return

    text = update.message.text
    context.user_data["admin_wait_broadcast"] = False

    data = load_data()
    users = data.get("users", {})

    ok = 0
    fail = 0
    for uid_str in users.keys():
        try:
            await context.bot.send_message(chat_id=int(uid_str), text=text)
            ok += 1
        except Exception:
            fail += 1

    await update.message.reply_text(
        f"✅ Yuborildi: {ok}\n❌ Yetmadi: {fail}",
        reply_markup=ADMIN_KB
    )


async def admin_export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    data = load_data()
    users = data.get("users", {})

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["user_id", "name", "surname", "phone", "region", "district", "refs", "joined", "ref_by"])

    for uid, info in users.items():
        writer.writerow([
            uid,
            (info.get("name") or "").strip(),
            (info.get("surname") or "").strip(),
            (info.get("phone") or "").strip(),
            (info.get("region") or "").strip(),
            (info.get("district") or "").strip(),
            int(info.get("refs", 0) or 0),
            bool(info.get("joined")),
            info.get("ref_by") or "",
        ])

    content = output.getvalue().encode("utf-8")
    await update.message.reply_document(
        document=content,
        filename="aloofest_users.csv",
        caption="📥 Export CSV",
        reply_markup=ADMIN_KB
    )


async def admin_to_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("⬅️ Oddiy menyu", reply_markup=MENU_KB)


# =========================
# FASTAPI
# =========================
app = FastAPI()
tg_app: Optional[Application] = None

region_options_html = "\n".join(
    [f'<option value="{r}">{r}</option>' for r in REGION_OPTIONS]
)

FORM_HTML = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Ro‘yxatdan o‘tish</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      background: #7fd1c7;
      margin: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: 20px;
    }}
    .card {{
      background: #fff;
      max-width: 420px;
      width: 100%;
      border-radius: 18px;
      padding: 26px;
      box-shadow: 0 12px 40px rgba(0,0,0,.18);
    }}
    h2 {{ margin: 0 0 10px 0; }}
    p {{ margin: 0 0 18px 0; color: #333; }}
    label {{ display: block; margin: 14px 0 6px 0; font-weight: 700; }}
    input, select {{
      width: 100%;
      padding: 12px 12px;
      border: 1px solid #ddd;
      border-radius: 12px;
      font-size: 16px;
      box-sizing: border-box;
      background: #fff;
    }}
    button {{
      margin-top: 18px;
      width: 100%;
      padding: 14px;
      border: 0;
      border-radius: 14px;
      background: #6fc6bb;
      font-size: 16px;
      font-weight: 800;
      cursor: pointer;
    }}
    .small {{
      font-size: 12px;
      color: #666;
      margin-top: 10px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h2>🎉 Konkursga ro‘yxatdan o‘tish</h2>
    <p>Ma’lumotlaringizni to‘ldiring</p>
    <form method="POST" action="/register">
      <input type="hidden" name="uid" value="{{uid}}"/>
      <input type="hidden" name="sig" value="{{sig}}"/>

      <label>Ismingiz *</label>
      <input name="name" required placeholder="Ismingizni kiriting"/>

      <label>Familiyangiz *</label>
      <input name="surname" required placeholder="Familiyangizni kiriting"/>

      <label>Viloyat *</label>
      <select id="region" name="region" required>
        <option value="">Viloyat tanlang</option>
        {region_options_html}
      </select>

      <label>Tuman / Shahar *</label>
      <select id="district" name="district" required>
        <option value="">Avval viloyat tanlang</option>
      </select>

      <button type="submit">Ro‘yxatdan o‘tish</button>
      <div class="small">Yuborgandan keyin Telegram botga qayting.</div>
    </form>
  </div>

  <script>
    const regionDistricts = {json.dumps(REGION_DISTRICTS, ensure_ascii=False)};
    const regionSelect = document.getElementById('region');
    const districtSelect = document.getElementById('district');

    regionSelect.addEventListener('change', function() {{
      const region = this.value;
      districtSelect.innerHTML = '';

      if (!region || !regionDistricts[region]) {{
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Avval viloyat tanlang';
        districtSelect.appendChild(option);
        return;
      }}

      const first = document.createElement('option');
      first.value = '';
      first.textContent = 'Tuman / Shahar tanlang';
      districtSelect.appendChild(first);

      regionDistricts[region].forEach(function(d) {{
        const option = document.createElement('option');
        option.value = d;
        option.textContent = d;
        districtSelect.appendChild(option);
      }});
    }});
  </script>
</body>
</html>
"""

@app.get("/", response_class=PlainTextResponse)
async def root():
    return "ok"

@app.get("/register", response_class=HTMLResponse)
async def register_get(uid: int, sig: str):
    if not verify_uid(uid, sig):
        return HTMLResponse("<h3>❌ Noto‘g‘ri link</h3>", status_code=403)

    html = FORM_HTML.replace("{uid}", str(uid)).replace("{sig}", sig)
    return HTMLResponse(html)

@app.post("/register", response_class=HTMLResponse)
async def register_post(
    uid: int = Form(...),
    sig: str = Form(...),
    name: str = Form(...),
    surname: str = Form(...),
    region: str = Form(...),
    district: str = Form(...)
):
    if not verify_uid(uid, sig):
        return HTMLResponse("<h3>❌ Noto‘g‘ri link</h3>", status_code=403)

    if region not in REGION_DISTRICTS:
        return HTMLResponse("<h3>❌ Noto‘g‘ri viloyat</h3>", status_code=400)

    if district not in REGION_DISTRICTS[region]:
        return HTMLResponse("<h3>❌ Noto‘g‘ri tuman/shahar</h3>", status_code=400)

    data = load_data()
    u = get_user(data, uid)
    u["name"] = name.strip()
    u["surname"] = surname.strip()
    u["region"] = region.strip()
    u["district"] = district.strip()
    save_data(data)

    contact_kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Raqamimni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    if tg_app:
        await tg_app.bot.send_message(
            chat_id=uid,
            text="✅ Ma'lumotlar qabul qilindi!\n\nEndi telefon raqamingizni yuboring 👇",
            reply_markup=contact_kb
        )

    bot_username = (await tg_app.bot.get_me()).username if tg_app else "aloofest_bot"
    return HTMLResponse(
        f"""
        <h3>✅ Tayyor!</h3>
        <p>Telegramga qayting — bot sizdan telefon raqamingizni so‘raydi.</p>
        <p><a href="https://t.me/{bot_username}">➡️ Telegramga qaytish</a></p>
        """
    )

@app.post("/telegram")
async def telegram_webhook(request: Request):
    payload = await request.json()
    update = Update.de_json(payload, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    global tg_app
    if not BOT_TOKEN or not CHANNEL_USERNAME or not BASE_URL:
        raise RuntimeError("BOT_TOKEN / CHANNEL_USERNAME / BASE_URL missing in Railway Variables")

    tg_app = Application.builder().token(BOT_TOKEN).build()

    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CommandHandler("id", cmd_id))
    tg_app.add_handler(CommandHandler("admin", cmd_admin))
    tg_app.add_handler(CommandHandler("cancel", cancel))

    tg_app.add_handler(CallbackQueryHandler(check_join, pattern="^check$"))
    tg_app.add_handler(MessageHandler(filters.CONTACT, got_contact))

    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Mening shaxsiy linkim 🔗$"), my_link))
    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Mening hisobim 📑$"), my_account))
    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^TOP 10🏆$"), top10))
    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Sovg'alar 🎁$"), gifts))
    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^Qo'llanma 🗂$"), guide))

    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📊 Statistika$"), admin_stats))
    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🏆 TOP 10 \\(admin\\)$"), admin_top10))
    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🏅 TOP 50 \\(admin\\)$"), admin_top50))
    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🔎 User qidirish$"), admin_search_start))
    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📢 Broadcast$"), admin_broadcast_start))
    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📥 Export CSV$"), admin_export_csv))
    tg_app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^⬅️ Oddiy menyu$"), admin_to_user_menu))

    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_search_receive))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_receive))

    await tg_app.initialize()
    await tg_app.start()
    await tg_app.bot.set_webhook(f"{BASE_URL}/telegram")

@app.on_event("shutdown")
async def on_shutdown():
    if tg_app:
        await tg_app.stop()
        await tg_app.shutdown()
