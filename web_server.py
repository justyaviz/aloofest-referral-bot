import html
import json
import aiohttp
from aiohttp import web
from config import PORT, BOT_TOKEN, BOT_URL
from database import db
from keyboards import sign_uid

DISTRICTS = {
    "Toshkent sh.": ["Bektemir", "Chilonzor", "Yakkasaroy", "Mirobod", "Mirzo Ulug‘bek", "Olmazor", "Sergeli", "Shayxontohur", "Uchtepa", "Yashnobod", "Yunusobod"],
    "Toshkent vil.": ["Angren", "Bekobod sh.", "Chirchiq", "Olmaliq", "Ohangaron sh.", "Yangiyo‘l sh.", "Nurafshon", "Bo‘ka", "Bo‘stonliq", "Chinoz", "Qibray", "Parkent", "Piskent", "Zangiota"],
    "Andijon": ["Andijon sh.", "Xonobod", "Asaka", "Baliqchi", "Bo‘ston", "Izboskan", "Marhamat", "Paxtaobod", "Shahrixon"],
    "Farg‘ona": ["Farg‘ona sh.", "Qo‘qon", "Marg‘ilon", "Quvasoy", "Oltiariq", "Bag‘dod", "Beshariq", "Dang‘ara", "Quva", "Rishton"],
    "Namangan": ["Namangan sh.", "Chust", "Kosonsoy", "Pop", "To‘raqo‘rg‘on", "Uychi", "Chortoq", "Yangiqo‘rg‘on"],
    "Samarqand": ["Samarqand sh.", "Kattaqo‘rg‘on sh.", "Bulung‘ur", "Ishtixon", "Jomboy", "Nurobod", "Paxtachi", "Payariq", "Toyloq", "Urgut"],
    "Buxoro": ["Buxoro sh.", "Kogon sh.", "G‘ijduvon", "Jondor", "Olot", "Qorako‘l", "Romitan", "Shofirkon", "Vobkent"],
    "Xorazm": ["Urganch sh.", "Xiva sh.", "Bog‘ot", "Gurlan", "Hazorasp", "Xonqa", "Qo‘shko‘pir", "Shovot", "Yangiariq"],
    "Qashqadaryo": ["Qarshi sh.", "Shahrisabz sh.", "Dehqonobod", "Kasbi", "Kitob", "Koson", "Muborak", "Nishon", "Qamashi", "Yakkabog‘"],
    "Surxondaryo": ["Termiz sh.", "Angor", "Boysun", "Denov", "Jarqo‘rg‘on", "Qumqo‘rg‘on", "Sherobod", "Sho‘rchi", "Uzun"],
    "Navoiy": ["Navoiy sh.", "Zarafshon", "Karmana", "Konimex", "Navbahor", "Nurota", "Qiziltepa", "Uchquduq", "Xatirchi"],
    "Jizzax": ["Jizzax sh.", "Arnasoy", "Baxmal", "Do‘stlik", "Forish", "G‘allaorol", "Paxtakor", "Yangiobod", "Zomin"],
    "Sirdaryo": ["Guliston sh.", "Shirin", "Yangiyer", "Boyovut", "Guliston tumani", "Mirzaobod", "Oqoltin", "Sardoba", "Xovos"],
    "Qoraqalpog‘iston": ["Nukus sh.", "Amudaryo", "Beruniy", "Chimboy", "Mo‘ynoq", "Qo‘ng‘irot", "Shumanay", "To‘rtko‘l", "Xo‘jayli"],
}
REGIONS = list(DISTRICTS.keys())


def verify_uid(uid: int, sig: str) -> bool:
    return sign_uid(uid) == sig


