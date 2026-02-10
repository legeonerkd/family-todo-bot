from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📋 Задачи"),
            KeyboardButton(text="🛒 Покупки"),
        ],
        [
            KeyboardButton(text="➕ Добавить задачу"),
            KeyboardButton(text="➕ Добавить покупку"),
        ],
        [
            KeyboardButton(text="👨‍👩‍👧‍👦 Семья"),
        ]
    ],
    resize_keyboard=True
)
