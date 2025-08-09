from aiohttp import web
import asyncio

async def handle(request):
    return web.Response(text="Bot is alive!")

def keep_alive():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    loop.run_until_complete(site.start())
