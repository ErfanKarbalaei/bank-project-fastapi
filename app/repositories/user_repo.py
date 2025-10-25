# app/repositories/user_repo.py

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import user_model


class UserRepository:
    """Repository برای مدیریت عملیات پایگاه داده مربوط به کاربران."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------ Retrieval Methods ------------------ #

    async def get_by_phone(self, phone_number: str) -> Optional[user_model.User]:
        """دریافت کاربر بر اساس شماره تلفن."""
        q = select(user_model.User).where(user_model.User.phone_number == phone_number)
        res = await self.session.execute(q)
        return res.scalars().first()

    async def get_by_id(self, user_id: int) -> Optional[user_model.User]:
        """دریافت کاربر بر اساس شناسه (ID)."""
        q = select(user_model.User).where(user_model.User.id == user_id)
        res = await self.session.execute(q)
        return res.scalars().first()

    # ------------------ Creation ------------------ #

    async def create(self, *, user_in) -> user_model.User:
        """ایجاد کاربر جدید در پایگاه داده."""
        user = user_model.User(
            national_code=user_in.national_code,
            full_name=user_in.full_name,
            phone_number=user_in.phone_number,
            email=user_in.email,
            hashed_password=user_in.hashed_password,
        )
        self.session.add(user)
        await self.session.flush()  # برای دریافت ID
        await self.session.commit()
        await self.session.refresh(user)
        return user
