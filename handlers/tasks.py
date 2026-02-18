from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from states.user_states import UserState
from keyboards.confirm import confirm_keyboard
from db import get_family_id, get_pool

router = Router()

@router.message(F.text == "➕ Добавить")
async def add_task(message: Message, state):
    await state.set_state(UserState.confirm_type)
    await message.answer("Введите текст задачи или покупки:")

@router.message(UserState.confirm_type)
async def choose_type(message: Message, state):
    await state.update_data(text=message.text)
    await message.answer(
        f"Добавить:\n\n«{message.text}»",
        reply_markup=confirm_keyboard()
    )

@router.callback_query(F.data.startswith("confirm:"))
async def confirm_add(callback: CallbackQuery, state):
    data = await state.get_data()
    text = data.get("text")

    family_id = await get_family_id(callback.from_user.id)

    async with get_pool().acquire() as conn:
        if callback.data == "confirm:task":
            await conn.execute(
                "INSERT INTO tasks (family_id, text) VALUES ($1,$2)",
                family_id, text
            )
        else:
            await conn.execute(
                "INSERT INTO shopping (family_id, text) VALUES ($1,$2)",
                family_id, text
            )

    await state.clear()
    await callback.message.delete()
    await callback.answer("Добавлено ✅")
