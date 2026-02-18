"""
Планировщик задач для отправки ежедневных дайджестов
"""
import asyncio
from datetime import datetime, time
from db import bot, get_pool


async def send_daily_digest():
    """Отправка ежедневного дайджеста всем членам семей"""
    print(f"[{datetime.now()}] Sending daily digest...")
    
    async with get_pool().acquire() as conn:
        # Получаем все семьи
        families = await conn.fetch("SELECT id, name FROM families")
        
        for family in families:
            family_id = family["id"]
            family_name = family["name"]
            
            # Получаем активные задачи
            tasks = await conn.fetch(
                "SELECT text, assigned_to FROM tasks WHERE family_id=$1 AND completed=false",
                family_id
            )
            
            # Получаем активные покупки
            shopping = await conn.fetch(
                "SELECT text, assigned_to FROM shopping WHERE family_id=$1 AND completed=false",
                family_id
            )
            
            # Получаем членов семьи
            members = await conn.fetch(
                "SELECT user_id FROM family_members WHERE family_id=$1",
                family_id
            )
            
            if not tasks and not shopping:
                continue  # Пропускаем семьи без активных задач
            
            # Формируем дайджест
            digest = f"📊 Ежедневный дайджест: {family_name}\n\n"
            
            if tasks:
                digest += f"📋 Активные задачи ({len(tasks)}):\n"
                for i, task in enumerate(tasks[:5], 1):  # Показываем первые 5
                    task_text = task["text"]
                    if task["assigned_to"]:
                        try:
                            chat = await bot.get_chat(task["assigned_to"])
                            assignee = f" (👤 {chat.first_name})"
                        except:
                            assignee = ""
                    else:
                        assignee = " (🌐 Всем)"
                    digest += f"{i}. {task_text}{assignee}\n"
                
                if len(tasks) > 5:
                    digest += f"... и ещё {len(tasks) - 5}\n"
                digest += "\n"
            
            if shopping:
                digest += f"🛒 Список покупок ({len(shopping)}):\n"
                for i, shop in enumerate(shopping[:5], 1):  # Показываем первые 5
                    shop_text = shop["text"]
                    if shop["assigned_to"]:
                        try:
                            chat = await bot.get_chat(shop["assigned_to"])
                            assignee = f" (👤 {chat.first_name})"
                        except:
                            assignee = ""
                    else:
                        assignee = " (🌐 Всем)"
                    digest += f"{i}. {shop_text}{assignee}\n"
                
                if len(shopping) > 5:
                    digest += f"... и ещё {len(shopping) - 5}\n"
            
            # Отправляем дайджест всем членам семьи
            for member in members:
                try:
                    await bot.send_message(member["user_id"], digest)
                    print(f"Digest sent to {member['user_id']}")
                except Exception as e:
                    print(f"Failed to send digest to {member['user_id']}: {e}")
    
    print(f"[{datetime.now()}] Daily digest sent!")


async def schedule_daily_digest():
    """Планировщик для отправки дайджеста каждый день в 20:00"""
    while True:
        now = datetime.now()
        # Устанавливаем время отправки - 20:00 (8 PM)
        target_time = time(20, 0)
        
        # Вычисляем время до следующей отправки
        target_datetime = datetime.combine(now.date(), target_time)
        if now.time() > target_time:
            # Если уже прошло 20:00, планируем на завтра
            from datetime import timedelta
            target_datetime += timedelta(days=1)
        
        wait_seconds = (target_datetime - now).total_seconds()
        
        print(f"Next digest scheduled at {target_datetime} (in {wait_seconds/3600:.1f} hours)")
        
        # Ждём до назначенного времени
        await asyncio.sleep(wait_seconds)
        
        # Отправляем дайджест
        await send_daily_digest()
