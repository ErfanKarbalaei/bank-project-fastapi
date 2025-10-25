from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db, get_current_user
from app.repositories.user_repo import UserRepository
from app.services.auth_services import AuthService
from app.schemas.auth_schema import UserCreate, Token, UserOut
from app.db.models.user_model import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """ثبت‌نام کاربر جدید."""
    user_repo = UserRepository(db)
    auth_svc = AuthService(user_repo)

    try:
        created = await auth_svc.register_user(db, user_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return created


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """دریافت توکن دسترسی برای کاربر."""
    user_repo = UserRepository(db)
    auth_svc = AuthService(user_repo)

    user = await auth_svc.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive. Please contact support.",
        )

    token = auth_svc.create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """
    دریافت اطلاعات کاربر فعلی.
    اعتبارسنجی توکن به طور کامل توسط get_current_user انجام می‌شود.
    """
    return current_user
