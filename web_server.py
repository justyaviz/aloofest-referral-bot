import html
import json
from aiohttp import web
from config import PORT
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

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>aloofest ro‘yxatdan o‘tish</title>
<style>
body {{
  margin: 0;
  padding: 20px;
  font-family: Arial, sans-serif;
  background: #0f172a;
  color: white;
}}
.card {{
  max-width: 460px;
  margin: 0 auto;
  background: #1e293b;
  border-radius: 16px;
  padding: 20px;
}}
label {{
  display: block;
  margin-top: 14px;
  margin-bottom: 6px;
}}
input, select {{
  width: 100%;
  padding: 12px;
  border-radius: 10px;
  border: none;
}}
button {{
  width: 100%;
  margin-top: 18px;
  padding: 14px;
  border: none;
  border-radius: 10px;
  background: #22c55e;
  color: white;
  font-weight: bold;
}}
</style>
</head>
<body>
<div class="card">
  <h2>aloofest ro‘yxatdan o‘tish</h2>
  <p>Formani to‘ldiring va konkurs ishtirokchisiga aylaning.</p>

  <form id="regForm">
    <label>Ismingiz</label>
    <input id="name" required>

    <label>Instagram username</label>
    <input id="instagram" required>

    <label>Viloyatingizni tanlang</label>
    <select id="region" required>
      <option value="">Tanlang</option>
      {options}
    </select>

    <label>Tuman / shaharni tanlang</label>
    <select id="district" required>
      <option value="">Avval viloyat tanlang</option>
    </select>

    <button type="submit">RO‘YXATDAN O‘TISH</button>
  </form>

  <div id="msg" style="margin-top:15px;"></div>
</div>

<script>
const districts = {districts_json};
const uid = {user_id};
const sig = "{sig}";

const regionEl = document.getElementById("region");
const districtEl = document.getElementById("district");

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

  const payload = {{
    uid: uid,
    sig: sig,
    full_name: document.getElementById("name").value.trim(),
    instagram: document.getElementById("instagram").value.trim(),
    region: regionEl.value,
    district: districtEl.value
  }};

  const res = await fetch("/api/register", {{
    method: "POST",
    headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify(payload)
  }});

  const data = await res.json();
  document.getElementById("msg").innerText = data.message || data.error || "Xatolik";
}});
</script>
</body>
</html>"""


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
    instagram = str(data.get("instagram", "")).strip()
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

    return web.json_response({
        "ok": True,
        "message": f"Tabriklaymiz! Siz muvaffaqiyatli ro‘yxatdan o‘tdingiz. FEST ID: {result}"
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
