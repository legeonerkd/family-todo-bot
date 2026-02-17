from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from db import ensure_family, add_user_to_family, is_parent
from keyboards.main_menu import main_menu

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    args = message.text.split()

    if len(args) == 2 and args[1].isdigit():
        await add_user_to_family(message.from_user.id, int(args[1]))
        await message.answer("🎉 Вы присоединились к семье!")
    else:
        await ensure_family(message.from_user.id)

    parent = await is_parent(message.from_user.id)
    await message.answer("Добро пожаловать 👋", reply_markup=main_menu(parent))
