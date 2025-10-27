# app/repositories/user_repo.py

from typing import Optional
import asyncpg
from asyncpg import Connection # ایمپورت Connection

# ⚠️ دیگر نیازی به ایمپورت‌های SQLAlchemy نیست
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.db.models import user_model

class UserRepository:
    """Repository برای مدیریت عملیات پایگاه داده مربوط به کاربران."""

    # ⚠️ تغییر type hint
    def __init__(self, conn: Connection):
        self.conn = conn

    # ------------------ Retrieval Methods ------------------ #

    async def get_by_phone(self, phone_number: str) -> Optional[dict]: # تغییر نوع بازگشتی به dict
        """دریافت کاربر بر اساس شماره تلفن (با کوئری خام)."""
        sql = "SELECT * FROM users WHERE phone_number = $1;"
        record = await self.conn.fetchrow(sql, phone_number)
        return dict(record) if record else None

    async def get_by_id(self, user_id: int) -> Optional[dict]: # تغییر نوع بازگشتی به dict
        """دریافت کاربر بر اساس شناسه (ID) (با کوئری خام)."""
        sql = "SELECT * FROM users WHERE id = $1;"
        record = await self.conn.fetchrow(sql, user_id)
        return dict(record) if record else None

    async def get_by_national_code(self, national_code: str):
        sql = "SELECT * FROM users WHERE national_code = $1"
        return await self.conn.fetchrow(sql, national_code)
    # ------------------ Creation ------------------ #

    async def create(self, user_in: dict) -> dict:
        sql = """
            INSERT INTO users (national_code, full_name, phone_number, email, hashed_password, is_active)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *;
        """
        record = await self.conn.fetchrow(
            sql,
            user_in["national_code"],
            user_in["full_name"],
            user_in["phone_number"],
            user_in["email"],
            user_in["hashed_password"],
            True
        )
        return dict(record)
