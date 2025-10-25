from decimal import Decimal

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.card_model import Card
from app.db.models.transaction_model import Transaction


class CardRepository:
    """Repository برای انجام عملیات مرتبط با کارت‌ها."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------ Retrieval Methods ------------------ #

    async def get_by_id(self, card_id: int) -> Card | None:
        """دریافت کارت بر اساس ID."""
        q = select(Card).where(Card.id == card_id)
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    async def get_by_number(self, card_number: str) -> Card | None:
        """دریافت کارت بر اساس شماره کارت."""
        q = select(Card).where(Card.card_number == card_number)
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    async def list_by_user(self, user_id: int):
        """لیست کارت‌های متعلق به کاربر."""
        q = select(Card).where(Card.user_id == user_id)
        res = await self.db.execute(q)
        return res.scalars().all()

    # ------------------ Update / Lock Methods ------------------ #

    async def lock_by_id(self, card_id: int) -> Card | None:
        """دریافت کارت با قفل (SELECT ... FOR UPDATE) برای جلوگیری از race condition."""
        q = select(Card).where(Card.id == card_id).with_for_update()
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    async def change_balance(self, card: Card, amount: Decimal):
        """تغییر موجودی کارت (مقدار می‌تواند منفی باشد)."""
        new_balance = (card.balance or Decimal("0")) + amount
        stmt = (
            update(Card)
            .where(Card.id == card.id)
            .values(balance=new_balance)
            .returning(Card)
        )
        res = await self.db.execute(stmt)
        await self.db.flush()
        return res.fetchone()

    # ------------------ Aggregation Methods ------------------ #

    async def daily_total_for_card(self, card_id: int, date_from, date_to):
        """محاسبه مجموع تراکنش‌های روزانه برای یک کارت در بازه زمانی مشخص."""
        q = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.source_card_id == card_id)
            .where(Transaction.created_at >= date_from)
            .where(Transaction.created_at < date_to)
        )
        res = await self.db.execute(q)
        return res.scalar_one()
