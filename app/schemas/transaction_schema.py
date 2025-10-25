from pydantic import BaseModel, constr
from decimal import Decimal
from datetime import datetime

class TransferIn(BaseModel):
    source_card: constr(min_length=16, max_length=16)
    dest_card: constr(min_length=16, max_length=16)
    amount: Decimal
    description: str | None = None

class WithdrawIn(BaseModel):
    card_number: constr(min_length=16, max_length=16)
    amount: Decimal
    description: str | None = None

class TransactionOut(BaseModel):
    id: int
    source_card_id: int | None
    dest_card_id: int | None
    amount: Decimal
    fee: Decimal
    status: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True
