import logging
import traceback
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from decimal import Decimal

from asyncpg import Connection

from app.api.v1.deps import get_db_connection, get_current_user
from app.services.transaction_service import (
    TransactionService,
    InsufficientFunds,
    BusinessRuleViolation,
    ForbiddenOperation
)
from app.schemas.transaction_schema import (
    TransferIn,
    WithdrawIn,
    TransactionOut,
    TotalRevenueResponse,
    RevenueFilters
)
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.card_repo import CardRepository

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])


def get_card_repo(conn: Connection = Depends(get_db_connection)) -> CardRepository:
    return CardRepository(conn)

def get_transaction_repo(conn: Connection = Depends(get_db_connection)) -> TransactionRepository:
    return TransactionRepository(conn)

def get_transaction_service(
        conn: Connection = Depends(get_db_connection),
        tx_repo: TransactionRepository = Depends(get_transaction_repo),
        card_repo: CardRepository = Depends(get_card_repo)
) -> TransactionService:
    return TransactionService(conn, tx_repo, card_repo)


@router.post("/withdraw", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def withdraw(
        body: WithdrawIn,
        current_user: dict = Depends(get_current_user),
        tx_service: TransactionService = Depends(get_transaction_service),
):
    try:
        tx = await tx_service.withdraw_from_card(
            body.card_number,
            body.amount,
            body.description,
            user_id=current_user['id']
        )
        return tx

    except (BusinessRuleViolation, InsufficientFunds, ForbiddenOperation) as e:
        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(e, ForbiddenOperation):
            status_code = status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail=str(e))

    except Exception as e:
        logging.error(f"Internal Server Error in withdraw: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An unknown error occurred.")

@router.post("/transfer", response_model=TransactionOut)
async def transfer(
        body: TransferIn,
        current_user: dict = Depends(get_current_user),
        tx_service: TransactionService = Depends(get_transaction_service),
):
    try:
        tx = await tx_service.transfer(
            body.source_card,
            body.dest_card,
            body.amount,
            body.description,
            user_id=current_user['id']
        )
        return tx

    except (BusinessRuleViolation, InsufficientFunds, ForbiddenOperation) as e:
        status_code = status.HTTP_400_BAD_REQUEST
        if isinstance(e, ForbiddenOperation):
            status_code = status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail=str(e))

    except Exception as e:
        logging.error(f"Internal Server Error in transfer: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An unknown error occurred.")

@router.get("/recent", response_model=list[TransactionOut])
async def recent_transactions(
        limit: int = Query(10, gt=0, le=50),
        tx_repo: TransactionRepository = Depends(get_transaction_repo),
        current_user: dict = Depends(get_current_user)
):
    try:
        txs = await tx_repo.recent_for_user(current_user['id'], limit=limit)
        return txs
    except Exception as e:
        logging.error(f"Error fetching recent transactions: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to fetch recent transactions.")

@router.get("/revenue", response_model=TotalRevenueResponse)
async def get_total_revenue(
        filters: RevenueFilters = Depends(),
        tx_repo: TransactionRepository = Depends(get_transaction_repo)
):
    try:
        total_income = await tx_repo.fee_sum(
            date_from=filters.start_date,
            date_to=filters.end_date,
            tx_id=filters.transaction_id
        )
        return TotalRevenueResponse(total_revenue=total_income)
    except Exception as e:
        logging.error(f"Error fetching revenue: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to fetch fee income report.")
