from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from decimal import Decimal, InvalidOperation
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.deps import get_db, get_current_user
# ایمپورت کردن کلاس‌های خطا
from app.services.transaction_service import (
    TransactionService,
    InsufficientFunds,
    BusinessRuleViolation,
    ForbiddenOperation
)
# اصلاح ایمپورت‌ها: حذف FeeIncomeOut و افزودن TotalRevenueResponse و RevenueFilters
from app.schemas.transaction_schema import (
    TransferIn,
    WithdrawIn,
    TransactionOut,
    TotalRevenueResponse,
    RevenueFilters
)
from app.db.models.user_model import User
from app.repositories.transaction_repo import TransactionRepository

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


# 1. Dependency برای Repository
def get_transaction_repo(db: AsyncSession = Depends(get_db)) -> TransactionRepository:
    """Dependency برای ایجاد و تزریق Repository."""
    return TransactionRepository(db)


# 2. Dependency برای Service
def get_transaction_service(
        db: AsyncSession = Depends(get_db),
        tx_repo: TransactionRepository = Depends(get_transaction_repo)
) -> TransactionService:
    """Dependency برای ایجاد و تزریق Service با Repository و Session."""
    return TransactionService(db, tx_repo)


@router.post("/withdraw", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def withdraw(
        body: WithdrawIn,
        current_user: User = Depends(get_current_user),
        tx_service: TransactionService = Depends(get_transaction_service),
        db: AsyncSession = Depends(get_db)  # ✅ تزریق مجدد DB برای مدیریت commit/rollback
):
    """انجام عملیات برداشت وجه از کارت کاربر."""
    try:
        # فراخوانی سرویس: این متد تغییرات را در session ایجاد می‌کند اما commit نمی‌کند.
        tx = await tx_service.withdraw_from_card(
            body.card_number,
            body.amount,
            body.description,
            user_id=current_user.id
        )
        # ✅ commit نهایی در لایه Endpoint
        await db.commit()
        return tx

    except (BusinessRuleViolation, InsufficientFunds, ForbiddenOperation) as e:
        # ✅ rollback در صورت بروز هر خطای منطقی/امنیتی
        await db.rollback()

        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(e, ForbiddenOperation):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(e, InsufficientFunds):
            # 409 Conflict نیز برای موجودی ناکافی رایج است، اما 400 نیز قابل قبول است.
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(status_code=status_code, detail=str(e))

    except Exception as e:
        # ✅ rollback برای هر خطای ناشناخته (مانند خطای پایگاه داده)
        await db.rollback()
        # بهتر است خطای اصلی در لاگ‌ها ثبت شود
        print(f"Internal Server Error in withdraw: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unknown error occurred.")


@router.post("/transfer", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def transfer(
        body: TransferIn,
        current_user: User = Depends(get_current_user),
        tx_service: TransactionService = Depends(get_transaction_service),
        db: AsyncSession = Depends(get_db)  # ✅ تزریق مجدد DB برای مدیریت commit/rollback
):
    """انجام عملیات انتقال وجه بین دو کارت."""
    try:
        tx = await tx_service.transfer(
            body.source_card,
            body.dest_card,
            body.amount,
            body.description,
            user_id=current_user.id
        )
        # ✅ commit نهایی در لایه Endpoint
        await db.commit()
        return tx

    except (BusinessRuleViolation, InsufficientFunds, ForbiddenOperation) as e:
        # ✅ rollback در صورت بروز هر خطای منطقی/امنیتی
        await db.rollback()

        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(e, ForbiddenOperation):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(e, InsufficientFunds):
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(status_code=status_code, detail=str(e))

    except Exception as e:
        # ✅ rollback برای هر خطای ناشناخته
        await db.rollback()
        print(f"Internal Server Error in transfer: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unknown error occurred.")


@router.get("/recent", response_model=list[TransactionOut])
async def recent_transactions(
        limit: int = Query(10, gt=0, le=50),
        tx_repo: TransactionRepository = Depends(get_transaction_repo),
        current_user: User = Depends(get_current_user)
):
    """دریافت تراکنش‌های اخیر کاربر."""
    # این متد فقط SELECT است و نیازی به commit/rollback ندارد.
    txs = await tx_repo.recent_for_user(current_user.id, limit=limit)
    return txs


# --- شروع تغییرات برای نیازمندی 7 ---

@router.get(
    "/revenue",  # تغییر مسیر برای وضوح بیشتر
    response_model=TotalRevenueResponse,  # اصلاح response_model
    summary="دریافت مجموع درآمد از کارمزدها"
)
async def get_total_revenue(
        # current_user: User = Depends(get_current_user), # احتمالا نیاز به احراز هویت ادمین دارد

        # استفاده از مدل RevenueFilters برای دریافت فیلترها به صورت یکجا
        filters: RevenueFilters = Depends(),

        # استفاده مستقیم از Repository چون منطق در آنجا آماده است
        tx_repo: TransactionRepository = Depends(get_transaction_repo)
):
    """
    دریافت درآمد کل کارمزدها با قابلیت فیلترینگ (نیازمندی 7).
    """
    try:
        # فراخوانی متد fee_sum از ریپازیتوری
        total_income = await tx_repo.fee_sum(
            date_from=filters.start_date,
            date_to=filters.end_date,
            tx_id=filters.transaction_id
        )

        # برگرداندن پاسخ مطابق با مدل TotalRevenueResponse
        return TotalRevenueResponse(total_revenue=total_income)

    except Exception as e:
        print(f"Error fetching revenue: {e}")  # لاگ کردن خطا
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to fetch fee income report.")
# --- پایان تغییرات ---

