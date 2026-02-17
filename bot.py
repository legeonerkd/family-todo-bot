import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.config import BOT_TOKEN
from app.db import init_db
from app.handlers import start, tasks, shopping, family, history

WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")
WEBHOOK_URL = f"https://{os.environ.get('RAILWAY_STATIC_URL')}{WEBHOOK_PATH}"

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


async def on_startup():
    await init_db()
    await bot.set_webhook(
        WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET
    )
    print("✅ Webhook set:", WEBHOOK_URL)


async def on_shutdown():
    await bot.delete_webhook()
    print("🛑 Webhook deleted")


async def main():
    # подключаем роутеры
    dp.include_router(start.router)
    dp.include_router(tasks.router)
    dp.include_router(shopping.router)
    dp.include_router(family.router)
    dp.include_router(history.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    port = int(os.environ.get("PORT", 8080))
    await web._run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    asyncio.run(main())

