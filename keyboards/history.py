from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def history_keyboard(page: int, has_next: bool, filter_type: str = 'all'):
    """Клавиатура для навигации по истории с фильтрами"""
    buttons = []
    
    # Кнопки фильтрации
    filter_buttons = [
        InlineKeyboardButton(
            text="🌐 Все" if filter_type == 'all' else "○ Все",
            callback_data=f"history_filter:all:0"
        ),
        InlineKeyboardButton(
            text="📋 Задачи" if filter_type == 'task' else "○ Задачи",
            callback_data=f"history_filter:task:0"
        ),
        InlineKeyboardButton(
            text="🛒 Покупки" if filter_type == 'shopping' else "○ Покупки",
            callback_data=f"history_filter:shopping:0"
        )
    ]
    
    admin_filter_buttons = [
        InlineKeyboardButton(
            text="👑 Роли" if filter_type == 'role' else "○ Роли",
            callback_data=f"history_filter:role:0"
        ),
        InlineKeyboardButton(
            text="🗂 Админ" if filter_type == 'admin' else "○ Админ",
            callback_data=f"history_filter:admin:0"
        )
    ]
    
    buttons.append(filter_buttons)
    buttons.append(admin_filter_buttons)
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅ Назад", callback_data=f"history:{filter_type}:{page-1}")
        )

    if has_next:
        nav_buttons.append(
            InlineKeyboardButton(text="Вперёд ➡", callback_data=f"history:{filter_type}:{page+1}")
        )
    
    if nav_buttons:
        buttons.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=buttons)
