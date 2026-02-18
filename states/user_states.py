from aiogram.fsm.state import StatesGroup, State

class UserState(StatesGroup):
    confirm_type = State()
    rename_family = State()
    change_emoji = State()
