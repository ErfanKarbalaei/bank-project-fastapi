from pydantic import BaseModel, Field, EmailStr
from datetime import date

class UserBase(BaseModel):
    national_code: str = Field(..., pattern=r"^[0-9]{10}$")
    full_name: str
    phone_number: str = Field(..., pattern=r"^09[0-9]{9}$")
    email: EmailStr
    birth_date: date | None = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True
