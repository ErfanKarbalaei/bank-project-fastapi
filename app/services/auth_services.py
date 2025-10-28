from datetime import timedelta
from typing import Optional
from app.repositories.user_repo import UserRepository
from app.schemas.auth_schema import UserCreate
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.core.exceptions import UserAlreadyExistsException

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, user_in: UserCreate) -> dict:
        existing_phone = await self.user_repo.get_by_phone(user_in.phone_number)
        if existing_phone:
            raise UserAlreadyExistsException("phone number")
        existing_national = await self.user_repo.get_by_national_code(user_in.national_code)
        if existing_national:
            raise UserAlreadyExistsException("national code")

        hashed_password = hash_password(user_in.password)
        user_data = {
            "national_code": user_in.national_code,
            "full_name": user_in.full_name,
            "phone_number": user_in.phone_number,
            "email": user_in.email,
            "hashed_password": hashed_password,
        }
        return await self.user_repo.create(user_in=user_data)

    async def authenticate(self, phone_number: str, password: str) -> Optional[dict]:
        user = await self.user_repo.get_by_phone(phone_number)
        if not user:
            return None
        if not verify_password(password, user.get('hashed_password', '')):
            return None
        return user

    def create_token_for_user(self, user: dict) -> str:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(subject=str(user['id']), expires_delta=access_token_expires)
