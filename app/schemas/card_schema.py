# app/schemas/card_schema.py

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel


class CardOut(BaseModel):
    """مدل داده‌ی خروجی کارت برای پاسخ API."""
    id: int
    card_number: str
    balance: Decimal
    is_active: bool
    user_id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
