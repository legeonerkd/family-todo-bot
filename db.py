from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, DATABASE_URL
import asyncpg

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Пул соединений с базой данных
_pool = None


async def init_db():
    """Инициализация пула соединений и создание таблиц"""
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL)
    
    async with _pool.acquire() as conn:
        # Таблица семей
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS families (
                id SERIAL PRIMARY KEY,
                name TEXT DEFAULT 'Моя семья',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Таблица членов семьи
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                id SERIAL PRIMARY KEY,
                family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
                user_id BIGINT UNIQUE NOT NULL,
                role TEXT DEFAULT 'child',
                joined_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Таблица задач
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                completed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP
            )
        """)
        
        # Таблица покупок
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shopping (
                id SERIAL PRIMARY KEY,
                family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                completed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                completed_at TIMESTAMP
            )
        """)
        
        # Таблица истории активности
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id SERIAL PRIMARY KEY,
                family_id INTEGER REFERENCES families(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL,
                action TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)


def get_pool():
    """Получить пул соединений"""
    return _pool


async def ensure_family(user_id: int) -> int:
    """Убедиться, что пользователь состоит в семье, если нет - создать новую"""
    async with _pool.acquire() as conn:
        # Проверяем, есть ли пользователь в какой-то семье
        row = await conn.fetchrow(
            "SELECT family_id FROM family_members WHERE user_id=$1",
            user_id
        )
        
        if row:
            return row['family_id']
        
        # Создаем новую семью
        family_id = await conn.fetchval(
            "INSERT INTO families (name) VALUES ('Моя семья') RETURNING id"
        )
        
        # Добавляем пользователя как родителя
        await conn.execute(
            "INSERT INTO family_members (family_id, user_id, role) VALUES ($1, $2, 'parent')",
            family_id, user_id
        )
        
        return family_id


async def get_family_id(user_id: int) -> int:
    """Получить ID семьи пользователя"""
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT family_id FROM family_members WHERE user_id=$1",
            user_id
        )
        return row['family_id'] if row else None


async def is_parent(user_id: int) -> bool:
    """Проверить, является ли пользователь родителем"""
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT role FROM family_members WHERE user_id=$1",
            user_id
        )
        return row and row['role'] == 'parent'


async def close_db():
    """Закрыть пул соединений"""
    global _pool
    if _pool:
        await _pool.close()
