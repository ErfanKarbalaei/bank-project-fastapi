from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from asyncpg import Connection

from app.schemas.auth_schema import UserCreate, Token, UserOut
from app.api.v1.deps import get_db_connection, get_current_user
from app.repositories.user_repo import UserRepository
from app.services.auth_services import AuthService

router = APIRouter(tags=["auth"], prefix="/api/v1/auth")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, conn: Connection = Depends(get_db_connection)):
    user_repo = UserRepository(conn)
    auth_svc = AuthService(user_repo)
    try:
        created = await auth_svc.register_user(user_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": str(e)})
    return created


@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(),
                conn: Connection = Depends(get_db_connection)):
    user_repo = UserRepository(conn)
    auth_svc = AuthService(user_repo)
    try:
        user = await auth_svc.authenticate(form_data.username, form_data.password)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail={"error": "Authentication failed"})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"error": "incorrect_credentials"})
    if not user.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"error": "user_inactive"})
    token = auth_svc.create_token_for_user(user)
    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: dict = Depends(get_current_user)):
    return current_user
