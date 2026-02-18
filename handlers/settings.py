from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from states.user_states import UserState
from db import get_family_id, get_pool, is_parent, log_activity, get_family_settings

router = Router()

@router.message(F.text == "🎨 Настройки")
async def show_settings(message: Message):
    if not await is_parent(message.from_user.id):
        await message.answer("Только родитель может изменять настройки.")
        return
    
    family_id = await get_family_id(message.from_user.id)
    settings = await get_family_settings(family_id)
    
    text = f"🎨 Настройки семьи: {settings['name']}\n\n"
    text += "Текущие эмодзи:\n\n"
    text += f"{settings['emoji_add']} Добавить\n"
    text += f"{settings['emoji_task']} Задачи\n"
    text += f"{settings['emoji_shopping']} Покупки\n"
    text += f"{settings['emoji_family']} Семья\n"
    text += f"{settings['emoji_history']} История\n\n"
    text += "Выберите, что хотите изменить:"
    
    buttons = [
        [InlineKeyboardButton(text="➕ Изменить 'Добавить'", callback_data="emoji:add")],
        [InlineKeyboardButton(text="📋 Изменить 'Задачи'", callback_data="emoji:task")],
        [InlineKeyboardButton(text="🛒 Изменить 'Покупки'", callback_data="emoji:shopping")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 Изменить 'Семья'", callback_data="emoji:family")],
        [InlineKeyboardButton(text="📜 Изменить 'История'", callback_data="emoji:history")],
        [InlineKeyboardButton(text="🔄 Сбросить всё", callback_data="emoji:reset")]
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("emoji:"))
async def change_emoji(callback: CallbackQuery, state: FSMContext):
    emoji_type = callback.data.split(":")[1]
    
    if emoji_type == "reset":
        # Сбрасываем все эмодзи на дефолтные
        family_id = await get_family_id(callback.from_user.id)
        
        async with get_pool().acquire() as conn:
            await conn.execute(
                """UPDATE families SET 
                   emoji_task='📋', emoji_shopping='🛒', emoji_family='👨‍👩‍👧‍👦',
                   emoji_history='📜', emoji_add='➕'
                   WHERE id=$1""",
                family_id
            )
        
        await log_activity(family_id, callback.from_user.id, "Сбросил настройки эмодзи", 'other')
        await callback.message.delete()
        await callback.answer("✅ Эмодзи сброшены на стандартные")
        return
    
    # Запоминаем тип эмодзи для изменения
    await state.set_state(UserState.change_emoji)
    await state.update_data(emoji_type=emoji_type)
    
    emoji_names = {
        'add': 'Добавить',
        'task': 'Задачи',
        'shopping': 'Покупки',
        'family': 'Семья',
        'history': 'История'
    }
    
    await callback.message.edit_text(
        f"Отправьте новый эмодзи для кнопки '{emoji_names[emoji_type]}':\n\n"
        "Например: 🎯 или 🏠 или любой другой эмодзи"
    )

@router.message(UserState.change_emoji)
async def save_emoji(message: Message, state: FSMContext):
    data = await state.get_data()
    emoji_type = data.get('emoji_type')
    new_emoji = message.text.strip()
    
    # Проверяем, что это один символ (эмодзи)
    if len(new_emoji) > 5:  # Эмодзи могут быть составными
        await message.answer("❌ Пожалуйста, отправьте только один эмодзи")
        return
    
    family_id = await get_family_id(message.from_user.id)
    
    # Обновляем эмодзи в базе
    column_name = f"emoji_{emoji_type}"
    async with get_pool().acquire() as conn:
        await conn.execute(
            f"UPDATE families SET {column_name}=$1 WHERE id=$2",
            new_emoji, family_id
        )
    
    emoji_names = {
        'add': 'Добавить',
        'task': 'Задачи',
        'shopping': 'Покупки',
        'family': 'Семья',
        'history': 'История'
    }
    
    await log_activity(family_id, message.from_user.id, f"Изменил эмодзи '{emoji_names[emoji_type]}' на {new_emoji}", 'other')
    await state.clear()
    await message.answer(f"✅ Эмодзи для '{emoji_names[emoji_type]}' изменён на {new_emoji}")
