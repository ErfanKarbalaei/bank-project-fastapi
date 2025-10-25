# app/schemas/transaction_schema.py

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, constr, condecimal

# نوع سفارشی برای تضمین مثبت بودن و حداکثر دو رقم اعشار
PositiveDecimal = condecimal(gt=0, decimal_places=2)


class TransferIn(BaseModel):
    """مدل ورودی برای انتقال وجه بین کارت‌ها."""
    source_card: constr(min_length=16, max_length=16) = Field(..., description="شماره کارت مبدأ")
    dest_card: constr(min_length=16, max_length=16) = Field(..., description="شماره کارت مقصد")
    amount: PositiveDecimal = Field(..., description="مبلغ انتقال (تومان)")
    description: Optional[str] = Field(None, description="توضیحات تراکنش")


class WithdrawIn(BaseModel):
    """مدل ورودی برای برداشت وجه از کارت."""
    card_number: constr(min_length=16, max_length=16) = Field(..., description="شماره کارت برای برداشت")
    amount: PositiveDecimal = Field(..., description="مبلغ برداشت (تومان)")
    description: Optional[str] = Field(None, description="توضیحات تراکنش")


class TransactionOut(BaseModel):
    """مدل خروجی برای نمایش جزئیات تراکنش."""
    id: int
    source_card_id: Optional[int]
    dest_card_id: Optional[int]
    amount: Decimal
    fee: Decimal
    status: str
    description: Optional[str]
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class RevenueFilters(BaseModel):
    """مدل فیلترهای ورودی برای API درآمد (query params)."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    transaction_id: Optional[int] = None

    model_config = {
        "from_attributes": True
    }


class TotalRevenueResponse(BaseModel):
    """مدل خروجی API برای نمایش مجموع درآمد از کارمزدها."""
    total_revenue: Decimal

    model_config = {
        "from_attributes": True,
        "json_encoders": {Decimal: lambda v: float(v)}
    }