def build_html(user_id: int, sig: str) -> str:
    options = "".join(f'<option value="{html.escape(r)}">{html.escape(r)}</option>' for r in REGIONS)
    districts_json = json.dumps(DISTRICTS, ensure_ascii=False)
    back_url = BOT_URL or "#"

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>aloofest ro‘yxatdan o‘tish</title>
<style>
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  min-height: 100vh;
  font-family: Arial, sans-serif;
  background:
    radial-gradient(circle at top right, rgba(34,197,94,.25), transparent 25%),
    radial-gradient(circle at bottom left, rgba(59,130,246,.25), transparent 25%),
    linear-gradient(135deg, #0b1220 0%, #111827 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}}
.wrapper {{
  width: 100%;
  max-width: 540px;
}}
.card {{
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.12);
  backdrop-filter: blur(12px);
  border-radius: 24px;
  padding: 28px;
  box-shadow: 0 20px 60px rgba(0,0,0,.35);
}}
.badge {{
  display: inline-block;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(34,197,94,.15);
  border: 1px solid rgba(34,197,94,.35);
  color: #dcfce7;
  font-size: 13px;
  margin-bottom: 14px;
}}
h1 {{ margin: 0 0 8px; font-size: 28px; }}
p.subtitle {{
  margin: 0 0 20px;
  color: #cbd5e1;
  line-height: 1.6;
}}
label {{
  display: block;
  margin-top: 14px;
  margin-bottom: 8px;
  font-size: 14px;
  color: #e2e8f0;
  font-weight: 600;
}}
input, select {{
  width: 100%;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.08);
  color: white;
  font-size: 15px;
  outline: none;
}}
input::placeholder {{ color: #94a3b8; }}
option {{ color: black; }}
.buttons {{
  display: flex;
  gap: 12px;
  margin-top: 22px;
}}
button, a.back-btn {{
  flex: 1;
  text-align: center;
  padding: 15px;
  border: none;
  border-radius: 14px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
}}
button {{
  background: linear-gradient(90deg, #22c55e, #16a34a);
  color: white;
  box-shadow: 0 10px 25px rgba(34,197,94,.28);
}}
a.back-btn {{
  background: rgba(255,255,255,.08);
  color: white;
  border: 1px solid rgba(255,255,255,.12);
}}
#msg {{
  margin-top: 16px;
  padding: 14px;
  border-radius: 14px;
  display: none;
  font-size: 14px;
  line-height: 1.5;
}}
.success {{
  display: block !important;
  background: rgba(34,197,94,.15);
  border: 1px solid rgba(34,197,94,.35);
  color: #dcfce7;
}}
.error {{
  display: block !important;
  background: rgba(239,68,68,.15);
  border: 1px solid rgba(239,68,68,.35);
  color: #fee2e2;
}}
.footer-note {{
  margin-top: 14px;
  font-size: 12px;
  color: #94a3b8;
  text-align: center;
}}
</style>
</head>
<body>
<div class="wrapper">
  <div class="card">
    <div class="badge">🎉 aloofest registration</div>
    <h1>Ro‘yxatdan o‘tish</h1>
    <p class="subtitle">
      Quyidagi ma’lumotlarni to‘ldiring va konkurs ishtirokchisiga aylaning.
      Formani to‘ldirgach sizga <b>FEST ID</b> biriktiriladi va <b>+5 ball</b> beriladi.
    </p>

    <form id="regForm">
      <label>Ismingiz</label>
      <input id="name" placeholder="Masalan: Ali Valiyev" required>

      <label>Instagram username</label>
      <input id="instagram" placeholder="@username yoki username" required>

      <label>Viloyatingizni tanlang</label>
      <select id="region" required>
        <option value="">Tanlang</option>
        {options}
      </select>

      <label>Tuman / shaharni tanlang</label>
      <select id="district" required>
        <option value="">Avval viloyat tanlang</option>
      </select>

      <div class="buttons">
        <a class="back-btn" href="{back_url}">⬅️ ORQAGA QAYTISH</a>
        <button type="submit">RO‘YXATDAN O‘TISH</button>
      </div>
    </form>

    <div id="msg"></div>
    <div class="footer-note">aloo • aloofest mega konkurs</div>
  </div>
</div>

<script>
const districts = {districts_json};
const uid = {user_id};
const sig = "{sig}";
const regionEl = document.getElementById("region");
const districtEl = document.getElementById("district");
const msgBox = document.getElementById("msg");

regionEl.addEventListener("change", () => {{
  districtEl.innerHTML = '<option value="">Tanlang</option>';
  const arr = districts[regionEl.value] || [];
  arr.forEach(item => {{
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    districtEl.appendChild(opt);
  }});
}});

document.getElementById("regForm").addEventListener("submit", async (e) => {{
  e.preventDefault();
  msgBox.className = "";
  msgBox.style.display = "none";

  const payload = {{
    uid: uid,
    sig: sig,
    full_name: document.getElementById("name").value.trim(),
    instagram: document.getElementById("instagram").value.trim(),
    region: regionEl.value,
    district: districtEl.value
  }};

  try {{
    const res = await fetch("/api/register", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify(payload)
    }});
    const data = await res.json();

    if (data.ok) {{
      msgBox.classList.add("success");
      msgBox.innerText = data.message || "Muvaffaqiyatli ro‘yxatdan o‘tildi";
      setTimeout(() => {{
        if ("{back_url}") {{
          window.location.href = "{back_url}";
        }}
      }}, 1800);
    }} else {{
      msgBox.classList.add("error");
      msgBox.innerText = data.error || "Xatolik yuz berdi";
    }}
    msgBox.style.display = "block";
  }} catch (e) {{
    msgBox.classList.add("error");
    msgBox.innerText = "Server bilan bog‘lanishda xatolik yuz berdi";
    msgBox.style.display = "block";
  }}
}});
</script>
</body>
</html>"""


async def send_bot_message(chat_id: int, text: str):
    async with aiohttp.ClientSession() as session:
        await session.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        )


async def register_page(request: web.Request):
    try:
        uid = int(request.query.get("uid", "0"))
    except ValueError:
        return web.Response(text="Noto‘g‘ri uid", status=400)

    sig = request.query.get("sig", "")
    if not verify_uid(uid, sig):
        return web.Response(text="Ruxsat yo‘q", status=403)

    user = await db.get_user(uid)
    if not user:
        return web.Response(text="Foydalanuvchi topilmadi. Avval botda /start bosing.", status=404)

    return web.Response(text=build_html(uid, sig), content_type="text/html")


async def register_api(request: web.Request):
    data = await request.json()

    uid = int(data.get("uid", 0))
    sig = data.get("sig", "")
    full_name = str(data.get("full_name", "")).strip()
    instagram = str(data.get("instagram", "")).strip().replace("@", "")
    region = str(data.get("region", "")).strip()
    district = str(data.get("district", "")).strip()

    if not verify_uid(uid, sig):
        return web.json_response({"ok": False, "error": "Ruxsat yo‘q"})

    if not full_name:
        return web.json_response({"ok": False, "error": "Ism kiritilishi shart"})
    if not instagram:
        return web.json_response({"ok": False, "error": "Instagram username kiritilishi shart"})
    if region not in DISTRICTS:
        return web.json_response({"ok": False, "error": "Viloyat noto‘g‘ri"})
    if district not in DISTRICTS[region]:
        return web.json_response({"ok": False, "error": "Tuman/shahar noto‘g‘ri"})

    user = await db.get_user(uid)
    if not user:
        return web.json_response({"ok": False, "error": "Foydalanuvchi topilmadi. Avval botda /start bosing."})

    ok, result = await db.register_user(
        user_id=uid,
        full_name=full_name,
        instagram=instagram,
        region=region,
        district=district
    )

    if not ok:
        return web.json_response({"ok": False, "error": result})

    await send_bot_message(
        uid,
        f"🎉 <b>Tabriklaymiz, {html.escape(full_name)}!</b>\n\n"
        f"Siz konkurs ishtirokchisiga aylandingiz va <b>+5 ball</b> qo‘lga kiritdingiz.\n"
        f"🆔 Sizning FEST ID raqamingiz: <b>{result}</b>\n\n"
        f"Endi do‘stlaringizni taklif qiling va g‘olib bo‘lish imkoniyatingizni maksimal oshiring.\n\n"
        f"Savollar tug‘ilsa, <b>YORDAM</b> menyusi orqali adminga savolingizni yuboring yoki <b>@aloouz_chat</b> ga bog‘laning."
    )

    return web.json_response({
        "ok": True,
        "message": f"🎉 Tabriklaymiz! Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz. FEST ID: {result}. Botga qaytib davom etishingiz mumkin."
    })


async def health(request: web.Request):
    return web.Response(text="OK")


async def setup_web_server():
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/register", register_page)
    app.router.add_post("/api/register", register_api)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    return runner
