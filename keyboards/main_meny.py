from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu(is_parent: bool):
    rows = [
        [KeyboardButton(text="➕ Добавить")],
        [
            KeyboardButton(text="📋 Задачи"),
            KeyboardButton(text="🛒 Покупки")
        ],
        [KeyboardButton(text="👨‍👩‍👧‍👦 Семья")]
    ]

    if is_parent:
        rows.append([KeyboardButton(text="📜 История")])
        rows.append([
            KeyboardButton(text="✏️ Название семьи"),
            KeyboardButton(text="🎨 Настройки")
        ])
        rows.append([KeyboardButton(text="👨‍👩‍👧‍👦 Пригласить")])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
