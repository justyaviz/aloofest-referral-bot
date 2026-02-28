import os, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
DATA_FILE = "data.json"

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
        data["users"][uid] = {"ref_by": None, "refs": 0, "joined": False}
    return data["users"][uid]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()
    u = get_user(data, user.id)

    if context.args:
        ref_id = context.args[0]
        if ref_id.isdigit() and int(ref_id) != user.id and u["ref_by"] is None:
            u["ref_by"] = int(ref_id)

    save_data(data)

    kb = [
        [InlineKeyboardButton("✅ A’zo bo‘ldim (tekshir)", callback_data="check")],
        [InlineKeyboardButton("📣 Taklif linkim", callback_data="mylink")],
        [InlineKeyboardButton("📊 Natijam", callback_data="stats")],
    ]

    text = (
        "🔥 Aloofest Super Konkurs!\n\n"
        f"1) Kanalga a’zo bo‘ling: {CHANNEL_USERNAME}\n"
        "2) So‘ng tekshir tugmasini bosing.\n\n"
        "👥 Har bir do‘st = 1 ball\n"
        "🏆 Eng ko‘p ball to‘plagan g‘olib bo‘ladi!"
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
    except:
        is_joined = False

    if is_joined and not u["joined"]:
        u["joined"] = True
        if u["ref_by"]:
            ref_user = get_user(data, u["ref_by"])
            ref_user["refs"] += 1
        save_data(data)
        msg = "✅ Tasdiqlandi! Endi taklif linkni ulashing 🚀"
    elif is_joined:
        msg = "✅ Siz allaqachon tasdiqlangansiz."
    else:
        msg = f"❌ Avval kanalga a’zo bo‘ling: {CHANNEL_USERNAME}"

    await q.edit_message_text(msg, reply_markup=q.message.reply_markup)

async def my_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user.id}"

    await q.edit_message_text(
        f"📣 Sizning taklif linkingiz:\n{link}\n\nDo‘st kirsa va a’zo bo‘lsa sizga +1 ball yoziladi.",
        reply_markup=q.message.reply_markup
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user
    data = load_data()
    u = get_user(data, user.id)
    joined = "Ha" if u["joined"] else "Yo‘q"

    await q.edit_message_text(
        f"📊 Natijangiz\n\nA’zo: {joined}\nTaklif: {u['refs']} ta",
        reply_markup=q.message.reply_markup
    )

def main():
    token = os.getenv("BOT_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="^check$"))
    app.add_handler(CallbackQueryHandler(my_link, pattern="^mylink$"))
    app.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
    app.run_polling()

if __name__ == "__main__":
    main()
