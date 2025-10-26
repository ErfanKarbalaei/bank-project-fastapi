from typing import AsyncGenerator, Optional, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from asyncpg import Connection  # ✅ استفاده از asyncpg.Connection

from app.core.security import decode_access_token
# ❌ حذف ایمپورت قدیمی get_db
# ✅ ایمپورت تابع جدید: get_db_connection
from app.db.session import get_db_connection
from app.repositories.user_repo import UserRepository
from app.schemas.auth_schema import TokenPayload
from app.db.models.user_model import User  # برای حفظ سازگاری type hint (خروجی نهایی دیکشنری است)

# ✅ اصلاح tokenUrl: آدرس باید مستقیماً به اِندپوینت تولید توکن اشاره کند.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# این تابع نقطه متمرکز اعتبارسنجی امنیتی است و وظیفه دارد یا کاربر را برگرداند یا خطا دهد.
async def get_current_user(
        token: str = Depends(oauth2_scheme),
        # ⚠️ استفاده از تابع جدید get_db_connection
        conn: Connection = Depends(get_db_connection),
) -> dict:  # 👈 نوع خروجی dict است (بر اساس خروجی asyncpg Repository)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        if payload is None:
            raise credentials_exception
        token_data = TokenPayload(**payload)
    except JWTError:
        raise credentials_exception

    # ⚠️ ساخت UserRepository با Connection
    # فرض می‌کنیم UserRepository به‌روز شده و Connection دریافت می‌کند
    user_repo = UserRepository(conn)

    # user_repo اکنون دیکشنری برمی‌گرداند
    user_data = await user_repo.get_by_id(int(token_data.sub))

    if user_data is None:
        raise credentials_exception

    return user_data
