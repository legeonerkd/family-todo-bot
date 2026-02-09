import asyncio
import os
import asyncpg

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ======================
# CONFIG
# ======================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN or not DATABASE_URL:
    raise RuntimeError("ENV variables not set")

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

db_pool: asyncpg.Pool | None = None

# ======================
# FSM
# ======================

class UserState(StatesGroup):
    confirm_type = State()

# ======================
# DATABASE
# ======================

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    async with db_pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS families (
            id SERIAL PRIMARY KEY,
            owner_id BIGINT
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
            user_id BIGINT PRIMARY KEY,
            family_id INTEGER REFERENCES families(id)
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            family_id INTEGER,
            text TEXT,
            done BOOLEAN DEFAULT FALSE
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS shopping (
            id SERIAL PRIMARY KEY,
            family_id INTEGER,
            text TEXT,
            is_bought BOOLEAN DEFAULT FALSE
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id BIGINT PRIMARY KEY,
            notifications TEXT DEFAULT 'all'
        );
        """)

# ======================
# UI
# ======================

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить")],
            [
                KeyboardButton(text="📋 Задачи"),
                KeyboardButton(text="🛒 Покупки"),
            ],
            [
                KeyboardButton(text="⚙️ Уведомления"),
                KeyboardButton(text="👨‍👩‍👧‍👦 Пригласить"),
            ],
        ],
        resize_keyboard=True,
    )

def confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="📋 Задача", callback_data="confirm:task"),
            InlineKeyboardButton(text="🛒 Покупка", callback_data="confirm:shopping"),
        ]]
    )

def shopping_actions():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отметить купленным", callback_data="shop:done")],
            [InlineKeyboardButton(text="🧹 Очистить купленные", callback_data="shop:clear")],
        ]
    )

def notification_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Все", callback_data="notif:all")],
            [InlineKeyboardButton(text="👤 Только важные", callback_data="notif:important")],
            [InlineKeyboardButton(text="🔕 Выключить", callback_data="notif:off")],
        ]
    )

# ======================
# HELPERS
# ======================

async def get_family_id(user_id: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT family_id FROM family_members WHERE user_id=$1",
            user_id,
        )
        return row["family_id"] if row else None

async def ensure_family(user_id: int):
    family_id = await get_family_id(user_id)
    if family_id:
        return family_id

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO families (owner_id) VALUES ($1) RETURNING id",
            user_id,
        )
        family_id = row["id"]
        await conn.execute(
            "INSERT INTO family_members (user_id, family_id) VALUES ($1,$2)",
            user_id,
            family_id,
        )
    return family_id

async def add_user_to_family(user_id: int, family_id: int):
    async with db_pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO family_members (user_id, family_id)
        VALUES ($1,$2)
        ON CONFLICT (user_id) DO UPDATE SET family_id=$2
        """, user_id, family_id)

async def get_notif_mode(user_id: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT notifications FROM user_settings WHERE user_id=$1",
            user_id,
        )
        return row["notifications"] if row else "all"

async def notify_family(family_id: int, text: str, author_id: int, level="all"):
    async with db_pool.acquire() as conn:
        users = await conn.fetch(
            "SELECT user_id FROM family_members WHERE family_id=$1 AND user_id!=$2",
            family_id,
            author_id,
        )

    for u in users:
        mode = await get_notif_mode(u["user_id"])
        if mode == "off":
            continue
        if mode == "important" and level != "important":
            continue
        try:
            await bot.send_message(u["user_id"], text)
        except Exception:
            pass

# ======================
# START
# ======================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    args = message.text.split()
    if len(args) == 2 and args[1].isdigit():
        await add_user_to_family(message.from_user.id, int(args[1]))
        await message.answer("🎉 Ты присоединился к семье!")

    await ensure_family(message.from_user.id)
    await message.answer(
        "👨‍👩‍👧 Семейный менеджер задач",
        reply_markup=main_menu(),
    )

# ======================
# INVITE
# ======================

@dp.message(F.text == "👨‍👩‍👧‍👦 Пригласить")
async def invite(message: Message):
    family_id = await ensure_family(message.from_user.id)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={family_id}"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Присоединиться", url=link)]
        ]
    )

    await message.answer("Отправь ссылку члену семьи 👇", reply_markup=kb)

# ======================
# ADD FLOW
# ======================

@dp.message(F.text == "➕ Добавить")
async def add_any(message: Message, state: FSMContext):
    await state.set_state(UserState.confirm_type)
    await message.answer("✍️ Напиши, что нужно добавить")

