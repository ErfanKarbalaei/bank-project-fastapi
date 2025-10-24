from pydantic import BaseModel, EmailStr
from datetime import date

class UserBase(BaseModel):
    national_code: str
    full_name: str
    phone_number: str
    email: EmailStr
    birth_date: date | None = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True  # معادل orm_mode=True در Pydantic v2
