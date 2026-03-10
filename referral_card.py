from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont


def generate_referral_card(full_name: str, diamonds: int, referral_count: int, invite_link: str, out_path: str = "referral_card.png") -> str:
    width, height = 1000, 550
    img = Image.new("RGB", (width, height), (11, 18, 32))
    draw = ImageDraw.Draw(img)

    # oddiy default font
    title_font = ImageFont.load_default()
    text_font = ImageFont.load_default()

    draw.rounded_rectangle((35, 35, 965, 515), radius=28, fill=(21, 31, 55), outline=(60, 90, 150), width=2)

    draw.text((60, 60), "ALOOfest Referral Card", fill=(255, 255, 255), font=title_font)
    draw.text((60, 140), f"Ism: {full_name}", fill=(240, 245, 255), font=text_font)
    draw.text((60, 200), f"Ball: {diamonds} 💎", fill=(0, 255, 200), font=text_font)
    draw.text((60, 260), f"Takliflar: {referral_count}", fill=(255, 255, 255), font=text_font)

    draw.text((60, 340), "Taklif havolasi:", fill=(200, 220, 255), font=text_font)
    draw.text((60, 380), invite_link, fill=(255, 255, 255), font=text_font)

    draw.text((60, 460), "Ko‘proq do‘st taklif qiling va sovg‘alar yuting 🚀", fill=(190, 210, 255), font=text_font)

    img.save(out_path)
    return out_path
