from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states.user_states import UserState
from keyboards.confirm import confirm_keyboard
from db import get_family_id, get_pool, log_activity, bot

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
    task_type = callback.data.split(":")[1]
    
    await state.update_data(task_type=task_type)
    
    # Показываем список членов семьи для выбора исполнителя
    family_id = await get_family_id(callback.from_user.id)
    
    async with get_pool().acquire() as conn:
        members = await conn.fetch(
            "SELECT user_id FROM family_members WHERE family_id=$1",
            family_id
        )
    
    buttons = []
    for member in members:
        try:
            chat = await bot.get_chat(member["user_id"])
            name = chat.first_name
        except:
            name = str(member["user_id"])
        
        buttons.append([InlineKeyboardButton(
            text=f"👤 {name}",
            callback_data=f"assign:{task_type}:{member['user_id']}"
        )])
    
    buttons.append([InlineKeyboardButton(
        text="🌐 Всем",
        callback_data=f"assign:{task_type}:all"
    )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        f"Кому назначить?\n\n«{text}»",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("assign:"))
async def assign_task(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get("text")
    
    parts = callback.data.split(":")
    task_type = parts[1]
    assigned_to = None if parts[2] == "all" else int(parts[2])
    
    family_id = await get_family_id(callback.from_user.id)
    
    async with get_pool().acquire() as conn:
        if task_type == "task":
            await conn.execute(
                "INSERT INTO tasks (family_id, text, created_by, assigned_to) VALUES ($1,$2,$3,$4)",
                family_id, text, callback.from_user.id, assigned_to
            )
            await log_activity(family_id, callback.from_user.id, f"Добавил задачу: {text}")
        else:
            await conn.execute(
                "INSERT INTO shopping (family_id, text, created_by, assigned_to) VALUES ($1,$2,$3,$4)",
                family_id, text, callback.from_user.id, assigned_to
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
                "SELECT id, text, assigned_to FROM tasks WHERE family_id=$1 AND completed=false ORDER BY created_at",
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
        task_text = r['text']
        
        # Добавляем информацию об исполнителе
        if r['assigned_to']:
            try:
                chat = await bot.get_chat(r['assigned_to'])
                assignee = chat.first_name
                task_text += f" (👤 {assignee})"
            except:
                pass
        else:
            task_text += " (🌐 Всем)"
        
        text += f"{i}. {task_text}\n"
        button_text = r['text'] if len(r['text']) <= 25 else r['text'][:22] + "..."
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
