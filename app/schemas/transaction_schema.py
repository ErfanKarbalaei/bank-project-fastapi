from pydantic import BaseModel, constr, Field, condecimal
from decimal import Decimal
from datetime import datetime
from typing import Optional

# نوع سفارشی برای تضمین مثبت بودن و حداکثر دو رقم اعشار
PositiveDecimal = condecimal(gt=0, decimal_places=2)


class TransferIn(BaseModel):
    source_card: constr(min_length=16, max_length=16) = Field(..., description="شماره کارت مبدأ")
    dest_card: constr(min_length=16, max_length=16) = Field(..., description="شماره کارت مقصد")
    amount: PositiveDecimal = Field(..., description="مبلغ انتقال (تومان)") # ✅ اعتبارسنجی
    description: Optional[str] = Field(None, description="توضیحات تراکنش")

class WithdrawIn(BaseModel):
    card_number: constr(min_length=16, max_length=16) = Field(..., description="شماره کارت برای برداشت")
    amount: PositiveDecimal = Field(..., description="مبلغ برداشت (تومان)") # ✅ اعتبارسنجی
    description: Optional[str] = Field(None, description="توضیحات تراکنش")

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
    """
    مدل Pydantic برای نگهداری فیلترهای ورودی API درآمد.
    این مدل مستقیماً توسط FastAPI به عنوان Dependency استفاده می‌شود
    تا پارامترهای کوئری (query parameters) را دریافت کند.
    """
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    transaction_id: Optional[int] = None  # <-- از uuid.UUID به int تغییر کرد

    class Config:
        # فعال کردن حالت orm_mode (که اکنون validate_assignment=True نامیده می‌شود)
        # اگرچه برای query params ضروری نیست، اما عادت خوبی است.
        from_attributes = True


class TotalRevenueResponse(BaseModel):
    """
    مدل Pydantic برای پاسخ API درآمد.
    """
    total_revenue: Decimal

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v)  # برای سازگاری بهتر با JSON
        }

