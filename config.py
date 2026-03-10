import os


def parse_admin_ids(raw: str) -> set[int]:
    result = set()
    for item in raw.split(","):
        item = item.strip()
        if item.isdigit():
            result.add(int(item))
    return result


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_USERNAME = os.getenv("BOT_USERNAME", "").replace("@", "").strip()
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
WEBAPP_SECRET = os.getenv("WEBAPP_SECRET", "change-me-secret")

CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "aloo_uzb").replace("@", "").strip()
SHOP_BOT_USERNAME = os.getenv("SHOP_BOT_USERNAME", "aloouz_bot").replace("@", "").strip()

CHANNEL_URL = f"https://t.me/{CHANNEL_USERNAME}"
SHOP_BOT_URL = f"https://t.me/{SHOP_BOT_USERNAME}"
BOT_URL = f"https://t.me/{BOT_USERNAME}" if BOT_USERNAME else ""

INSTAGRAM_MAIN_URL = os.getenv("INSTAGRAM_MAIN_URL", "https://instagram.com/aloo.uz_").strip()
INSTAGRAM_RULE_TEXT = os.getenv(
    "INSTAGRAM_RULE_TEXT",
    "@aloo.uz_ profiliga va u obuna bo'lgan 15 ta profilga ham obuna bo'lish majburiy",
)

ADMIN_IDS = parse_admin_ids(os.getenv("ADMIN_IDS", ""))

DB_PATH = os.getenv("DB_PATH", "bot.db")
PORT = int(os.getenv("PORT", "8080"))

REGISTRATION_BONUS = int(os.getenv("REGISTRATION_BONUS", "5"))
REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", "5"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi")
if not BASE_URL:
    raise RuntimeError("BASE_URL topilmadi")
