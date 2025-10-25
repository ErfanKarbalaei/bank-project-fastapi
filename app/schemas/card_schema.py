from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

class CardOut(BaseModel):
    id: int
    card_number: str
    balance: Decimal
    is_active: bool
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
