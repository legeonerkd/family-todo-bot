import asyncpg
from app.config import DATABASE_URL

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    print("✅ Database connected")

def get_pool():
    return pool
