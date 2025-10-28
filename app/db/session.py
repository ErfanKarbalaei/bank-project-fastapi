import asyncpg
from asyncpg.pool import Pool
from asyncpg import Connection
from typing import AsyncGenerator
from app.core.config import settings

db_pool: Pool | None = None

async def get_pool() -> Pool:
    global db_pool
    if db_pool is None:
        await connect_db_pool()
    return db_pool

async def connect_db_pool():
    global db_pool
    if db_pool is None:
        try:
            db_pool = await asyncpg.create_pool(
                dsn=settings.asyncpg_url,
                min_size=5,
                max_size=20,
                timeout=30,
            )
            print("✅ AsyncPG Connection Pool created successfully.")
        except Exception as e:
            print(f"❌ Error connecting to database: {e}")
            raise

async def close_db_pool():
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None
        print("❌ AsyncPG Connection Pool closed.")

async def get_db_connection() -> AsyncGenerator[Connection, None]:
    if db_pool is None:
        raise Exception("Database pool is not initialized.")
    async with db_pool.acquire() as connection:
        yield connection
