import asyncio
import os
import asyncpg

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart

# ======================
# CONFIG
# ======================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

db_pool: asyncpg.Pool | None = None


# ======================
# DATABASE
# ======================

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    async with db_pool.acquire() as conn:
        # families
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS families (
            id SERIAL PRIMARY KEY
        );
        """)

        # 🔥 МИГРАЦИЯ: добавляем owner_id, если его нет
        await conn.execute("""
        ALTER TABLE families
        ADD COLUMN IF NOT EXISTS owner_id BIGINT;
        """)

        # members
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
            user_id BIGINT PRIMARY KEY,
            family_id INTEGER REFERENCES families(id)
        );
        """)

        # tasks
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            family_id INTEGER REFERENCES families(id),
            text TEXT NOT NULL,
            done BOOLEAN DEFAULT FALSE
        );
        """)


# ======================
# HELPERS
# ======================

async def get_family_id(user_id: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT family_id FROM family_members WHERE user_id=$1",
            user_id
        )
        return row["family_id"] if row else None


async def ensure_family(user_id: int):
    family_id = await get_family_id(user_id)
    if family_id:
        return family_id

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO families (owner_id) VALUES ($1) RETURNING id",
            user_id
        )

        family_id = row["id"]

        await conn.execute(
            "INSERT INTO family_members (user_id, family_id) VALUES ($1, $2)",
            user_id, family_id
        )

    return family_id


# ======================
# HANDLERS
# ======================

@dp.message(CommandStart())
async def start(message: Message):
    await ensure_family(message.from_user.id)

    await message.answer(
        "👨‍👩‍👧 Семейный менеджер задач\n\n"
        "✍️ Просто напиши задачу текстом:\n"
        "Купить молоко\n\n"
        "📋 Чтобы посмотреть список — напиши:\n"
        "список"
    )


@dp.message(F.text.lower() == "список")
async def show_tasks(message: Message):
    family_id = await get_family_id(message.from_user.id)

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, text, done FROM tasks WHERE family_id=$1 ORDER BY id",
            family_id
        )

    if not rows:
        await message.answer("🎉 Все задачи выполнены!")
        return

    text = "📋 Список задач:\n\n"
    keyboard = []

    for row in rows:
        status = "✅" if row["done"] else "⬜"
        text += f"{status} {row['text']}\n"

        if not row["done"]:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"✔ {row['text']}",
                    callback_data=f"done:{row['id']}"
                )
            ])

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@dp.callback_query(F.data.startswith("done:"))
async def mark_done(callback):
    task_id = int(callback.data.split(":")[1])

    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE tasks SET done=TRUE WHERE id=$1",
            task_id
        )

    await callback.answer("Готово ✅")
    await callback.message.delete()
    await show_tasks(callback.message)


@dp.message(F.text)
async def add_task(message: Message):
    family_id = await ensure_family(message.from_user.id)

    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO tasks (family_id, text) VALUES ($1, $2)",
            family_id, message.text
        )

    await message.answer("➕ Задача добавлена")


# ======================
# MAIN
# ======================

async def main():
    # 🔥 сброс конфликтов Telegram
    await bot.delete_webhook(drop_pending_updates=True)

    await init_db()
    print("🤖 Bot started with PostgreSQL")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
