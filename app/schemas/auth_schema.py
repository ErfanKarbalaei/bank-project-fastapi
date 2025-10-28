from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None

class UserCreate(BaseModel):
    national_code: str = Field(..., min_length=10, max_length=10, pattern="^[0-9]{10}$")
    full_name: str
    phone_number: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    phone_number: str
    password: str

class UserOut(BaseModel):
    id: int
    national_code: str
    full_name: str
    phone_number: str
    email: EmailStr
    is_active: bool

    model_config = {
        "from_attributes": True
    }
