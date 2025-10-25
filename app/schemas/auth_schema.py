# app/schemas/auth.py

from typing import Optional
from pydantic import BaseModel, Field, EmailStr


# -------------------- Token Schemas -------------------- #

class Token(BaseModel):
    """مدل خروجی توکن JWT."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """payload داخل توکن JWT (برای استخراج اطلاعات کاربر)."""
    sub: Optional[str] = None


# -------------------- User Schemas -------------------- #

class UserCreate(BaseModel):
    """مدل داده‌های ورودی برای ثبت‌نام کاربر جدید."""
    national_code: str = Field(
        ...,
        min_length=10,
        max_length=10,
        pattern=r"^[0-9]{10}$",
        description="کد ملی ۱۰ رقمی",
    )
    full_name: str
    phone_number: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    """مدل داده‌های ورودی برای ورود کاربر."""
    phone_number: str
    password: str


class UserOut(BaseModel):
    """مدل داده‌های خروجی کاربر (برای پاسخ API)."""
    id: int
    national_code: str
    full_name: str
    phone_number: str
    email: EmailStr
    is_active: bool

    model_config = {
        "from_attributes": True
    }
