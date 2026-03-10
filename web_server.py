from __future__ import annotations

import html
import json

from aiohttp import web

from config import PORT
from database import db
from keyboards import sign_uid

DISTRICTS = {
    "Toshkent sh.": [
        "Bektemir", "Chilonzor", "Yakkasaroy", "Mirobod", "Mirzo Ulug‘bek",
        "Olmazor", "Sergeli", "Shayxontohur", "Uchtepa", "Yashnobod", "Yunusobod"
    ],
    "Toshkent vil.": [
        "Angren", "Bekobod sh.", "Chirchiq", "Olmaliq", "Ohangaron sh.",
        "Yangiyo‘l sh.", "Nurafshon", "Bekobod tumani", "Bo‘ka", "Bo‘stonliq",
        "Chinoz", "Qibray", "Ohangaron tumani", "Oqqo‘rg‘on", "Parkent",
        "Piskent", "Quyi Chirchiq", "Yangiyo‘l tumani", "Yuqori Chirchiq", "Zangiota"
    ],
    "Andijon": [
        "Andijon sh.", "Xonobod", "Andijon tumani", "Asaka", "Baliqchi",
        "Bo‘ston", "Buloqboshi", "Izboskan", "Jalaquduq", "Marhamat",
        "Oltinko‘l", "Paxtaobod", "Qo‘rg‘ontepa", "Shahrixon", "Ulug‘nor", "Xo‘jaobod"
    ],
    "Farg‘ona": [
        "Farg‘ona sh.", "Qo‘qon", "Marg‘ilon", "Quvasoy", "Farg‘ona tumani",
        "Oltiariq", "Bag‘dod", "Beshariq", "Buvayda", "Dang‘ara",
        "Furqat", "Qo‘shtepa", "Quva", "Rishton", "So‘x",
        "Toshloq", "Uchko‘prik", "Yozyovon"
    ],
    "Namangan": [
        "Namangan sh.", "Chust", "Kosonsoy", "Pop", "To‘raqo‘rg‘on",
        "Uychi", "Uchqo‘rg‘on", "Chortoq", "Mingbuloq", "Namangan tumani",
        "Norin", "Yangiqo‘rg‘on"
    ],
    "Samarqand": [
        "Samarqand sh.", "Kattaqo‘rg‘on sh.", "Bulung‘ur", "Ishtixon",
        "Jomboy", "Kattaqo‘rg‘on tumani", "Qo‘shrabot", "Narpay",
        "Nurobod", "Oqdaryo", "Paxtachi", "Pastdarg‘om",
        "Payariq", "Samarqand tumani", "Toyloq", "Urgut"
    ],
    "Buxoro": [
        "Buxoro sh.", "Kogon sh.", "Buxoro tumani", "G‘ijduvon",
        "Jondor", "Kogon tumani", "Olot", "Peshku",
        "Qorako‘l", "Qorovulbozor", "Romitan", "Shofirkon", "Vobkent"
    ],
    "Xorazm": [
        "Urganch sh.", "Xiva sh.", "Bog‘ot", "Gurlan", "Xiva tumani",
        "Hazorasp", "Xonqa", "Qo‘shko‘pir", "Shovot",
        "Urganch tumani", "Yangiariq", "Yangibozor", "Tuproqqal’a"
    ],
    "Qashqadaryo": [
        "Qarshi sh.", "Shahrisabz sh.", "Dehqonobod", "Kasbi", "Kitob",
        "Koson", "Ko‘kdala", "Mirishkor", "Muborak", "Nishon",
        "Qamashi", "Qarshi tumani", "Yakkabog‘", "Chiroqchi", "Shahrisabz tumani", "G‘uzor"
    ],
    "Surxondaryo": [
        "Termiz sh.", "Angor", "Bandixon", "Boysun", "Denov",
        "Jarqo‘rg‘on", "Muzrabot", "Oltinsoy", "Qiziriq", "Qumqo‘rg‘on",
        "Sariosiyo", "Sherobod", "Sho‘rchi", "Termiz tumani", "Uzun"
    ],
    "Navoiy": [
        "Navoiy sh.", "Zarafshon", "G‘ozg‘on", "Karmana", "Konimex",
        "Navbahor", "Nurota", "Qiziltepa", "Tomdi", "Uchquduq", "Xatirchi"
    ],
    "Jizzax": [
        "Jizzax sh.", "Arnasoy", "Baxmal", "Do‘stlik", "Forish",
        "G‘allaorol", "Mirzacho‘l", "Paxtakor", "Yangiobod",
        "Zafarobod", "Zarbdor", "Zomin", "Sharof Rashidov"
    ],
    "Sirdaryo": [
        "Guliston sh.", "Shirin", "Yangiyer", "Boyovut", "Guliston tumani",
        "Mirzaobod", "Oqoltin", "Sardoba", "Sayxunobod", "Sirdaryo", "Xovos"
    ],
    "Qoraqalpog‘iston": [
        "Nukus sh.", "Amudaryo", "Beruniy", "Bo‘zatov", "Chimboy",
        "Ellikqal’a", "Kegeyli", "Mo‘ynoq", "Nukus tumani", "Qanliko‘l",
        "Qo‘ng‘irot", "Qorao‘zak", "Shumanay", "Taxtako‘pir", "To‘rtko‘l", "Xo‘jayli"
    ],
}
REGIONS = list(DISTRICTS.keys())


