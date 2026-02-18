from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Задача", callback_data="confirm:task"),
                InlineKeyboardButton(text="🛒 Покупка", callback_data="confirm:shopping")
            ]
        ]
    )
