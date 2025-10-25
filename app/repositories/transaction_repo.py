from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.card_model import Card
from app.db.models.transaction_model import Transaction


class TransactionRepository:
    """Repository برای عملیات پایگاه داده مرتبط با تراکنش‌ها و کارت‌ها."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------ Card Locking ------------------ #

    async def get_card_by_number_for_update(self, card_number: str) -> Card | None:
        """واکشی کارت با شماره کارت و قفل‌گذاری (SELECT ... FOR UPDATE)."""
        q = (
            select(Card)
            .where(Card.card_number == card_number)
            .with_for_update(nowait=False, of=Card)
        )
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    async def get_cards_by_id_for_update(self, id1: int, id2: int) -> tuple[Card, Card]:
        """
        واکشی و قفل دو کارت به‌صورت ترتیبی برای جلوگیری از Deadlock.
        ترتیب IDها حفظ می‌شود تا قفل‌ها هم‌زمان با ترتیب یکسان اعمال شوند.
        """
        ids = sorted([id1, id2])

        q = (
            select(Card)
            .where(Card.id.in_(ids))
            .with_for_update(nowait=False, of=Card)
            .order_by(Card.id)
        )
        res = await self.db.execute(q)
        locked_cards = res.scalars().all()

        if len(locked_cards) != 2:
            raise ValueError("Could not lock both cards during transfer.")

        card_map = {c.id: c for c in locked_cards}
        return card_map[id1], card_map[id2]

    # ------------------ Transaction Queries ------------------ #

    async def recent_for_user(self, user_id: int, limit: int = 10):
        """
        دریافت تراکنش‌های اخیر کاربر (چه مبدأ و چه مقصد).
        از selectinload برای واکشی کارت‌های مرتبط در همان کوئری استفاده می‌شود.
        """
        q = (
            select(Transaction)
            .options(
                selectinload(Transaction.source_card),
                selectinload(Transaction.dest_card),
            )
            .where(
                (Transaction.source_card.has(user_id=user_id))
                | (Transaction.dest_card.has(user_id=user_id))
            )
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(q)
        return res.scalars().all()

    # ------------------ Aggregation ------------------ #

    async def fee_sum(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tx_id: Optional[int] = None,
    ) -> Decimal:
        """
        محاسبه مجموع کارمزد تراکنش‌های موفق با فیلترهای اختیاری:
        - بازه زمانی (از / تا)
        - آیدی تراکنش خاص (tx_id)
        """
        conditions = [Transaction.status == "SUCCESS"]

        if tx_id is not None:
            conditions.append(Transaction.id == tx_id)
        if date_from:
            conditions.append(Transaction.created_at >= date_from)
        if date_to:
            conditions.append(Transaction.created_at <= date_to)

        q = select(func.coalesce(func.sum(Transaction.fee), 0)).where(and_(*conditions))
        res = await self.db.execute(q)

        return Decimal(res.scalar_one() or 0)
