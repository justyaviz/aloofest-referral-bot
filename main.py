import os, json, hmac, hashlib
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
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

# ====== ENV ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # masalan: @aloofest
BASE_URL = os.getenv("BASE_URL")  # masalan: https://xxx.up.railway.app
SECRET_KEY = os.getenv("SECRET_KEY", "change-me")  # o'zingiz qo'ying

DATA_FILE = "data.json"

# ====== STORAGE ======
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
        data["users"][uid] = {"ref_by": None, "refs": 0, "joined": False, "name": "", "surname": "", "phone": ""}
    return data["users"][uid]

# ====== SIGN/VERIFY (tampering bo'lmasin) ======
def sign_uid(uid: int) -> str:
    msg = str(uid).encode()
    return hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()

def verify_uid(uid: int, sig: str) -> bool:
    return hmac.compare_digest(sign_uid(uid), sig or "")

# ====== TELEGRAM HANDLERS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()
    u = get_user(data, user.id)

    # referral: /start <ref_id>
    if context.args:
        ref_id = context.args[0]
        if ref_id.isdigit() and int(ref_id) != user.id and u["ref_by"] is None:
            u["ref_by"] = int(ref_id)

    save_data(data)

    kb = [
        [InlineKeyboardButton("✅📺 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
        [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check")],
    ]

    text = (
        "🎉  Kutib oling aloo'dan MEGA KONKURS - aloofest\n\n"
        "Keling, endi sovg'alar ro'yxati bilan tanishtiraman👇\n\n"
        "🎁 TOP 3 talik uchun Sovg'alar:\n"
        "Ko'proq do'stingizni taklif qiling va qimmatbaho sovg'alardan birini yutib oling!\n\n"
        "🥇 1-o‘rin — Tecno Spark 30C smartfoni\n"
        "🥈 2-o‘rin — Mi kolonkasi\n"
        "🥉 3-o‘rin — Zamonaviy ryugzak\n\n"
        "📅 Sovg'alar g'oliblari 9-mart kuni soat 14:00da hammaning ko'z o'ngida,\n"
        "JONLI EFIR orqali aniqlaymiz.\n\n"
        "Hammaga omad 🍀\n\n"
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

    if is_joined:
        # bir marta joined qilib qo'yamiz
        if not u["joined"]:
            u["joined"] = True
            if u["ref_by"]:
                ref_user = get_user(data, u["ref_by"])
                ref_user["refs"] += 1
            save_data(data)

        # ro'yxatdan o'tish linki (uid+sig bilan)
        sig = sign_uid(user.id)
        reg_link = f"{BASE_URL}/register?uid={user.id}&sig={sig}"

        kb2 = [
            [InlineKeyboardButton("📝 Ro‘yxatdan o‘tish", url=reg_link)],
        ]

        await q.edit_message_text(
            "✅ Obuna tasdiqlandi!\n\n"
            "📝 Endi konkursga ro‘yxatdan o‘tish uchun tugmani bosing 👇",
            reply_markup=InlineKeyboardMarkup(kb2),
        )
    else:
        kb = [
            [InlineKeyboardButton("✅📺 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")],
            [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check")],
        ]
        await q.edit_message_text(
            "❌ Hali kanalga a’zo bo‘lmagansiz.\n\n"
            "Avval kanalga a’zo bo‘ling, keyin yana tekshiring 👇",
            reply_markup=InlineKeyboardMarkup(kb),
        )

async def got_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.contact:
        return

    user_id = update.effective_user.id
    phone = update.message.contact.phone_number

    data = load_data()
    u = get_user(data, user_id)
    u["phone"] = phone
    save_data(data)

    await update.message.reply_text(
        "✅ Rahmat! Telefon raqamingiz qabul qilindi.\n\n"
        "🎉 Endi konkursda ishtirokingiz tasdiqlandi!",
    )

# ====== FASTAPI APP (WEB FORM + WEBHOOK) ======
app = FastAPI()
tg_app: Application | None = None

FORM_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Ro‘yxatdan o‘tish</title>
  <style>
    body{font-family:Arial;background:#7fd1c7;margin:0;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px;}
    .card{background:#fff;max-width:420px;width:100%;border-radius:18px;padding:26px;box-shadow:0 12px 40px rgba(0,0,0,.18);}
    h2{margin:0 0 10px 0;}
    p{margin:0 0 18px 0;color:#333;}
    label{display:block;margin:14px 0 6px 0;font-weight:700;}
    input{width:100%;padding:12px 12px;border:1px solid #ddd;border-radius:12px;font-size:16px;}
    button{margin-top:18px;width:100%;padding:14px;border:0;border-radius:14px;background:#6fc6bb;font-size:16px;font-weight:800;cursor:pointer;}
    .small{font-size:12px;color:#666;margin-top:10px;}
  </style>
</head>
<body>
  <div class="card">
    <h2>🎉 Konkursga ro‘yxatdan o‘tish</h2>
    <p>Ma’lumotlaringizni to‘ldiring</p>
    <form method="POST" action="/register">
      <input type="hidden" name="uid" value="{uid}"/>
      <input type="hidden" name="sig" value="{sig}"/>
      <label>Ismingiz *</label>
      <input name="name" required placeholder="Ismingizni kiriting"/>
      <label>Familiyangiz *</label>
      <input name="surname" required placeholder="Familiyangizni kiriting"/>
      <button type="submit">Ro‘yxatdan o‘tish</button>
      <div class="small">Yuborgandan keyin Telegram botga qayting.</div>
    </form>
  </div>
</body>
</html>
"""

@app.get("/register", response_class=HTMLResponse)
async def register_get(uid: int, sig: str):
    if not verify_uid(uid, sig):
        return HTMLResponse("<h3>❌ Noto‘g‘ri link</h3>", status_code=403)
    return HTMLResponse(FORM_HTML.format(uid=uid, sig=sig))

@app.post("/register", response_class=HTMLResponse)
async def register_post(uid: int = Form(...), sig: str = Form(...), name: str = Form(...), surname: str = Form(...)):
    if not verify_uid(uid, sig):
        return HTMLResponse("<h3>❌ Noto‘g‘ri link</h3>", status_code=403)

    # Saqlab qo'yamiz
    data = load_data()
    u = get_user(data, uid)
    u["name"] = name.strip()
    u["surname"] = surname.strip()
    save_data(data)

    # Telegramga xabar + contact tugma
    contact_kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Raqamimni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await tg_app.bot.send_message(
        chat_id=uid,
        text="✅ Ma'lumotlar qabul qilindi!\n\nEndi telefon raqamingizni yuboring 👇",
        reply_markup=contact_kb
    )

    return HTMLResponse(
        "<h3>✅ Tayyor!</h3><p>Telegramga qayting — bot sizdan telefon raqamingizni so‘raydi.</p>"
    )

@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    global tg_app
    if not BOT_TOKEN or not CHANNEL_USERNAME or not BASE_URL:
        raise RuntimeError("BOT_TOKEN / CHANNEL_USERNAME / BASE_URL missing in Railway Variables")

    tg_app = Application.builder().token(BOT_TOKEN).build()

    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CallbackQueryHandler(check_join, pattern="^check$"))
    tg_app.add_handler(MessageHandler(filters.CONTACT, got_contact))

    await tg_app.initialize()
    await tg_app.start()

    # webhook o'rnatamiz
    await tg_app.bot.set_webhook(f"{BASE_URL}/telegram")

@app.on_event("shutdown")
async def on_shutdown():
    if tg_app:
        await tg_app.stop()
        await tg_app.shutdown()
