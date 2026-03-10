import os


def _parse_admin_ids(raw: str) -> set[int]:
    result: set[int] = set()
    for item in raw.split(","):
        item = item.strip()
        if item.isdigit():
            result.add(int(item))
    return result


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
WEBAPP_SECRET = os.getenv("WEBAPP_SECRET", "change-me-secret")

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "aloo_uzb").replace("@", "").strip()
SHOP_BOT_USERNAME = os.getenv("SHOP_BOT_USERNAME", "aloouz_bot").replace("@", "").strip()

ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

DB_PATH = os.getenv("DB_PATH", "bot.db")
PORT = int(os.getenv("PORT", "8080"))

REGISTRATION_BONUS = int(os.getenv("REGISTRATION_BONUS", "5"))
REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", "5"))

CHANNEL_URL = f"https://t.me/{CHANNEL_USERNAME}"
SHOP_BOT_URL = f"https://t.me/{SHOP_BOT_USERNAME}"


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")

if not BASE_URL:
    raise RuntimeError("BASE_URL topilmadi")

class Settings:
    bot_token = BOT_TOKEN
    base_url = BASE_URL
    webapp_secret = WEBAPP_SECRET
    channel_username = CHANNEL_USERNAME
    shop_bot_username = SHOP_BOT_USERNAME
    channel_url = CHANNEL_URL
    shop_bot_url = SHOP_BOT_URL
    admin_ids = ADMIN_IDS
    db_path = DB_PATH
    port = PORT
    registration_bonus = REGISTRATION_BONUS
    referral_bonus = REFERRAL_BONUS


settings = Settings()