@dp.message(UserState.confirm_type)
async def choose_type(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer(
        f"Добавить:\n\n«{message.text}»",
        reply_markup=confirm_keyboard(),
    )

@dp.callback_query(F.data.startswith("confirm:"))
async def confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data["text"]
    family_id = await ensure_family(callback.from_user.id)

    if callback.data == "confirm:task":
        async with db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO tasks (family_id, text) VALUES ($1,$2)",
                family_id,
                text,
            )
        await notify_family(
            family_id,
            f"🆕 Новая задача:\n{text}",
            callback.from_user.id,
            "important",
        )
        await callback.message.edit_text("📋 Задача добавлена")

    else:
        async with db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO shopping (family_id, text) VALUES ($1,$2)",
                family_id,
                text,
            )
        await notify_family(
            family_id,
            f"🛒 Добавлено в покупки:\n{text}",
            callback.from_user.id,
        )
        await callback.message.edit_text("🛒 Покупка добавлена")

    await state.clear()
    await callback.message.answer("Готово 👍", reply_markup=main_menu())

# ======================
# TASKS
# ======================

@dp.message(F.text == "📋 Задачи")
async def tasks(message: Message):
    family_id = await get_family_id(message.from_user.id)

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, text, done FROM tasks WHERE family_id=$1",
            family_id,
        )

    if not rows:
        await message.answer("Задач нет 🎉", reply_markup=main_menu())
        return

    text = "📋 Задачи:\n\n"
    kb = []

    for r in rows:
        text += f"{'✅' if r['done'] else '⬜'} {r['text']}\n"
        if not r["done"]:
            kb.append([
                InlineKeyboardButton(
                    text=f"✔ {r['text']}",
                    callback_data=f"taskdone:{r['id']}",
                )
            ])

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
    )

@dp.callback_query(F.data.startswith("taskdone:"))
async def task_done(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE tasks SET done=TRUE WHERE id=$1 RETURNING text, family_id",
            task_id,
        )

    await notify_family(
        row["family_id"],
        f"✅ Задача выполнена:\n{row['text']}",
        callback.from_user.id,
        "important",
    )

    await callback.message.delete()
    await callback.message.answer("Готово ✅", reply_markup=main_menu())

# ======================
# SHOPPING
# ======================

@dp.message(F.text == "🛒 Покупки")
async def shopping(message: Message):
    family_id = await get_family_id(message.from_user.id)

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, text, is_bought FROM shopping WHERE family_id=$1",
            family_id,
        )

    if not rows:
        await message.answer("Покупок нет 🛒", reply_markup=main_menu())
        return

    text = "🛒 Покупки:\n\n"
    for r in rows:
        text += f"{'✅' if r['is_bought'] else '⬜'} {r['text']}\n"

    await message.answer(text, reply_markup=shopping_actions())

@dp.callback_query(F.data == "shop:done")
async def choose_shop(callback: CallbackQuery):
    family_id = await get_family_id(callback.from_user.id)

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, text FROM shopping WHERE family_id=$1 AND is_bought=FALSE",
            family_id,
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=r["text"],
                    callback_data=f"bought:{r['id']}",
                )
            ]
            for r in rows
        ]
    )

    await callback.message.answer("Что купили?", reply_markup=kb)

@dp.callback_query(F.data.startswith("bought:"))
async def bought(callback: CallbackQuery):
    item_id = int(callback.data.split(":")[1])

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE shopping SET is_bought=TRUE WHERE id=$1 RETURNING text, family_id",
            item_id,
        )

    await notify_family(
        row["family_id"],
        f"🛒 Куплено:\n{row['text']}",
        callback.from_user.id,
    )

    await callback.message.delete()
    await callback.message.answer("Отмечено ✅", reply_markup=main_menu())

@dp.callback_query(F.data == "shop:clear")
async def clear_shop(callback: CallbackQuery):
    family_id = await get_family_id(callback.from_user.id)

    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM shopping WHERE family_id=$1 AND is_bought=TRUE",
            family_id,
        )

    await callback.message.delete()
    await callback.message.answer("Очищено 🧹", reply_markup=main_menu())

# ======================
# NOTIFICATIONS SETTINGS
# ======================

@dp.message(F.text == "⚙️ Уведомления")
async def notif_settings(message: Message):
    await message.answer(
        "Настройки уведомлений",
        reply_markup=notification_menu(),
    )

@dp.callback_query(F.data.startswith("notif:"))
async def notif_change(callback: CallbackQuery):
    mode = callback.data.split(":")[1]

    async with db_pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO user_settings (user_id, notifications)
        VALUES ($1,$2)
        ON CONFLICT (user_id) DO UPDATE SET notifications=$2
        """, callback.from_user.id, mode)

    await callback.answer("Сохранено 👍", show_alert=True)
    await callback.message.delete()
    await callback.message.answer("Настройки обновлены", reply_markup=main_menu())

# ======================
# MAIN
# ======================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await init_db()
    print("🤖 Bot started — FULL MVP (aiogram3 / pydantic2 safe)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
