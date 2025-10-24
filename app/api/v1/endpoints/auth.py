# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.auth_schema import UserCreate, UserLogin, Token, UserOut
from app.api.v1.deps import get_db
from app.repositories.user_repo import UserRepository
from app.services.auth_services import AuthService
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import timedelta

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
    token = auth_svc.create_token_for_user(user)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def read_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    from app.core.security import decode_access_token
    payload = None
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    user_id = int(payload.get("sub"))
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
