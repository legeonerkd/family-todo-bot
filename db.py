import asyncpg
from config import DATABASE_URL

db_pool = None

async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)

def get_pool():
    return db_pool

