from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_family_id, get_pool, log_activity, bot

router = Router()

@router.message(F.text == "🛒 Покупки")
async def show_shopping(message: Message):
    try:
        family_id = await get_family_id(message.from_user.id)
        
        if not family_id:
            await message.answer("❌ Ошибка: вы не состоите в семье")
            return
        
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, text, assigned_to FROM shopping WHERE family_id=$1 AND completed=false ORDER BY created_at",
                family_id
            )
        
        if not rows:
            await message.answer("🛒 Список покупок пуст")
            return
    except Exception as e:
        print(f"Error in show_shopping: {e}")
        await message.answer(f"❌ Ошибка при загрузке покупок: {str(e)}")
        return
    
    text = "🛒 Список покупок:\n\n"
    buttons = []
    
    for i, r in enumerate(rows, 1):
        shop_text = r['text']
        
        # Добавляем информацию об исполнителе
        if r['assigned_to']:
            try:
                chat = await bot.get_chat(r['assigned_to'])
                assignee = chat.first_name
                shop_text += f" (👤 {assignee})"
            except:
                pass
        else:
            shop_text += " (🌐 Всем)"
        
        text += f"{i}. {shop_text}\n"
        button_text = r['text'] if len(r['text']) <= 25 else r['text'][:22] + "..."
        buttons.append([InlineKeyboardButton(
            text=f"✅ {button_text}",
            callback_data=f"shop_done:{r['id']}"
        )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("shop_done:"))
async def mark_shopping_done(callback: CallbackQuery):
    shop_id = int(callback.data.split(":")[1])
    family_id = await get_family_id(callback.from_user.id)
    
    # Получаем имя выполнившего
    try:
        executor_chat = await bot.get_chat(callback.from_user.id)
        executor_name = executor_chat.first_name
    except:
        executor_name = "Кто-то"
    
    async with get_pool().acquire() as conn:
        shop = await conn.fetchrow(
            "SELECT text, created_by FROM shopping WHERE id=$1 AND family_id=$2",
            shop_id, family_id
        )
        
        if shop:
            await conn.execute(
                "UPDATE shopping SET completed=true, completed_at=NOW() WHERE id=$1",
                shop_id
            )
            await log_activity(family_id, callback.from_user.id, f"Купил: {shop['text']}")
            
            # Уведомляем создателя о выполнении
            if shop['created_by'] and shop['created_by'] != callback.from_user.id:
                try:
                    await bot.send_message(
                        shop['created_by'],
                        f"✅ Покупка выполнена!\n\n«{shop['text']}»\n\n👤 Купил: {executor_name}"
                    )
                except Exception as e:
                    print(f"Failed to send completion notification: {e}")
    
    await callback.message.delete()
    await callback.answer("Покупка выполнена! ✅")
