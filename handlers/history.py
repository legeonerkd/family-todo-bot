from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_pool
from services.family_service import get_family_id, is_parent

router = Router()

PAGE_SIZE = 5


@router.message(F.text == "📜 История")
async def show_history(message: Message):
    if not await is_parent(message.from_user.id):
        await message.answer("⛔ Только родитель может смотреть историю")
        return

    await send_history_page(message, 0)


async def send_history_page(message: Message, page: int):
    family_id = await get_family_id(message.from_user.id)

    limit = PAGE_SIZE
    offset = page * limit

    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT action, created_at
            FROM activity_log
            WHERE family_id=$1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            family_id,
            limit,
            offset
        )

    if not rows:
        await message.answer("📜 История пуста")
        return

    text = f"📜 История (стр. {page+1})\n\n"

    for r in rows:
        time = r["created_at"].strftime("%d.%m %H:%M")
        text += f"🕒 {time}\n📌 {r['action']}\n\n"

    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="⬅ Назад",
                callback_data=f"history:{page-1}"
            )
        )

    if len(rows) == limit:
        buttons.append(
            InlineKeyboardButton(
                text="Вперёд ➡",
                callback_data=f"history:{page+1}"
            )
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[buttons] if buttons else []
    )

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("history:"))
async def change_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])

    await callback.message.delete()
    await send_history_page(callback.message, page)
    await callback.answer()
