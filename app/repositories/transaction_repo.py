from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select as future_select
from sqlalchemy.orm import selectinload
from app.db.models.card_model import Card
from app.db.models.transaction_model import Transaction


class TransactionRepository:
    """
    مسئولیت تعامل مستقیم با جداول Transaction و Card (برای عملیات‌های تراکنشی)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_card_by_number_for_update(self, card_number: str) -> Card | None:
        """واکشی یک کارت با شماره و اعمال قفل FOR UPDATE"""
        q = (
            select(Card)
            .where(Card.card_number == card_number)
            .with_for_update(nowait=False, of=Card)  # اعمال قفل
        )
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    async def get_cards_by_id_for_update(self, id1: int, id2: int) -> tuple[Card, Card]:
        """
        واکشی دو کارت بر اساس ID و قفل کردن آن‌ها (ترتیب IDها برای جلوگیری از Deadlock مهم است).
        """
        # اطمینان از ترتیب واکشی برای جلوگیری از Deadlock
        ids = sorted([id1, id2])

        q = (
            select(Card)
            .where(Card.id.in_(ids))
            .with_for_update(nowait=False, of=Card)  # اعمال قفل
            .order_by(Card.id)
        )
        res = await self.db.execute(q)
        locked_cards = res.scalars().all()

        if len(locked_cards) != 2:
            raise ValueError("Could not lock both cards during transfer")

        # برگرداندن به ترتیب اولیه (source, destination)
        card_map = {c.id: c for c in locked_cards}

        return card_map[id1], card_map[id2]

    async def recent_for_user(self, user_id: int, limit: int = 10):
        """
        واکشی تراکنش‌های اخیر که کاربر در آن‌ها مبدأ یا مقصد بوده است.
        از selectinload برای واکشی joinهای مورد نیاز در یک کوئری استفاده می‌شود.
        """
        q = (
            select(Transaction)
            .options(selectinload(Transaction.source_card), selectinload(Transaction.dest_card))
            .where(
                (Transaction.source_card.has(user_id=user_id)) |
                (Transaction.dest_card.has(user_id=user_id))
            )
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(q)
        return res.scalars().all()


    async def fee_sum(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
                      tx_id: Optional[int] = None) -> Decimal:
        """
        محاسبه جمع کارمزدهای تراکنش‌های موفق با فیلترهای بازه زمانی و آیدی تراکنش (نیازمندی 7).
        """
        # فقط کارمزدهای مربوط به تراکنش‌های موفق را جمع می‌زنیم
        conditions = [Transaction.status == "SUCCESS"]

        if tx_id is not None:
            # فیلتر آیدی تراکنش
            conditions.append(Transaction.id == tx_id)

        if date_from:
            # فیلتر از تاریخ شروع (شامل)
            conditions.append(Transaction.created_at >= date_from)

        if date_to:
            # فیلتر تا تاریخ پایان (ناشامل)
            conditions.append(Transaction.created_at <= date_to)

        # func.coalesce برای اطمینان از برگشت 0 به جای None در صورت عدم وجود رکورد
        q = select(func.coalesce(func.sum(Transaction.fee), 0)).where(and_(*conditions))

        res = await self.db.execute(q)
        # اطمینان از خروجی Decimal
        return Decimal(res.scalar_one() or 0)

