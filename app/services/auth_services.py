# app/services/auth_service.py
from datetime import timedelta
# ❌ حذف AsyncSession از type hint (به دلیل حذف آن از متدها)
from typing import Optional, Any

from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.repositories.user_repo import UserRepository
from app.schemas.auth_schema import UserCreate
from app.core.config import settings
from jose import JWTError
from app.core.exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
)


class AuthService:
    def __init__(self, user_repo: UserRepository):
        # user_repo اکنون از Connection asyncpg استفاده می کند
        self.user_repo = user_repo

        # ⚠️ حذف پارامتر session که در SQLAlchemy برای commit/rollback لازم بود

    # در asyncpg ما از Connection (که از get_db_connection می آید) استفاده می کنیم
    # و Repositoryها مستقیماً عملیات را انجام می دهند.
    async def register_user(self, user_in: UserCreate) -> dict:
        """ثبت نام کاربر جدید (با بررسی شماره تلفن تکراری)."""

        existing_phone = await self.user_repo.get_by_phone(user_in.phone_number)
        if existing_phone:
            raise UserAlreadyExistsException("phone number")

        # چک تکراری بودن کد ملی
        existing_national = await self.user_repo.get_by_national_code(user_in.national_code)
        if existing_national:
            raise UserAlreadyExistsException("national code")

        hashed_password = hash_password(user_in.password)

        user_data = {
            "national_code": user_in.national_code,
            "full_name": user_in.full_name,
            "phone_number": user_in.phone_number,
            "email": user_in.email,
            "hashed_password": hashed_password,
        }

        created_user_dict = await self.user_repo.create(user_in=user_data)
        return created_user_dict

    async def authenticate(self, phone_number: str, password: str) -> Optional[dict]:  # 👈 خروجی dict
        """اعتبارسنجی کاربر بر اساس شماره موبایل و رمز عبور."""
        # user اکنون یک دیکشنری است
        user = await self.user_repo.get_by_phone(phone_number)

        if not user:
            return None

        # ⚠️ دسترسی به 'hashed_password' در دیکشنری
        if not verify_password(password, user.get('hashed_password', '')):
            return None

        return user

    # ⚠️ user ورودی یک دیکشنری است
    def create_token_for_user(self, user: dict) -> str:
        """تولید Access Token برای کاربر."""
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        # ⚠️ استفاده از user['id'] برای subject
        token = create_access_token(
            subject=str(user['id']),
            expires_delta=access_token_expires
        )
        return token
