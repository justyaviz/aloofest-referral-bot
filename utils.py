from __future__ import annotations

import hashlib
import hmac
import html
from datetime import datetime

import aiohttp

from config import settings


def esc(text: str | None) -> str:
    return html.escape(text or '')


def sign_uid(uid: int) -> str:
    return hmac.new(settings.webapp_secret.encode(), str(uid).encode(), hashlib.sha256).hexdigest()


def verify_uid(uid: int, signature: str) -> bool:
    return hmac.compare_digest(sign_uid(uid), signature)


async def is_channel_member(user_id: int) -> bool:
    url = f'https://api.telegram.org/bot{settings.bot_token}/getChatMember'
    params = {
        'chat_id': f'@{settings.channel_username}',
        'user_id': user_id,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=15) as resp:
                data = await resp.json()
                if not data.get('ok'):
                    return False
                status = data['result']['status']
                return status in ('member', 'administrator', 'creator')
    except Exception:
        return False


def format_dt(ts: int | None) -> str:
    if not ts:
        return '—'
    return datetime.fromtimestamp(ts).strftime('%d.%m.%Y %H:%M')
