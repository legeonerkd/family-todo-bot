from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def task_keyboard(task_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{task_id}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete:{task_id}")
        ]
    ])