def verify_uid(uid: int, sig: str) -> bool:
    return sign_uid(uid) == sig


def registration_html(user_id: int, first_name: str, last_name: str, region: str, district: str, sig: str) -> str:
    region_options = "".join(
        f'<option value="{html.escape(r)}" {"selected" if r == region else ""}>{html.escape(r)}</option>'
        for r in REGIONS
    )
    districts_json = json.dumps(DISTRICTS, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>aloo ro‘yxatdan o‘tish</title>
<style>
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  padding: 0;
  font-family: Arial, sans-serif;
  background: linear-gradient(135deg, #0b1220, #10192d);
  color: white;
}}
.wrap {{
  max-width: 480px;
  margin: 0 auto;
  padding: 20px;
}}
.card {{
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 20px;
  padding: 20px;
  margin-top: 20px;
}}
h1 {{ margin: 0 0 10px; }}
p {{ color: #d6e2ff; }}
label {{ display:block; margin-top:14px; margin-bottom:6px; }}
input, select {{
  width:100%;
  padding:14px;
  border-radius:12px;
  border:1px solid rgba(255,255,255,0.15);
  background:rgba(255,255,255,0.08);
  color:white;
}}
option {{ color:black; }}
button {{
  width:100%;
  margin-top:18px;
  padding:14px;
  border:0;
  border-radius:12px;
  background:#16a34a;
  color:white;
  font-weight:bold;
  cursor:pointer;
}}
.ok, .err {{
  display:none;
  margin-top:14px;
  padding:12px;
  border-radius:12px;
}}
.ok {{
  background: rgba(34,197,94,.15);
  border:1px solid rgba(34,197,94,.3);
}}
.err {{
  background: rgba(239,68,68,.15);
  border:1px solid rgba(239,68,68,.3);
}}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>🎉 aloo konkurs ro‘yxati</h1>
    <p>Formani to‘ldiring va <b>aloofest</b> konkursida qatnashishni boshlang.</p>
    <form id="regForm">
      <label>Ism</label>
      <input id="first_name" value="{html.escape(first_name)}" required>

      <label>Familiya</label>
      <input id="last_name" value="{html.escape(last_name)}" required>

      <label>Viloyatingizni tanlang</label>
      <select id="region" required>
        <option value="">Tanlang</option>
        {region_options}
      </select>

      <label>Shahar yoki tumaningizni tanlang</label>
      <select id="district" required>
        <option value="">Avval viloyat tanlang</option>
      </select>

      <button type="submit">RO‘YXATDAN O‘TISH</button>

      <div class="ok" id="okBox"></div>
      <div class="err" id="errBox"></div>
    </form>
  </div>
</div>

<script>
const districts = {districts_json};
const selectedRegion = {json.dumps(region, ensure_ascii=False)};
const selectedDistrict = {json.dumps(district, ensure_ascii=False)};
const uid = {user_id};
const sig = {json.dumps(sig)};

const regionEl = document.getElementById("region");
const districtEl = document.getElementById("district");
const okBox = document.getElementById("okBox");
const errBox = document.getElementById("errBox");

function loadDistricts(region, selected="") {{
  districtEl.innerHTML = "";
  if (!region || !districts[region]) {{
    districtEl.innerHTML = '<option value="">Avval viloyat tanlang</option>';
    return;
  }}
  const first = document.createElement("option");
  first.value = "";
  first.textContent = "Tanlang";
  districtEl.appendChild(first);

  districts[region].forEach(item => {{
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    if (item === selected) opt.selected = true;
    districtEl.appendChild(opt);
  }});
}}

regionEl.addEventListener("change", () => {{
  loadDistricts(regionEl.value, "");
}});

if (selectedRegion) {{
  regionEl.value = selectedRegion;
  loadDistricts(selectedRegion, selectedDistrict);
}}

document.getElementById("regForm").addEventListener("submit", async (e) => {{
  e.preventDefault();

  okBox.style.display = "none";
  errBox.style.display = "none";

  const payload = {{
    uid,
    sig,
    first_name: document.getElementById("first_name").value.trim(),
    last_name: document.getElementById("last_name").value.trim(),
    region: regionEl.value,
    district: districtEl.value,
  }};

  try {{
    const res = await fetch("/api/register", {{
      method: "POST",
      headers: {{"Content-Type":"application/json"}},
      body: JSON.stringify(payload)
    }});
    const data = await res.json();

    if (data.ok) {{
      okBox.style.display = "block";
      okBox.textContent = "✅ Tabriklaymiz! Ma’lumotlaringiz saqlandi. Endi botga qaytib davom etishingiz mumkin.";
    }} else {{
      errBox.style.display = "block";
      errBox.textContent = data.error || "Xatolik yuz berdi";
    }}
  }} catch (e) {{
    errBox.style.display = "block";
    errBox.textContent = "Server bilan bog‘lanishda xatolik yuz berdi.";
  }}
}});
</script>
</body>
</html>"""


async def health(request: web.Request):
    return web.Response(text="OK")


async def register_page(request: web.Request):
    try:
        uid = int(request.query.get("uid", "0"))
    except ValueError:
        return web.Response(text="Noto‘g‘ri uid", status=400)

    sig = request.query.get("sig", "")
    if not uid or not verify_uid(uid, sig):
        return web.Response(text="Ruxsat yo‘q", status=403)

    user = await db.get_user(uid)
    if not user:
        return web.Response(
            text="Foydalanuvchi topilmadi. Avval botda /start bosing.",
            status=404
        )

    html_text = registration_html(
        uid,
        user["first_name"] or "",
        user["last_name"] or "",
        user["region"] or "",
        user["district"] or "",
        sig
    )
    return web.Response(text=html_text, content_type="text/html")


async def register_api(request: web.Request):
    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "Noto‘g‘ri so‘rov"})

    uid = int(payload.get("uid", 0))
    sig = payload.get("sig", "")
    first_name = str(payload.get("first_name", "")).strip()
    last_name = str(payload.get("last_name", "")).strip()
    region = str(payload.get("region", "")).strip()
    district = str(payload.get("district", "")).strip()

    if not uid or not verify_uid(uid, sig):
        return web.json_response({"ok": False, "error": "Ruxsat yo‘q"})

    if not first_name:
        return web.json_response({"ok": False, "error": "Ism kiritilishi shart"})
    if not last_name:
        return web.json_response({"ok": False, "error": "Familiya kiritilishi shart"})
    if region not in DISTRICTS:
        return web.json_response({"ok": False, "error": "Viloyat noto‘g‘ri"})
    if district not in DISTRICTS[region]:
        return web.json_response({"ok": False, "error": "Tuman/Shahar noto‘g‘ri"})

    user = await db.get_user(uid)
    if not user:
        return web.json_response({"ok": False, "error": "Foydalanuvchi topilmadi. Avval botda /start bosing."})

    ok, msg = await db.register_user(
        user_id=uid,
        username=user["username"],
        first_name=first_name,
        last_name=last_name,
        region=region,
        district=district,
        is_subscribed=True
    )
    if not ok:
        return web.json_response({"ok": False, "error": msg})

    return web.json_response({"ok": True})


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
