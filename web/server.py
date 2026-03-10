web/server.py
from aiohttp import web
from config import PORT


async def health(request: web.Request):
    return web.Response(text="OK")


async def setup_web_server():
    app = web.Application()
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    return runner
