import asyncio
import secrets

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from db import init_db, get_pool


bot = Bot(
    BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()


# ======================
# HELPERS
# ======================
async def get_or_create_user(user_id, name):
    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT family_id FROM users WHERE telegram_id=$1",
            user_id
        )
        if user:
            return user["family_id"]

        family_id = await conn.fetchval(
            "INSERT INTO families DEFAULT VALUES RETURNING id"
        )

        await conn.execute(
            "INSERT INTO users (telegram_id, name, family_id) VALUES ($1,$2,$3)",
            user_id, name, family_id
        )
        return family_id


async def notify_family(family_id, text, exclude=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        users = await conn.fetch(
            "SELECT telegram_id FROM users WHERE family_id=$1",
            family_id
        )

    for u in users:
        if exclude and u["telegram_id"] == exclude:
            continue
        try:
            await bot.send_message(u["telegram_id"], text)
        except:
            pass


# ======================
# MENU
# ======================
def menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("➕ Добавить задачу")],
            [KeyboardButton("🛒 Покупки")],
            [KeyboardButton("👨‍👩‍👧‍👦 Пригласить")]
        ],
        resize_keyboard=True
    )


# ======================
# START
# ======================
@dp.message(CommandStart())
async def start(message: Message):
    family_id = await get_or_create_user(
        message.from_user.id,
        message.from_user.first_name
    )

    await message.answer(
        "👋 <b>Бот онлайн 24/7</b>\nВыбирай действие 👇",
        reply_markup=menu()
    )


# ======================
# ADD TASK
# ======================
@dp.message(lambda m: m.text == "➕ Добавить задачу")
async def ask_task(message: Message):
    await message.answer("✍️ Напиши задачу")


@dp.message(lambda m: m.text and not m.text.startswith(("➕","🛒","👨")))
async def add_task(message: Message):
    pool = await get_pool()
    family_id = await get_or_create_user(
        message.from_user.id,
        message.from_user.first_name
    )

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO tasks (family_id, text) VALUES ($1,$2)",
            family_id, message.text
        )

    await notify_family(
        family_id,
        f"➕ <b>{message.from_user.first_name}</b> добавил задачу:\n{message.text}",
        exclude=message.from_user.id
    )


# ======================
# RUN
# ======================
async def main():
    await init_db()
    print("🤖 Bot started with PostgreSQL")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
