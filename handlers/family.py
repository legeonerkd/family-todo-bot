from aiogram import Router, F
from aiogram.types import Message
from db import bot, get_family_id, get_pool

router = Router()

@router.message(F.text == "👨‍👩‍👧‍👦 Семья")
async def show_family(message: Message):
    family_id = await get_family_id(message.from_user.id)

    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, role FROM family_members WHERE family_id=$1",
            family_id
        )

    text = "👨‍👩‍👧‍👦 Участники семьи:\n\n"

    for r in rows:
        try:
            chat = await bot.get_chat(r["user_id"])
            name = chat.first_name
        except:
            name = str(r["user_id"])

        role = "👑 Родитель" if r["role"] == "parent" else "👶 Ребёнок"
        text += f"{role} — {name}\n"

    await message.answer(text)
