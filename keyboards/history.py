from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def history_keyboard(page: int, has_next: bool):
    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton(text="⬅ Назад", callback_data=f"history:{page-1}")
        )

    if has_next:
        buttons.append(
            InlineKeyboardButton(text="Вперёд ➡", callback_data=f"history:{page+1}")
        )

    if buttons:
        return InlineKeyboardMarkup(inline_keyboard=[buttons])

    return None
