from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import async_session
from app.repositories.user_repo import UserRepository
from app.schemas.auth_schema import TokenPayload
from app.db.models.user_model import User  # 👈 اضافه کردن این import برای استفاده در auth.py

# ✅ اصلاح tokenUrl: آدرس باید مستقیماً به اِندپوینت تولید توکن اشاره کند.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


# این تابع نقطه متمرکز اعتبارسنجی امنیتی است و وظیفه دارد یا کاربر را برگرداند یا خطا دهد.
async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
) -> User:  # 👈 مشخص کردن نوع خروجی برای Type Hinting بهتر
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",  # 👈 پیام خطای تمیزتر
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        if payload is None:
            raise credentials_exception
        # بهتر است اعتبارسنجی TokenPayload اینجا انجام شود تا از دیکد شدن موفق اطمینان حاصل شود
        token_data = TokenPayload(**payload)
    except JWTError:
        raise credentials_exception

    user_repo = UserRepository(db)
    # token_data.sub معمولاً ID کاربر (Integer) است.
    user = await user_repo.get_by_id(int(token_data.sub))

    if user is None:
        raise credentials_exception

    # ⚠️ نکته: اگر کاربر is_active=False باشد، باید اینجا خطا داده شود.
    # if not user.is_active:
    #     raise credentials_exception 

    return user