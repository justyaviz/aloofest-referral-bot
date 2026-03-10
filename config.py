import os


def parse_admin_ids(raw: str) -> set[int]:
    result = set()
    for x in raw.split(","):
        x = x.strip()
        if x.isdigit():
            result.add(int(x))
    return result


BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL")

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
SHOP_BOT_USERNAME = os.getenv("SHOP_BOT_USERNAME")

CHANNEL_URL = f"https://t.me/{CHANNEL_USERNAME}"
SHOP_BOT_URL = f"https://t.me/{SHOP_BOT_USERNAME}"

ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", ""))

DB_PATH = os.getenv("DB_PATH", "bot.db")

PORT = int(os.getenv("PORT", 8080))

REGISTRATION_BONUS = int(os.getenv("REGISTRATION_BONUS", 5))
REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", 5))

WEBAPP_SECRET = os.getenv("WEBAPP_SECRET", "secret")
