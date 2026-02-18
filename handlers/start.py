from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from db import bot, ensure_family, is_parent, get_pool, log_activity
from keyboards.main_meny import main_menu

router = Router()

@router.message(CommandStart())
async def start(message: Message):
    # Проверяем, есть ли параметр приглашения
    args = message.text.split()
    
    if len(args) > 1 and args[1].startswith("join_"):
        # Обработка приглашения
        try:
            family_id = int(args[1].replace("join_", ""))
            
            async with get_pool().acquire() as conn:
                # Проверяем, существует ли семья
                family = await conn.fetchrow(
                    "SELECT name FROM families WHERE id=$1",
                    family_id
                )
                
                if not family:
                    await message.answer("❌ Семья не найдена")
                    return
                
                # Проверяем, не состоит ли пользователь уже в семье
                existing = await conn.fetchrow(
                    "SELECT family_id FROM family_members WHERE user_id=$1",
                    message.from_user.id
                )
                
                if existing:
                    await message.answer("❌ Вы уже состоите в семье")
                    return
                
                # Добавляем пользователя в семью как ребёнка
                await conn.execute(
                    "INSERT INTO family_members (family_id, user_id, role) VALUES ($1, $2, 'child')",
                    family_id, message.from_user.id
                )
            
            await log_activity(family_id, message.from_user.id, "Присоединился к семье", 'join')
            await message.answer(
                f"✅ Вы присоединились к семье: {family['name']}",
                reply_markup=main_menu(False)
            )
            return
            
        except Exception as e:
            await message.answer(f"❌ Ошибка при присоединении: {str(e)}")
            return
    
    # Обычный старт
    family_id = await ensure_family(message.from_user.id)
    parent = await is_parent(message.from_user.id)

    await message.answer(
        "🏠 Добро пожаловать в семейный бот!\n\n"
        "Здесь вы можете:\n"
        "• Создавать задачи и списки покупок\n"
        "• Отмечать выполненные дела\n"
        "• Просматривать историю активности\n"
        "• Управлять семьёй",
        reply_markup=main_menu(parent)
    )
