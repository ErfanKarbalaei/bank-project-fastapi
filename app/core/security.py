# app/core/security.py

import hashlib
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

# ------------------- Password & Token Config ------------------- #

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------- Password Hashing ------------------- #

def hash_password(password: str) -> str:
    """
    هش کردن رمز عبور با ترکیب SHA256 و bcrypt.
    ابتدا رمز به SHA256 تبدیل می‌شود تا طول آن استاندارد شود،
    سپس با bcrypt هش می‌گردد.
    """
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return pwd_context.hash(digest)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    بررسی تطابق رمز عبور خام با هش ذخیره‌شده.
    رمز خام ابتدا با SHA256 هش شده و سپس با bcrypt مقایسه می‌شود.
    """
    digest = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return pwd_context.verify(digest, hashed_password)


# ------------------- JWT Token Operations ------------------- #

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    تولید توکن JWT برای کاربر.
    پارامتر expires_delta مدت زمان انقضا را مشخص می‌کند (پیش‌فرض: مقدار از تنظیمات).
    """
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode = {"sub": str(subject), "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    دیکد کردن توکن JWT و بازگرداندن payload.
    اگر توکن نامعتبر یا منقضی باشد، jose.exceptions.JWTError برمی‌گرداند.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
