import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS families (
            id SERIAL PRIMARY KEY
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id BIGINT PRIMARY KEY,
            name TEXT,
            family_id INTEGER REFERENCES families(id)
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            family_id INTEGER REFERENCES families(id),
            text TEXT,
            is_done BOOLEAN DEFAULT FALSE
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS shopping (
            id SERIAL PRIMARY KEY,
            family_id INTEGER REFERENCES families(id),
            text TEXT,
            is_bought BOOLEAN DEFAULT FALSE
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS invites (
            code TEXT PRIMARY KEY,
            family_id INTEGER REFERENCES families(id)
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS pinned_messages (
            family_id INTEGER,
            chat_id BIGINT,
            message_type TEXT,
            message_id BIGINT,
            PRIMARY KEY (family_id, message_type)
        );
        """)
