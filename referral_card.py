from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1200
HEIGHT = 630
BG = (10, 20, 45)
ACCENT = (32, 209, 180)
WHITE = (255, 255, 255)
MUTED = (210, 220, 245)


def _font(size: int):
    try:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)
    except Exception:
        return ImageFont.load_default()


def generate_referral_card(full_name: str, diamonds: int, invite_url: str, save_path: str) -> str:
    img = Image.new('RGB', (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((40, 40, WIDTH - 40, HEIGHT - 40), radius=32, outline=ACCENT, width=4)

    title_font = _font(52)
    big_font = _font(84)
    text_font = _font(34)
    small_font = _font(26)

    draw.text((80, 85), 'aloo referral card', fill=WHITE, font=title_font)
    draw.text((80, 190), full_name[:28], fill=WHITE, font=big_font)
    draw.text((80, 320), f'💎 Ball: {diamonds}', fill=ACCENT, font=text_font)
    draw.text((80, 385), 'Do‘stlaringizni taklif qiling va reytingda yuqoriga chiqing.', fill=MUTED, font=text_font)

    box_y = 470
    draw.rounded_rectangle((80, box_y, WIDTH - 80, box_y + 90), radius=20, fill=(20, 34, 70))
    draw.text((105, box_y + 28), invite_url[:75], fill=WHITE, font=small_font)

    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(save_path, format='PNG')
    return save_path
