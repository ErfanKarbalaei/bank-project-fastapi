from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.auth_schema import UserCreate, Token, UserOut
# ✅ Import کردن get_db_connection و get_current_user از deps.py
from app.api.v1.deps import get_db_connection, get_current_user
from app.repositories.user_repo import UserRepository
from app.services.auth_services import AuthService
# ❌ حذف ایمپورت AsyncSession
from asyncpg import Connection  # ✅ استفاده از Connection برای DB Dependency
from fastapi.security import OAuth2PasswordRequestForm
# ❌ حذف ایمپورت مدل User، زیرا get_current_user دیکشنری برمی‌گرداند.
from typing import Dict, Any

# ⚠️ از آنجایی که get_current_user یک dict برمی‌گرداند،
# ما از dict برای type hint استفاده می‌کنیم تا Endpoints نشکنند.

router = APIRouter(tags=["auth"], prefix="/api/v1/auth")


@router.post("/register", response_model=UserOut, status_code=201)
# ⚠️ جایگزینی AsyncSession با Connection و get_db با get_db_connection
async def register(user_in: UserCreate, conn: Connection = Depends(get_db_connection)):
    user_repo = UserRepository(conn)
    auth_svc = AuthService(user_repo)
    try:
        # created اکنون یک دیکشنری است
        created = await auth_svc.register_user(user_in)
    except ValueError as e:
        # این خطا توسط user_repo یا auth_svc صادر می شود
        raise HTTPException(status_code=400, detail=str(e))

        # خروجی (created) یک دیکشنری است که مستقیماً به Pydantic Model (UserOut) مپ می شود.
    return created


@router.post("/token", response_model=Token)
# ⚠️ جایگزینی AsyncSession با Connection و get_db با get_db_connection
async def login(form_data: OAuth2PasswordRequestForm = Depends(), conn: Connection = Depends(get_db_connection)):
    user_repo = UserRepository(conn)
    auth_svc = AuthService(user_repo)
    # user اکنون یک دیکشنری است
    user = await auth_svc.authenticate(form_data.username, form_data.password)

    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials")

    # ✅ بررسی فعال بودن حساب کاربری
    # ⚠️ دسترسی به 'is_active' در دیکشنری
    if not user.get('is_active', False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive. Please contact support."
        )

    token = auth_svc.create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer"}


# ✅ مسیر /me بازنویسی شده است:
@router.get("/me", response_model=UserOut)
# ⚠️ get_current_user دیکشنری کاربر را برمی‌گرداند
async def read_current_user(current_user: dict = Depends(get_current_user)):
    # current_user یک دیکشنری است و به راحتی به UserOut مپ می‌شود
    return current_user
