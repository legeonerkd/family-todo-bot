from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from db import get_family_id, get_pool, log_activity

router = Router()

@router.message(F.text == "🛒 Покупки")
async def show_shopping(message: Message):
    family_id = await get_family_id(message.from_user.id)
    
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, text FROM shopping WHERE family_id=$1 AND completed=false ORDER BY created_at",
            family_id
        )
    
    if not rows:
        await message.answer("🛒 Список покупок пуст")
        return
    
    text = "🛒 Список покупок:\n\n"
    buttons = []
    
    for i, r in enumerate(rows, 1):
        text += f"{i}. {r['text']}\n"
        button_text = r['text'] if len(r['text']) <= 30 else r['text'][:27] + "..."
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
    
    async with get_pool().acquire() as conn:
        shop = await conn.fetchrow(
            "SELECT text FROM shopping WHERE id=$1 AND family_id=$2",
            shop_id, family_id
        )
        
        if shop:
            await conn.execute(
                "UPDATE shopping SET completed=true WHERE id=$1",
                shop_id
            )
            await log_activity(family_id, callback.from_user.id, f"Купил: {shop['text']}")
    
    await callback.message.delete()
    await callback.answer("Покупка выполнена! ✅")
