import asyncpg
from asyncpg.pool import Pool
from asyncpg import Connection
from typing import AsyncGenerator

# ⚠️ ایمپورت‌های SQLAlchemy را حذف می‌کنیم.
# from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
# from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# 1. Base برای Alembic (بدون تغییر)
# اگرچه این مدل‌ها دیگر برای Repository استفاده نمی‌شوند،
# Alembic برای ردیابی ساختار دیتابیس به Base نیاز دارد.
# Base = declarative_base() # اگر این خط در فایل دیگری نیست، باید از همان Base استفاده کنید.
# فرض می‌کنیم Base در جای دیگری تعریف و ایمپورت شده است.

# 2. متغیر گلوبال برای نگهداری Pool اتصال
db_pool: asyncpg.Pool| None = None

async def get_pool() -> asyncpg.Pool:
    global db_pool
    if db_pool is None:
        await connect_db_pool()
    return db_pool

async def connect_db_pool():
    """ایجاد Connection Pool توسط asyncpg در زمان راه‌اندازی برنامه."""
    global db_pool
    if db_pool is None:
        try:
            # استفاده از asyncpg_url جدید
            db_pool = await asyncpg.create_pool(
                dsn=settings.asyncpg_url,
                min_size=5,  # حداقل تعداد اتصالات
                max_size=20, # حداکثر تعداد اتصالات
                timeout=30,  # مدت زمان انتظار برای گرفتن اتصال
                # سایر تنظیمات بهینه سازی
            )
            print("✅ AsyncPG Connection Pool created successfully.")
        except Exception as e:
            print(f"❌ Error connecting to database: {e}")
            raise


async def close_db_pool():
    """بستن Connection Pool در زمان خاموش شدن برنامه."""
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None
        print("❌ AsyncPG Connection Pool closed.")


# 3. Dependency Injection برای FastAPI
async def get_db_connection() -> AsyncGenerator[Connection, None]:
    """
    Dependency Injection که یک اتصال (Connection) را از Pool می‌گیرد
    و پس از پایان درخواست به Pool بازمی‌گرداند.
    """
    if db_pool is None:
        raise Exception("Database pool is not initialized.")

    # استفاده از async with pool.acquire()
    async with db_pool.acquire() as connection:
        # ⚠️ Connection مستقیماً در اختیار Repository قرار می‌گیرد
        yield connection