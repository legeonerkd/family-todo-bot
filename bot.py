import asyncio
import os
import asyncpg

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# =====================================================
# CONFIG
# =====================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN or not DATABASE_URL:
    raise RuntimeError("ENV variables not set")

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db_pool: asyncpg.Pool | None = None

# =====================================================
# FSM
# =====================================================

class UserState(StatesGroup):
    confirm_type = State()

# =====================================================
# DB INIT
# =====================================================

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

# =====================================================
# HELPERS: FAMILY & ROLES
# =====================================================

async def get_member(user_id: int):
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT family_id, role FROM family_members WHERE user_id=$1",
            user_id
        )

async def get_family_id(user_id: int):
    m = await get_member(user_id)
    return m["family_id"] if m else None

async def is_parent(user_id: int) -> bool:
    m = await get_member(user_id)
    return bool(m and m["role"] == "parent")

async def ensure_family(user_id: int):
    async with db_pool.acquire() as conn:
        m = await conn.fetchrow(
            "SELECT family_id FROM family_members WHERE user_id=$1",
            user_id
        )
        if m:
            return m["family_id"]

        fam = await conn.fetchrow(
            "INSERT INTO families (owner_id) VALUES ($1) RETURNING id",
            user_id
        )
        await conn.execute(
            "INSERT INTO family_members (user_id, family_id, role) VALUES ($1,$2,'parent')",
            user_id, fam["id"]
        )
        return fam["id"]

