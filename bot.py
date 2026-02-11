import asyncio
from config import BOT_TOKEN, DATABASE_URL
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
from db import init_db, get_pool

# =====================================================
# CONFIG
# =====================================================
if not BOT_TOKEN or not DATABASE_URL:
    raise RuntimeError("ENV variables not set")

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =====================================================
# FSM
# =====================================================

class UserState(StatesGroup):
    confirm_type = State()
    rename_family = State()

# =====================================================
# HELPERS: FAMILY & ROLES
# =====================================================

async def get_member(user_id: int):
    async with get_pool().acquire() as conn:
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
    async with get_pool().acquire() as conn:
        m = await conn.fetchrow(
            "SELECT family_id FROM family_members WHERE user_id=$1",
            user_id
        )
        if m:
            return m["family_id"]

        fam = await conn.fetchrow(
            "INSERT INTO families (title, owner_id) VALUES ('Наша семья', $1) RETURNING id",
            user_id
        )
        await conn.execute(
            "INSERT INTO family_members (user_id, family_id, role) "
            "VALUES ($1,$2,'parent')",
            user_id, fam["id"]
        )
        return fam["id"]

async def add_user_to_family(user_id: int, family_id: int):
    async with get_pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO family_members (user_id, family_id, role)
            VALUES ($1,$2,'child')
            ON CONFLICT (user_id)
            DO UPDATE SET family_id=$2
            """,
            user_id, family_id
        )

# =====================================================
# HELPERS: NOTIFICATIONS
# =====================================================

async def get_notif_mode(user_id: int):
    async with get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT notifications FROM user_settings WHERE user_id=$1",
            user_id
        )
        return row["notifications"] if row else "all"

async def notify_family(family_id: int, text: str, author_id: int, level="all"):
    async with get_pool().acquire() as conn:
        users = await conn.fetch(
            "SELECT user_id FROM family_members "
            "WHERE family_id=$1 AND user_id!=$2",
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
# HELPERS: ACTIVITY LOG
# =====================================================

async def log_action(family_id: int, user_id: int, action: str):
    async with get_pool().acquire() as conn:
        await conn.execute(
            "INSERT INTO activity_log (family_id, user_id, action) "
            "VALUES ($1,$2,$3)",
            family_id, user_id, action
        )

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
        rows.append([KeyboardButton(text="✏️ Название семьи")])
        rows.append([KeyboardButton(text="📜 История")])
        rows.append([KeyboardButton(text="👨‍👩‍👧‍👦 Пригласить")])
        rows.append([KeyboardButton(text="⚙️ Уведомления")])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def confirm_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="📋 Задача", callback_data="confirm:task"),
        InlineKeyboardButton(text="🛒 Покупка", callback_data="confirm:shopping"),
    ]])

def task_actions(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Выполнено", callback_data=f"task:done:{task_id}")
    ]])

def shopping_actions(item_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛒 Куплено", callback_data=f"shop:done:{item_id}")
    ]])
def notification_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔔 Все уведомления", callback_data="notif:all")],
        [InlineKeyboardButton(text="👤 Только важные", callback_data="notif:important")],
        [InlineKeyboardButton(text="🔕 Выключить", callback_data="notif:off")],
    ])

# =====================================================
# HOME
# =====================================================

async def home_text(family_id: int):
    async with get_pool().acquire() as conn:
        title = await conn.fetchval(
            "SELECT title FROM families WHERE id=$1",
            family_id
        )
        t_active = await conn.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE family_id=$1 AND done=FALSE",
            family_id
        )
        s_active = await conn.fetchval(
            "SELECT COUNT(*) FROM shopping WHERE family_id=$1 AND is_bought=FALSE",
            family_id
        )

    return (
        f"🏠 {title}\n\n"
        f"📋 Активные задачи: {t_active}\n"
        f"🛒 Покупки в списке: {s_active}\n\n"
        "Выбери действие 👇"
    )

async def show_home(message: Message):
    family_id = await ensure_family(message.from_user.id)
    parent = await is_parent(message.from_user.id)

    # Сначала убираем старую клавиатуру
    await message.answer(" ", reply_markup=ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True))

    # Потом отправляем нормальное меню
    await message.answer(
        await home_text(family_id),
        reply_markup=main_menu(parent)
    )
    
# =====================================================
# HANDLERS
# =====================================================

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    # ВАЖНО: принудительно обновляем меню
    await show_home(message)

    args = message.text.split()
    if len(args) == 2 and args[1].isdigit():
        await add_user_to_family(message.from_user.id, int(args[1]))
        await message.answer("🎉 Ты присоединился к семье!")

    await show_home(message)

# ==========================
# ДОБАВЛЕНИЕ
# ==========================

@dp.message(F.text == "➕ Добавить")
async def add_any(message: Message, state: FSMContext):
    await state.set_state(UserState.confirm_type)
    await message.answer("Введите текст задачи или покупки:")


@dp.message(UserState.confirm_type)
async def choose_type(message: Message, state: FSMContext):
    await state.update_data(text=message.text)

    await message.answer(
        f"Добавить:\n\n«{message.text}»",
        reply_markup=confirm_keyboard()
    )


@dp.callback_query(F.data.startswith("confirm:"))
async def confirm_add(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("text")

    if not text:
        await callback.answer("Действие устарело", show_alert=True)
        await state.clear()
        return

    family_id = await ensure_family(callback.from_user.id)

    async with get_pool().acquire() as conn:
        if callback.data == "confirm:task":
            await conn.execute(
                "INSERT INTO tasks (family_id, text) VALUES ($1,$2)",
                family_id, text
            )
            await log_action(family_id, callback.from_user.id, f"добавил задачу «{text}»")
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
            await log_action(family_id, callback.from_user.id, f"добавил покупку «{text}»")
            await notify_family(
                family_id,
                f"🛒 Добавлено в покупки:\n{text}",
                callback.from_user.id
            )

    await state.clear()
    await callback.message.delete()
    await show_home(callback.message)


# ==========================
# ЗАДАЧИ
# ==========================

@dp.message(F.text == "📋 Задачи")
async def show_tasks(message: Message):
    family_id = await get_family_id(message.from_user.id)
    async with get_pool().acquire() as conn:
        await conn.execute(
        "DELETE FROM tasks WHERE family_id=$1 AND done=TRUE",
        family_id
        )

    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, text, done FROM tasks WHERE family_id=$1 ORDER BY id DESC",
            family_id
        )

    if not rows:
        await message.answer("📋 Задач пока нет")
        return

    for r in rows:
        status = "✅" if r["done"] else "🔲"

        await message.answer(
            f"{status} {r['text']}",
            reply_markup=task_actions(r["id"]) if not r["done"] else None
        )



# ==========================
# ПОКУПКИ
# ==========================

@dp.message(F.text == "🛒 Покупки")
async def show_shopping(message: Message):
    family_id = await get_family_id(message.from_user.id)

    async with get_pool().acquire() as conn:
        await conn.execute(
        "DELETE FROM shopping WHERE family_id=$1 AND is_bought=TRUE",
        family_id
        )


    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, text, is_bought FROM shopping WHERE family_id=$1 ORDER BY id DESC",
            family_id
        )

    if not rows:
        await message.answer("🛒 Список покупок пуст")
        return

    for r in rows:
        status = "✅" if r["is_bought"] else "🛒"

        await message.answer(
            f"{status} {r['text']}",
            reply_markup=shopping_actions(r["id"]) if not r["is_bought"] else None
        )

# ==========================
# СЕМЬЯ
# ==========================

@dp.message(F.text == "👨‍👩‍👧‍👦 Семья")
async def show_family(message: Message):
    family_id = await get_family_id(message.from_user.id)

    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, role FROM family_members WHERE family_id=$1",
            family_id
        )

    text = "👨‍👩‍👧‍👦 Участники семьи:\n\n"

    for r in rows:
        role = "👑 Родитель" if r["role"] == "parent" else "👶 Ребёнок"

        try:
            chat = await bot.get_chat(r["user_id"])
            name = chat.first_name or "Без имени"
        except:
            name = f"id:{r['user_id']}"

        text += f"{role} — {name}\n"

    await message.answer(text)


@dp.callback_query(F.data.startswith("notif:"))
async def set_notifications(callback: CallbackQuery):
    mode = callback.data.split(":")[1]
    user_id = callback.from_user.id

    async with get_pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO user_settings (user_id, notifications)
            VALUES ($1,$2)
            ON CONFLICT (user_id)
            DO UPDATE SET notifications=$2
            """,
            user_id, mode
        )

    text_map = {
        "all": "🔔 Теперь ты получаешь ВСЕ уведомления",
        "important": "👤 Теперь только важные уведомления",
        "off": "🔕 Уведомления выключены",
    }

    await callback.answer(text_map[mode], show_alert=True)
    await callback.message.edit_reply_markup()

