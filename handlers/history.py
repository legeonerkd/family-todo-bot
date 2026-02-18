from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards.history import history_keyboard
from db import bot, get_family_id, get_pool, is_parent

router = Router()

PAGE_SIZE = 5

# Эмодзи для типов действий
ACTION_EMOJI = {
    'task': '📋',
    'shopping': '🛒',
    'role': '👑',
    'remove': '❌',
    'rename': '✏️',
    'join': '➕',
    'other': '📌'
}

@router.message(F.text == "📜 История")
async def show_history(message: Message):
    if not await is_parent(message.from_user.id):
        await message.answer("Только родитель может смотреть историю.")
        return

    await send_history_page(message, 0, 'all')

@router.callback_query(F.data.startswith("history:"))
async def change_page(callback: CallbackQuery):
    parts = callback.data.split(":")
    filter_type = parts[1] if len(parts) > 2 else 'all'
    page = int(parts[2]) if len(parts) > 2 else int(parts[1])
    
    # Получаем данные для новой страницы
    family_id = await get_family_id(callback.from_user.id)
    offset = page * PAGE_SIZE
    
    # Формируем запрос с фильтром
    if filter_type == 'all':
        query = """
            SELECT action, created_at, user_id, action_type
            FROM activity_log
            WHERE family_id=$1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        params = (family_id, PAGE_SIZE, offset)
    elif filter_type == 'admin':
        # Админ-логи: роли, удаления, переименования
        query = """
            SELECT action, created_at, user_id, action_type
            FROM activity_log
            WHERE family_id=$1 AND action_type IN ('role', 'remove', 'rename', 'join')
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        params = (family_id, PAGE_SIZE, offset)
    else:
        query = """
            SELECT action, created_at, user_id, action_type
            FROM activity_log
            WHERE family_id=$1 AND action_type=$2
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
        """
        params = (family_id, filter_type, PAGE_SIZE, offset)
    
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(query, *params)
    
    if not rows:
        await callback.answer("📜 История пуста", show_alert=True)
        return
    
    # Формируем текст с эмодзи типов
    filter_names = {
        'all': 'Все',
        'task': 'Задачи',
        'shopping': 'Покупки',
        'role': 'Роли',
        'admin': 'Админ-логи'
    }
    
    text = f"📜 История: {filter_names.get(filter_type, 'Все')} (стр. {page+1})\n\n"
    
    for r in rows:
        time_str = r["created_at"].strftime("%d.%m %H:%M")
        try:
            chat = await bot.get_chat(r["user_id"])
            name = chat.first_name
        except:
            name = "Неизвестно"
        
        emoji = ACTION_EMOJI.get(r.get("action_type", "other"), "📌")
        text += f"{emoji} {time_str} | {name}\n{r['action']}\n\n"
    
    keyboard = history_keyboard(page, len(rows) == PAGE_SIZE, filter_type)
    
    # Редактируем существующее сообщение вместо удаления
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("history_filter:"))
async def filter_history(callback: CallbackQuery):
    parts = callback.data.split(":")
    filter_type = parts[1]
    page = int(parts[2])
    
    # Используем тот же обработчик, что и для навигации
    callback.data = f"history:{filter_type}:{page}"
    await change_page(callback)

async def send_history_page(message: Message, page: int, filter_type: str = 'all'):
    family_id = await get_family_id(message.from_user.id)
    offset = page * PAGE_SIZE

    # Формируем запрос с фильтром
    if filter_type == 'all':
        query = """
            SELECT action, created_at, user_id, action_type
            FROM activity_log
            WHERE family_id=$1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        params = (family_id, PAGE_SIZE, offset)
    elif filter_type == 'admin':
        query = """
            SELECT action, created_at, user_id, action_type
            FROM activity_log
            WHERE family_id=$1 AND action_type IN ('role', 'remove', 'rename', 'join')
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
        """
        params = (family_id, PAGE_SIZE, offset)
    else:
        query = """
            SELECT action, created_at, user_id, action_type
            FROM activity_log
            WHERE family_id=$1 AND action_type=$2
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
        """
        params = (family_id, filter_type, PAGE_SIZE, offset)

    async with get_pool().acquire() as conn:
        rows = await conn.fetch(query, *params)

    if not rows:
        await message.answer("📜 История пуста")
        return

    filter_names = {
        'all': 'Все',
        'task': 'Задачи',
        'shopping': 'Покупки',
        'role': 'Роли',
        'admin': 'Админ-логи'
    }
    
    text = f"📜 История: {filter_names.get(filter_type, 'Все')} (стр. {page+1})\n\n"

    for r in rows:
        time_str = r["created_at"].strftime("%d.%m %H:%M")
        try:
            chat = await bot.get_chat(r["user_id"])
            name = chat.first_name
        except:
            name = "Неизвестно"

        emoji = ACTION_EMOJI.get(r.get("action_type", "other"), "📌")
        text += f"{emoji} {time_str} | {name}\n{r['action']}\n\n"

    keyboard = history_keyboard(page, len(rows) == PAGE_SIZE, filter_type)

    await message.answer(text, reply_markup=keyboard)