async def add_user_to_family(user_id: int, family_id: int):
    async with db_pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO family_members (user_id, family_id, role)
        VALUES ($1,$2,'child')
        ON CONFLICT (user_id)
        DO UPDATE SET family_id=$2
        """, user_id, family_id)

# =====================================================
# HELPERS: NOTIFICATIONS
# =====================================================

async def get_notif_mode(user_id: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT notifications FROM user_settings WHERE user_id=$1",
            user_id
        )
        return row["notifications"] if row else "all"

async def notify_family(family_id: int, text: str, author_id: int, level="all"):
    async with db_pool.acquire() as conn:
        users = await conn.fetch(
            "SELECT user_id FROM family_members WHERE family_id=$1 AND user_id!=$2",
            family_id, author_id
        )

    for u in users:
        mode = await get_notif_mode(u["user_id"])
        if mode == "off":
            continue
        if mode == "important" and level != "important":
            continue
        try:
            await bot.send_message(u["user_id"], text)
        except:
            pass

# =====================================================
# UI
# =====================================================

def main_menu(is_parent: bool):
    rows = [
        [KeyboardButton(text="➕ Добавить")],
        [
            KeyboardButton(text="📋 Задачи"),
            KeyboardButton(text="🛒 Покупки")
        ],
        [KeyboardButton(text="👨‍👩‍👧‍👦 Семья")]
    ]
    if is_parent:
        rows.append([KeyboardButton(text="👨‍👩‍👧‍👦 Пригласить")])
        rows.append([KeyboardButton(text="⚙️ Уведомления")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def confirm_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📋 Задача", callback_data="confirm:task"),
        InlineKeyboardButton(text="🛒 Покупка", callback_data="confirm:shopping"),
    ]])

def shopping_actions(is_parent: bool):
    rows = [
        [InlineKeyboardButton(text="✅ Отметить купленным", callback_data="shop:done")]
    ]
    if is_parent:
        rows.append(
            [InlineKeyboardButton(text="🧹 Очистить купленные", callback_data="shop:clear")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)

def notification_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔔 Все", callback_data="notif:all")],
        [InlineKeyboardButton(text="👤 Только важные", callback_data="notif:important")],
        [InlineKeyboardButton(text="🔕 Выключить", callback_data="notif:off")]
    ])

# =====================================================
# HOME
# =====================================================

async def home_text(family_id: int):
    async with db_pool.acquire() as conn:
        t_total = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE family_id=$1", family_id
        )
        t_active = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE family_id=$1 AND done=FALSE", family_id
        )
        s_active = await conn.fetchval(
            "SELECT COUNT(*) FROM shopping WHERE family_id=$1 AND is_bought=FALSE", family_id
        )

    return (
        "👨‍👩‍👧 Семейный менеджер\n\n"
        f"📋 Активные задачи: {t_active} / {t_total}\n"
        f"🛒 Покупки в списке: {s_active}\n\n"
        "Выбери действие 👇"
    )

async def show_home(message: Message):
    family_id = await ensure_family(message.from_user.id)
    parent = await is_parent(message.from_user.id)
    await message.answer(
        await home_text(family_id),
        reply_markup=main_menu(parent)
    )

# =====================================================
# START / INVITE
# =====================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    args = message.text.split()
    if len(args) == 2 and args[1].isdigit():
        await add_user_to_family(message.from_user.id, int(args[1]))
        await message.answer("🎉 Ты присоединился к семье!")
    await show_home(message)

@dp.message(F.text == "👨‍👩‍👧‍👦 Пригласить")
async def invite(message: Message):
    if not await is_parent(message.from_user.id):
        return
    family_id = await ensure_family(message.from_user.id)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={family_id}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Присоединиться к семье", url=link)]
    ])
    await message.answer("Отправь ссылку 👇", reply_markup=kb)

# =====================================================
# FAMILY LIST
# =====================================================

@dp.message(F.text == "👨‍👩‍👧‍👦 Семья")
async def show_family(message: Message):
    family_id = await ensure_family(message.from_user.id)
    async with db_pool.acquire() as conn:
        members = await conn.fetch(
            "SELECT user_id, role FROM family_members WHERE family_id=$1",
            family_id
        )

    lines = ["👨‍👩‍👧‍👦 Семья:\n"]
    for m in members:
        try:
            chat = await bot.get_chat(m["user_id"])
            name = chat.first_name or "Без имени"
        except:
            name = "Неизвестный"
        role = "👑 Родитель" if m["role"] == "parent" else "👶 Ребёнок"
        lines.append(f"• {name} — {role}")

    await message.answer("\n".join(lines), reply_markup=main_menu(await is_parent(message.from_user.id)))

# =====================================================
# ADD FLOW
# =====================================================

@dp.message(F.text == "➕ Добавить")
async def add_any(message: Message, state: FSMContext):
    await state.set_state(UserState.confirm_type)
    await message.answer("Что нужно добавить?")

@dp.message(UserState.confirm_type)
async def choose_type(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer(
        f"Добавить:\n\n«{message.text}»",
        reply_markup=confirm_keyboard()
    )

@dp.callback_query(F.data.startswith("confirm:"))
async def confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data["text"]
    family_id = await ensure_family(callback.from_user.id)

    async with db_pool.acquire() as conn:
        if callback.data == "confirm:task":
            await conn.execute(
                "INSERT INTO tasks (family_id, text) VALUES ($1,$2)",
                family_id, text
            )
            await notify_family(
                family_id,
                f"🆕 Новая задача:\n{text}",
                callback.from_user.id,
                "important"
            )
        else:
            await conn.execute(
                "INSERT INTO shopping (family_id, text) VALUES ($1,$2)",
                family_id, text
            )
            await notify_family(
                family_id,
                f"🛒 Добавлено в покупки:\n{text}",
                callback.from_user.id
            )

    await state.clear()
    await callback.message.delete()
    await show_home(callback.message)

# =====================================================
# TASKS
# =====================================================

@dp.message(F.text == "📋 Задачи")
async def tasks(message: Message):
    family_id = await get_family_id(message.from_user.id)
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, text, done FROM tasks WHERE family_id=$1",
            family_id
        )

    if not rows:
        await show_home(message)
        return

    text = "📋 Задачи:\n\n"
    kb = []
    for r in rows:
        text += f"{'✅' if r['done'] else '⬜'} {r['text']}\n"
        if not r["done"]:
            kb.append([
                InlineKeyboardButton(
                    text=f"✔ {r['text']}",
                    callback_data=f"taskdone:{r['id']}"
                )
            ])

    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@dp.callback_query(F.data.startswith("taskdone:"))
async def task_done(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE tasks SET done=TRUE WHERE id=$1 RETURNING text, family_id",
            task_id
        )

    await notify_family(
        row["family_id"],
        f"✅ Задача выполнена:\n{row['text']}",
        callback.from_user.id,
        "important"
    )

    await callback.message.delete()
    await show_home(callback.message)

# =====================================================
# SHOPPING
# =====================================================

@dp.message(F.text == "🛒 Покупки")
async def shopping(message: Message):
    family_id = await get_family_id(message.from_user.id)
    parent = await is_parent(message.from_user.id)

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, text, is_bought FROM shopping WHERE family_id=$1",
            family_id
        )

    text = "🛒 Покупки:\n\n"
    for r in rows:
        text += f"{'✅' if r['is_bought'] else '⬜'} {r['text']}\n"

    await message.answer(text, reply_markup=shopping_actions(parent))

@dp.callback_query(F.data == "shop:done")
async def choose_shop(callback: CallbackQuery):
    family_id = await get_family_id(callback.from_user.id)
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, text FROM shopping WHERE family_id=$1 AND is_bought=FALSE",
            family_id
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=r["text"], callback_data=f"bought:{r['id']}")]
        for r in rows
    ])

    await callback.message.answer("Что купили?", reply_markup=kb)

@dp.callback_query(F.data.startswith("bought:"))
async def bought(callback: CallbackQuery):
    item_id = int(callback.data.split(":")[1])
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE shopping SET is_bought=TRUE WHERE id=$1 RETURNING text, family_id",
            item_id
        )

    await notify_family(
        row["family_id"],
        f"🛒 Куплено:\n{row['text']}",
        callback.from_user.id
    )

    await callback.message.delete()
    await show_home(callback.message)

@dp.callback_query(F.data == "shop:clear")
async def clear_shop(callback: CallbackQuery):
    if not await is_parent(callback.from_user.id):
        return
    family_id = await get_family_id(callback.from_user.id)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM shopping WHERE family_id=$1 AND is_bought=TRUE",
            family_id
        )
    await callback.message.delete()
    await show_home(callback.message)

# =====================================================
# NOTIFICATION SETTINGS
# =====================================================

@dp.message(F.text == "⚙️ Уведомления")
async def notif_settings(message: Message):
    if not await is_parent(message.from_user.id):
        return
    await message.answer("Настройки уведомлений", reply_markup=notification_menu())

@dp.callback_query(F.data.startswith("notif:"))
async def notif_change(callback: CallbackQuery):
    if not await is_parent(callback.from_user.id):
        return
    mode = callback.data.split(":")[1]
    async with db_pool.acquire() as conn:
        await conn.execute("""
        INSERT INTO user_settings (user_id, notifications)
        VALUES ($1,$2)
        ON CONFLICT (user_id) DO UPDATE SET notifications=$2
        """, callback.from_user.id, mode)

    await callback.answer("Сохранено 👍", show_alert=True)
    await callback.message.delete()
    await show_home(callback.message)

# =====================================================
# MAIN
# =====================================================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await init_db()
    print("🤖 Bot started — FULL BASELINE MVP WITH ROLES")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