@dp.callback_query(F.data == "family:remove")
async def choose_member_to_remove(callback: CallbackQuery):
    user_id = callback.from_user.id

    if not await is_parent(user_id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    family_id = await get_family_id(user_id)

    async with get_pool().acquire() as conn:
        members = await conn.fetch(
            "SELECT user_id, role FROM family_members WHERE family_id=$1",
            family_id
        )

    buttons = []
    for m in members:
        if m["user_id"] == user_id:
            continue  # нельзя удалить себя

        role_icon = "👑" if m["role"] == "parent" else "👶"
        buttons.append([
            InlineKeyboardButton(
                text=f"{role_icon} {m['user_id']}",
                callback_data=f"remove:{m['user_id']}"
            )
        ])

    if not buttons:
        await callback.answer("Некого удалять", show_alert=True)
        return

    await callback.message.edit_text(
        "Выберите участника для удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
@dp.callback_query(F.data.startswith("remove:"))
async def remove_member(callback: CallbackQuery):
    requester_id = callback.from_user.id
    target_id = int(callback.data.split(":")[1])

    if not await is_parent(requester_id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return

    family_id = await get_family_id(requester_id)

    async with get_pool().acquire() as conn:
        # Проверяем участника
        target = await conn.fetchrow(
            "SELECT role FROM family_members WHERE user_id=$1 AND family_id=$2",
            target_id, family_id
        )

        if not target:
            await callback.answer("Участник не найден", show_alert=True)
            return

        # Защита последнего родителя
        if target["role"] == "parent":
            parents_count = await conn.fetchval(
                "SELECT COUNT(*) FROM family_members WHERE family_id=$1 AND role='parent'",
                family_id
            )
            if parents_count <= 1:
                await callback.answer("Нельзя удалить последнего родителя", show_alert=True)
                return

        # Удаляем
        await conn.execute(
            "DELETE FROM family_members WHERE user_id=$1 AND family_id=$2",
            target_id, family_id
        )

    await log_action(family_id, requester_id, f"удалил участника {target_id}")
    await notify_family(
        family_id,
        f"❌ Участник {target_id} был удалён из семьи",
        requester_id,
        "important"
    )

    try:
        await bot.send_message(target_id, "❌ Вы были удалены из семьи")
    except:
        pass

    await callback.answer("Участник удалён", show_alert=True)
    await callback.message.delete()

@dp.callback_query(F.data.startswith("task:done:"))
async def mark_task_done(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[2])

    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE tasks SET done=TRUE WHERE id=$1",
            task_id
        )

    await callback.answer("Задача выполнена ✅")
    await callback.message.edit_reply_markup()

@dp.callback_query(F.data.startswith("shop:done:"))
async def mark_shop_done(callback: CallbackQuery):
    item_id = int(callback.data.split(":")[2])

    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE shopping SET is_bought=TRUE WHERE id=$1",
            item_id
        )

    await callback.answer("Покупка отмечена ✅")
    await callback.message.edit_reply_markup()

@dp.message(F.text == "✏️ Название семьи")
async def rename_family_start(message: Message, state: FSMContext):
    if not await is_parent(message.from_user.id):
        return
    await state.set_state(UserState.rename_family)
    await message.answer("✏️ Введите новое название семьи:")
@dp.message(F.text == "⚙️ Уведомления")
async def notifications_menu(message: Message):
    await message.answer(
        "🔔 Настройки уведомлений:\n\n"
        "• Все — получать все события\n"
        "• Только важные — задачи, переименования\n"
        "• Выключить — без уведомлений",
        reply_markup=notification_menu()
    )

@dp.message(UserState.rename_family)
async def rename_family_save(message: Message, state: FSMContext):
    family_id = await get_family_id(message.from_user.id)
    title = message.text.strip()[:50]

    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE families SET title=$1 WHERE id=$2",
            title, family_id
        )

    await log_action(family_id, message.from_user.id, f"переименовал семью в «{title}»")
    await notify_family(
        family_id,
        f"🏠 Название семьи изменено на:\n{title}",
        message.from_user.id,
        "important"
    )

    await state.clear()
    await show_home(message)



# =====================================================
# MAIN
# =====================================================

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await init_db()
    print("🤖 Bot started — FAMILY NAME VERSION")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
