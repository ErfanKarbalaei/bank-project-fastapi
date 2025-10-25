# transaction:endpoint

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from decimal import Decimal, InvalidOperation
from asyncpg import Connection

# ❌ خطای شما اینجاست. get_db حذف شده و باید با get_db_connection جایگزین شود.
# from app.api.v1.deps import get_db, get_current_user
from app.api.v1.deps import get_db_connection, get_current_user # ✅ اصلاح شده

# ایمپورت کردن کلاس‌های خطا
from app.services.transaction_service import (
    TransactionService,
    InsufficientFunds,
    BusinessRuleViolation,
    ForbiddenOperation
)
# اصلاح ایمپورت‌ها:
from app.schemas.transaction_schema import (
    TransferIn,
    WithdrawIn,
    TransactionOut,
    TotalRevenueResponse,
    RevenueFilters
)
# ⚠️ مدل‌های DB را از endpoint حذف می‌کنیم و فقط User را برای احراز هویت نگه می‌داریم
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.card_repo import CardRepository


router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


# 1. Dependency برای Card Repository
# ⚠️ تغییر نام تابع تزریق
def get_card_repo(conn: Connection = Depends(get_db_connection)) -> CardRepository:
    """Dependency برای ایجاد و تزریق Card Repository با Connection."""
    return CardRepository(conn)


# 2. Dependency برای Transaction Repository
# ⚠️ تغییر نام تابع تزریق
def get_transaction_repo(conn: Connection = Depends(get_db_connection)) -> TransactionRepository:
    """Dependency برای ایجاد و تزریق Transaction Repository با Connection."""
    return TransactionRepository(conn)


# 3. Dependency برای Service
# ⚠️ تغییر نام تابع تزریق
def get_transaction_service(
        conn: Connection = Depends(get_db_connection),
        tx_repo: TransactionRepository = Depends(get_transaction_repo),
        card_repo: CardRepository = Depends(get_card_repo)
) -> TransactionService:
    """Dependency برای ایجاد و تزریق Service با Connection و Repositories."""
    # ⚠️ تغییرات در ورودی کلاس
    return TransactionService(conn, tx_repo, card_repo)


@router.post("/withdraw", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
# ⚠️ user_id اکنون یک دیکشنری است
async def withdraw(
        body: WithdrawIn,
        current_user: dict = Depends(get_current_user),
        tx_service: TransactionService = Depends(get_transaction_service),
):
    """انجام عملیات برداشت وجه از کارت کاربر."""
    try:
        # فراخوانی سرویس: متد Service اکنون commit یا rollback را به صورت داخلی انجام می‌دهد.
        tx = await tx_service.withdraw_from_card(
            body.card_number,
            body.amount,
            body.description,
            # ⚠️ دسترسی به ID از دیکشنری
            user_id=current_user['id']
        )
        return tx

    except (BusinessRuleViolation, InsufficientFunds, ForbiddenOperation) as e:
        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(e, ForbiddenOperation):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(e, InsufficientFunds):
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(status_code=status_code, detail=str(e))

    except Exception as e:
        print(f"Internal Server Error in withdraw: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unknown error occurred.")


@router.post("/transfer", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
# ⚠️ user_id اکنون یک دیکشنری است
async def transfer(
        body: TransferIn,
        current_user: dict = Depends(get_current_user),
        tx_service: TransactionService = Depends(get_transaction_service),
):
    """انجام عملیات انتقال وجه بین دو کارت."""
    try:
        tx = await tx_service.transfer(
            body.source_card,
            body.dest_card,
            body.amount,
            body.description,
            # ⚠️ دسترسی به ID از دیکشنری
            user_id=current_user['id']
        )
        return tx

    except (BusinessRuleViolation, InsufficientFunds, ForbiddenOperation) as e:
        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(e, ForbiddenOperation):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(e, InsufficientFunds):
            status_code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(status_code=status_code, detail=str(e))

    except Exception as e:
        print(f"Internal Server Error in transfer: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unknown error occurred.")


@router.get("/recent", response_model=list[TransactionOut])
# ⚠️ user_id اکنون یک دیکشنری است
async def recent_transactions(
        limit: int = Query(10, gt=0, le=50),
        tx_repo: TransactionRepository = Depends(get_transaction_repo),
        current_user: dict = Depends(get_current_user)
):
    """دریافت تراکنش‌های اخیر کاربر (بدون تغییر)."""
    # ⚠️ دسترسی به ID از دیکشنری
    txs = await tx_repo.recent_for_user(current_user['id'], limit=limit)
    return txs


# --- مسیر گزارش‌گیری ---

@router.get(
    "/revenue",
    response_model=TotalRevenueResponse,
    summary="دریافت مجموع درآمد از کارمزدها"
)
async def get_total_revenue(
        filters: RevenueFilters = Depends(),
        tx_repo: TransactionRepository = Depends(get_transaction_repo)
):
    """
    دریافت درآمد کل کارمزدها با قابلیت فیلترینگ (بدون تغییر).
    """
    try:
        total_income = await tx_repo.fee_sum(
            date_from=filters.start_date,
            date_to=filters.end_date,
            tx_id=filters.transaction_id
        )

        return TotalRevenueResponse(total_revenue=total_income)

    except Exception as e:
        print(f"Error fetching revenue: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to fetch fee income report.")
