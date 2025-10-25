from fastapi import APIRouter, Depends, HTTPException, status
from decimal import Decimal, InvalidOperation
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.deps import get_db, get_current_user
from app.services.transaction_service import TransactionService, InsufficientFunds, BusinessRuleViolation
from app.schemas.transaction_schema import TransferIn, WithdrawIn, TransactionOut
from app.db.models.user_model import User

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])

@router.post("/withdraw", response_model=TransactionOut)
async def withdraw(body: WithdrawIn, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = TransactionService(db)
    try:
        tx = await svc.withdraw_from_card(body.card_number, body.amount, body.description, user_id=current_user.id)
        await db.commit()  # ✅ اضافه کن
        return tx
    except (BusinessRuleViolation, InsufficientFunds) as e:
        await db.rollback()  # ✅ rollback در خطا

        raise HTTPException(status_code=400, detail=str(e))
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientFunds as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.post("/transfer", response_model=TransactionOut)
async def transfer(body: TransferIn, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    svc = TransactionService(db)
    try:
        tx = await svc.transfer(body.source_card, body.dest_card, body.amount, body.description, user_id=current_user.id)
        await db.commit()
        return tx
    except BusinessRuleViolation as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientFunds as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.get("/recent", response_model=list[TransactionOut])
async def recent_transactions(limit: int = 10, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.repositories.transaction_repo import TransactionRepository
    tx_repo = TransactionRepository(db)
    txs = await tx_repo.recent_for_user(current_user.id, limit=limit)
    return txs
