from sqlalchemy import insert, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.transaction_model import Transaction

class TransactionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Transaction:
        stmt = insert(Transaction).values(**kwargs).returning(Transaction)
        res = await self.db.execute(stmt)
        created = res.fetchone()
        await self.db.flush()
        return created

    async def recent_for_user(self, user_id: int, limit: int = 10):
        # transactions where user is source or dest
        q = (
            select(Transaction)
            .where(
                (Transaction.source_card.has(user_id=user_id)) |
                (Transaction.dest_card.has(user_id=user_id))
            )
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(q)
        return res.scalars().all()

    async def fee_sum(self, date_from=None, date_to=None, tx_id=None):
        q = select(func.coalesce(func.sum(Transaction.fee), 0))
        if tx_id:
            q = q.where(Transaction.id == tx_id)
        if date_from:
            q = q.where(Transaction.created_at >= date_from)
        if date_to:
            q = q.where(Transaction.created_at < date_to)
        res = await self.db.execute(q)
        return res.scalar_one()
