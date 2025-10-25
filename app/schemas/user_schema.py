# app/schemas/user_schema.py

from datetime import date
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """مدل پایه‌ی کاربر (shared fields)."""
    national_code: str
    full_name: str
    phone_number: str
    email: EmailStr
    birth_date: date | None = None
    is_active: bool = True


class UserCreate(UserBase):
    """مدل ورودی برای ایجاد کاربر جدید."""
    password: str


class UserOut(UserBase):
    """مدل خروجی برای نمایش اطلاعات کاربر."""
    id: int

    model_config = {
        "from_attributes": True
    }
