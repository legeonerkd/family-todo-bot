import asyncio
from aiohttp import web
from db import dp, bot, init_db, close_db
from config import WEBHOOK_SECRET, RAILWAY_STATIC_URL
from handlers import start, tasks, family, history, shopping
from scheduler import schedule_daily_digest

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{RAILWAY_STATIC_URL}{WEBHOOK_PATH}"

dp.include_router(start.router)
dp.include_router(tasks.router)
dp.include_router(shopping.router)
dp.include_router(family.router)
dp.include_router(history.router)

async def on_startup():
    await init_db()
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    print("Database initialized")
    print("Webhook set")
    
    # Запускаем планировщик дайджестов
    asyncio.create_task(schedule_daily_digest())
    print("Daily digest scheduler started")

async def on_shutdown():
    await bot.delete_webhook()
    await close_db()
    print("Database closed")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET,
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    await web._run_app(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    asyncio.run(main())
