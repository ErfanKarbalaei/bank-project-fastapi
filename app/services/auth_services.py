# app/services/auth_service.py
from datetime import timedelta
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.repositories.user_repo import UserRepository
from app.schemas.auth_schema import UserCreate
from app.core.config import settings
from jose import JWTError

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, session, user_in: UserCreate):
        # بررسی وجود شماره موبایل یا ملی
        exists = await self.user_repo.get_by_phone(user_in.phone_number)
        if exists:
            raise ValueError("phone already registered")

        # هش کردن پسورد
        user_data = user_in.dict()
        user_data['hashed_password'] = hash_password(user_data.pop('password'))
        # تبدیل به نوعی که user_repo.create می‌پذیرد
        class _UserIn:
            pass
        uobj = _UserIn()
        for k, v in user_data.items():
            setattr(uobj, k, v)
        return await self.user_repo.create(user_in=uobj)

    async def authenticate(self, phone_number: str, password: str):
        user = await self.user_repo.get_by_phone(phone_number)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def create_token_for_user(self, user):
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(subject=str(user.id), expires_delta=access_token_expires)
        return token

    def decode_token(self, token: str):
        try:
            payload = decode_access_token(token)
            return payload
        except JWTError:
            return None
