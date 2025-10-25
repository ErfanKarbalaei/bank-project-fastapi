from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.auth_schema import UserCreate, Token, UserOut
# ✅ Import کردن get_db و get_current_user از deps.py
from app.api.v1.deps import get_db, get_current_user
from app.repositories.user_repo import UserRepository
from app.services.auth_services import AuthService
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
# ✅ Import کردن مدل User برای استفاده در Depends
from app.db.models.user_model import User

router = APIRouter(tags=["auth"], prefix="/api/v1/auth")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


@router.post("/register", response_model=UserOut, status_code=201)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user_repo = UserRepository(db)
    auth_svc = AuthService(user_repo)
    try:
        created = await auth_svc.register_user(db, user_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return created


@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user_repo = UserRepository(db)
    auth_svc = AuthService(user_repo)
    user = await auth_svc.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect credentials")

    # ✅ بررسی فعال بودن حساب کاربری
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive. Please contact support."
        )

    token = auth_svc.create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer"}


# ✅ مسیر /me بازنویسی شده است:
@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """
    اطلاعات کاربر فعلی را برمی‌گرداند.
    اعتبارسنجی توکن به طور کامل توسط get_current_user انجام می‌شود.
    """
    # اگر get_current_user موفق شود، شیء کاربر در current_user قرار دارد.
    return current_user
