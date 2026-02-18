from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from db import bot, ensure_family, is_parent
from keyboards.main_meny import main_menu

router = Router()

@router.message(CommandStart())
async def start(message: Message):
    family_id = await ensure_family(message.from_user.id)
    parent = await is_parent(message.from_user.id)

    await message.answer(
        "🏠 Добро пожаловать!",
        reply_markup=main_menu(parent)
    )
