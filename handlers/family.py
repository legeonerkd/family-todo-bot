from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.user_states import UserState
from db import bot, get_family_id, get_pool, is_parent, log_activity

router = Router()

@router.message(F.text == "👨‍👩‍👧‍👦 Семья")
async def show_family(message: Message):
    family_id = await get_family_id(message.from_user.id)

    async with get_pool().acquire() as conn:
        family = await conn.fetchrow(
            "SELECT name FROM families WHERE id=$1",
            family_id
        )
        
        rows = await conn.fetch(
            "SELECT user_id, role FROM family_members WHERE family_id=$1",
            family_id
        )

    family_name = family["name"] if family else "Моя семья"
    text = f"👨‍👩‍👧‍👦 {family_name}\n\nУчастники:\n\n"

    for r in rows:
        try:
            chat = await bot.get_chat(r["user_id"])
            name = chat.first_name
        except:
            name = str(r["user_id"])

        role = "👑 Родитель" if r["role"] == "parent" else "👶 Ребёнок"
        text += f"{role} — {name}\n"

    await message.answer(text)

@router.message(F.text == "✏️ Название семьи")
async def rename_family_start(message: Message, state: FSMContext):
    if not await is_parent(message.from_user.id):
        await message.answer("Только родитель может изменить название семьи.")
        return
    
    await state.set_state(UserState.rename_family)
    await message.answer("Введите новое название семьи:")

@router.message(UserState.rename_family)
async def rename_family_finish(message: Message, state: FSMContext):
    family_id = await get_family_id(message.from_user.id)
    new_name = message.text.strip()
    
    async with get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE families SET name=$1 WHERE id=$2",
            new_name, family_id
        )
    
    await log_activity(family_id, message.from_user.id, f"Изменил название семьи на: {new_name}")
    await state.clear()
    await message.answer(f"✅ Название семьи изменено на: {new_name}")

@router.message(F.text == "👨‍👩‍👧‍👦 Пригласить")
async def invite_member(message: Message):
    if not await is_parent(message.from_user.id):
        await message.answer("Только родитель может приглашать участников.")
        return
    
    family_id = await get_family_id(message.from_user.id)
    
    invite_link = f"https://t.me/{(await bot.get_me()).username}?start=join_{family_id}"
    
    await message.answer(
        f"👨‍👩‍👧‍👦 Пригласительная ссылка:\n\n{invite_link}\n\n"
        "Отправьте эту ссылку члену семьи для присоединения."
    )
