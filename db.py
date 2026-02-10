import asyncpg
from config import DATABASE_URL

db_pool: asyncpg.Pool | None = None


async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

    async with db_pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS families (
            id SERIAL PRIMARY KEY,
            title TEXT DEFAULT 'Наша семья'
        );

        CREATE TABLE IF NOT EXISTS family_members (
            user_id BIGINT PRIMARY KEY,
            family_id INTEGER REFERENCES families(id),
            role TEXT CHECK (role IN ('parent','child'))
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            family_id INTEGER REFERENCES families(id),
            text TEXT,
            done BOOLEAN DEFAULT FALSE
        );

        CREATE TABLE IF NOT EXISTS shopping (
            id SERIAL PRIMARY KEY,
            family_id INTEGER REFERENCES families(id),
            text TEXT,
            is_bought BOOLEAN DEFAULT FALSE
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id SERIAL PRIMARY KEY,
            family_id INTEGER,
            user_id BIGINT,
            action TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)


async def get_family_id(user_id: int) -> int | None:
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT family_id FROM family_members WHERE user_id=$1",
            user_id
        )
        return row["family_id"] if row else None


async def is_parent(user_id: int) -> bool:
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT role FROM family_members WHERE user_id=$1",
            user_id
        )
        return row and row["role"] == "parent"
