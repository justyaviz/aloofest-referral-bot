import os
from dataclasses import dataclass


def _parse_admin_ids(raw: str) -> set[int]:
    result: set[int] = set()
    for item in raw.split(','):
        item = item.strip()
        if item.isdigit():
            result.add(int(item))
    return result


@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv('BOT_TOKEN', '').strip()
    base_url: str = os.getenv('BASE_URL', '').rstrip('/')
    webapp_secret: str = os.getenv('WEBAPP_SECRET', 'change-me-secret')
    channel_username: str = os.getenv('CHANNEL_USERNAME', 'aloo_uzb').replace('@', '').strip()
    shop_bot_username: str = os.getenv('SHOP_BOT_USERNAME', 'aloouz_bot').replace('@', '').strip()
    admin_ids: set[int] = _parse_admin_ids(os.getenv('ADMIN_IDS', ''))
    db_path: str = os.getenv('DB_PATH', 'bot.db')
    port: int = int(os.getenv('PORT', '8080'))
    registration_bonus: int = int(os.getenv('REGISTRATION_BONUS', '5'))
    referral_bonus: int = int(os.getenv('REFERRAL_BONUS', '5'))

    @property
    def channel_url(self) -> str:
        return f'https://t.me/{self.channel_username}'

    @property
    def shop_bot_url(self) -> str:
        return f'https://t.me/{self.shop_bot_username}'


settings = Settings()

if not settings.bot_token:
    raise RuntimeError('BOT_TOKEN topilmadi')
if not settings.base_url:
    raise RuntimeError('BASE_URL topilmadi')
