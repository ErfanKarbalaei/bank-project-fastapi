from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.db.models.card_model import Card
from app.db.models.transaction_model import Transaction

class CardRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, card_id: int) -> Card | None:
        q = select(Card).where(Card.id == card_id)
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    async def get_by_number(self, card_number: str) -> Card | None:
        q = select(Card).where(Card.card_number == card_number)
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    async def lock_by_id(self, card_id: int) -> Card | None:
        # SELECT ... FOR UPDATE to avoid race
        q = select(Card).where(Card.id == card_id).with_for_update()
        res = await self.db.execute(q)
        return res.scalar_one_or_none()

    async def change_balance(self, card: Card, amount: Decimal):
        # amount can be negative
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

    async def list_by_user(self, user_id: int):
        q = select(Card).where(Card.user_id == user_id)
        res = await self.db.execute(q)
        return res.scalars().all()

    async def daily_total_for_card(self, card_id: int, date_from, date_to):
        q = (
            select(func.coalesce(func.sum(Transaction.amount), 0))
            .where(Transaction.source_card_id == card_id)
            .where(Transaction.created_at >= date_from)
            .where(Transaction.created_at < date_to)
        )
        res = await self.db.execute(q)
        return res.scalar_one()
