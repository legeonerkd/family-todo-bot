from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards.history import history_keyboard
from db import bot, get_family_id, get_pool, is_parent

router = Router()

PAGE_SIZE = 5

@router.message(F.text == "📜 История")
async def show_history(message: Message):
    if not await is_parent(message.from_user.id):
        await message.answer("Только родитель может смотреть историю.")
        return

    await send_history_page(message, 0)

@router.callback_query(F.data.startswith("history:"))
async def change_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    
    # Получаем данные для новой страницы
    family_id = await get_family_id(callback.from_user.id)
    offset = page * PAGE_SIZE
    
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT action, created_at, user_id
            FROM activity_log
            WHERE family_id=$1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            family_id,
            PAGE_SIZE,
            offset
        )
    
    if not rows:
        await callback.answer("📜 История пуста", show_alert=True)
        return
    
    text = f"📜 История (страница {page+1})\n\n"
    
    for r in rows:
        time_str = r["created_at"].strftime("%d.%m %H:%M")
        try:
            chat = await bot.get_chat(r["user_id"])
            name = chat.first_name
        except:
            name = "Неизвестно"
        
        text += f"🕒 {time_str}\n👤 {name}\n📌 {r['action']}\n\n"
    
    keyboard = history_keyboard(page, len(rows) == PAGE_SIZE)
    
    # Редактируем существующее сообщение вместо удаления
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

async def send_history_page(message: Message, page: int):
    family_id = await get_family_id(message.from_user.id)

    offset = page * PAGE_SIZE

    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT action, created_at, user_id
            FROM activity_log
            WHERE family_id=$1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            family_id,
            PAGE_SIZE,
            offset
        )

    if not rows:
        await message.answer("📜 История пуста")
        return

    text = f"📜 История (страница {page+1})\n\n"

    for r in rows:
        time_str = r["created_at"].strftime("%d.%m %H:%M")
        try:
            chat = await bot.get_chat(r["user_id"])
            name = chat.first_name
        except:
            name = "Неизвестно"

        text += f"🕒 {time_str}\n👤 {name}\n📌 {r['action']}\n\n"

    keyboard = history_keyboard(page, len(rows) == PAGE_SIZE)

    await message.answer(text, reply_markup=keyboard)
