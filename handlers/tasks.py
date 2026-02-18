from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states.user_states import UserState
from keyboards.confirm import confirm_keyboard
from db import get_family_id, get_pool, log_activity

router = Router()

@router.message(F.text == "➕ Добавить")
async def add_task(message: Message, state: FSMContext):
    await state.set_state(UserState.confirm_type)
    await message.answer("Введите текст задачи или покупки:")

@router.message(UserState.confirm_type)
async def choose_type(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer(
        f"Добавить:\n\n«{message.text}»",
        reply_markup=confirm_keyboard()
    )

@router.callback_query(F.data.startswith("confirm:"))
async def confirm_add(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("text")

    family_id = await get_family_id(callback.from_user.id)

    async with get_pool().acquire() as conn:
        if callback.data == "confirm:task":
            await conn.execute(
                "INSERT INTO tasks (family_id, text) VALUES ($1,$2)",
                family_id, text
            )
            await log_activity(family_id, callback.from_user.id, f"Добавил задачу: {text}")
        else:
            await conn.execute(
                "INSERT INTO shopping (family_id, text) VALUES ($1,$2)",
                family_id, text
            )
            await log_activity(family_id, callback.from_user.id, f"Добавил покупку: {text}")

    await state.clear()
    await callback.message.delete()
    await callback.answer("Добавлено ✅")

@router.message(F.text == "📋 Задачи")
async def show_tasks(message: Message):
    try:
        family_id = await get_family_id(message.from_user.id)
        
        if not family_id:
            await message.answer("❌ Ошибка: вы не состоите в семье")
            return
        
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, text FROM tasks WHERE family_id=$1 AND completed=false ORDER BY created_at",
                family_id
            )
        
        if not rows:
            await message.answer("📋 Нет активных задач")
            return
    except Exception as e:
        print(f"Error in show_tasks: {e}")
        await message.answer(f"❌ Ошибка при загрузке задач: {str(e)}")
        return
    
    text = "📋 Активные задачи:\n\n"
    buttons = []
    
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r['text']}\n"
        button_text = r['text'] if len(r['text']) <= 30 else r['text'][:27] + "..."
        buttons.append([InlineKeyboardButton(
            text=f"✅ {button_text}",
            callback_data=f"task_done:{r['id']}"
        )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("task_done:"))
async def mark_task_done(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    family_id = await get_family_id(callback.from_user.id)
    
    async with get_pool().acquire() as conn:
        task = await conn.fetchrow(
            "SELECT text FROM tasks WHERE id=$1 AND family_id=$2",
            task_id, family_id
        )
        
        if task:
            await conn.execute(
                "UPDATE tasks SET completed=true WHERE id=$1",
                task_id
            )
            await log_activity(family_id, callback.from_user.id, f"Выполнил задачу: {task['text']}")
    
    await callback.message.delete()
    await callback.answer("Задача выполнена! ✅")
