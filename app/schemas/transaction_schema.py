from pydantic import BaseModel, constr, Field, condecimal
from decimal import Decimal
from datetime import datetime
from typing import Optional

PositiveDecimal = condecimal(gt=0, decimal_places=2)

class TransferIn(BaseModel):
    source_card: constr(min_length=16, max_length=16) = Field(...)
    dest_card: constr(min_length=16, max_length=16) = Field(...)
    amount: PositiveDecimal = Field(...)
    description: Optional[str] = None

class WithdrawIn(BaseModel):
    card_number: constr(min_length=16, max_length=16) = Field(...)
    amount: PositiveDecimal = Field(...)
    description: Optional[str] = None

class TransactionOut(BaseModel):
    id: int
    source_card_id: Optional[int]
    dest_card_id: Optional[int]
    amount: Decimal
    fee: Decimal
    status: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class RevenueFilters(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    transaction_id: Optional[int] = None

    class Config:
        from_attributes = True

class TotalRevenueResponse(BaseModel):
    total_revenue: Decimal

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)
        }
