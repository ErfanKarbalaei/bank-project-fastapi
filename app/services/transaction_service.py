from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from app.db.models.card_model import Card
from app.db.models.transaction_model import Transaction
from app.repositories.card_repo import CardRepository
from app.repositories.transaction_repo import TransactionRepository

MIN_TX = Decimal("1000")
MAX_TX = Decimal("50000000")
FEE_RATE = Decimal("0.10")
FEE_CAP = Decimal("100000")
CARD_DAILY_CAP = Decimal("50000000")

class InsufficientFunds(Exception): pass
class BusinessRuleViolation(Exception): pass

class TransactionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.card_repo = CardRepository(db)
        self.tx_repo = TransactionRepository(db)

    def calc_fee(self, amount: Decimal) -> Decimal:
        fee = (amount * FEE_RATE).quantize(Decimal("1."), rounding=ROUND_DOWN)
        return min(fee, FEE_CAP)

    async def _daily_total_for_card(self, card_id: int, start, end) -> Decimal:
        q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.source_card_id == card_id,
            Transaction.created_at >= start,
            Transaction.created_at < end,
            Transaction.status == "SUCCESS"
        )
        res = await self.db.execute(q)
        return Decimal(res.scalar_one() or 0)

    async def withdraw_from_card(self, card_number: str, amount, description: str | None = None, user_id: int | None = None):
        amount = Decimal(str(amount))
        if amount < MIN_TX or amount > MAX_TX:
            raise BusinessRuleViolation("Amount out of allowed range")

        # تمام عملیات داخل یک تراکنش DB اجرا می‌شود
        async with self.db.begin_nested():
            # lock card row FOR UPDATE
            q = select(Card).where(Card.card_number == card_number).with_for_update()
            res = await self.db.execute(q)
            card = res.scalar_one_or_none()
            if card is None:
                raise BusinessRuleViolation("Card not found")
            if not card.is_active:
                raise BusinessRuleViolation("Card not active")

            # check daily cap
            now = datetime.now(timezone.utc)
            start = datetime.combine(now.date(), datetime.min.time()).replace(tzinfo=timezone.utc)
            end = start + timedelta(days=1)
            daily_total = await self._daily_total_for_card(card.id, start, end)
            if (daily_total + amount) > CARD_DAILY_CAP:
                raise BusinessRuleViolation("Card daily limit exceeded")

            fee = self.calc_fee(amount)
            total_debit = amount + fee
            if Decimal(card.balance or 0) < total_debit:
                raise InsufficientFunds("Not enough balance to cover amount and fee")

            # insert transaction
            ins = Transaction(
                source_card_id=card.id,
                dest_card_id=None,
                amount=amount,
                fee=fee,
                status="SUCCESS",
                description=description
            )
            self.db.add(ins)
            # update balance (use update statement to avoid stale attr issues)
            await self.db.execute(
                update(Card)
                .where(Card.id == card.id)
                .values(balance=(Card.balance - total_debit))
            )
            # flush to get id if needed
            await self.db.flush()
            return ins  # orm object (from_attributes / orm_mode will serialize)

    async def transfer(self, source_card_number: str, dest_card_number: str, amount, description: str | None = None, user_id: int | None = None):
        amount = Decimal(str(amount))
        if amount < MIN_TX or amount > MAX_TX:
            raise BusinessRuleViolation("Amount out of allowed range")

        async with self.db.begin_nested():
            # Load both and lock in deterministic order to avoid deadlock
            q_src = select(Card).where(Card.card_number == source_card_number)
            q_dst = select(Card).where(Card.card_number == dest_card_number)

            res_src = await self.db.execute(q_src)
            src = res_src.scalar_one_or_none()
            res_dst = await self.db.execute(q_dst)
            dst = res_dst.scalar_one_or_none()

            if not src or not dst:
                raise BusinessRuleViolation("Source or destination card not found")

            # lock rows in id order
            first_id, second_id = (src.id, dst.id) if src.id < dst.id else (dst.id, src.id)
            q1 = select(Card).where(Card.id == first_id).with_for_update()
            q2 = select(Card).where(Card.id == second_id).with_for_update()
            r1 = await self.db.execute(q1); row1 = r1.scalar_one()
            r2 = await self.db.execute(q2); row2 = r2.scalar_one()
            locked_src = row1 if row1.id == src.id else row2
            locked_dst = row2 if row2.id == dst.id else row1

            if not locked_src.is_active or not locked_dst.is_active:
                raise BusinessRuleViolation("One of cards is not active")

            # daily cap check on source
            now = datetime.now(timezone.utc)
            start = datetime.combine(now.date(), datetime.min.time()).replace(tzinfo=timezone.utc)
            end = start + timedelta(days=1)
            daily_total = await self._daily_total_for_card(locked_src.id, start, end)
            if (daily_total + amount) > CARD_DAILY_CAP:
                raise BusinessRuleViolation("Card daily limit exceeded")

            fee = self.calc_fee(amount)
            total_debit = amount + fee
            if Decimal(locked_src.balance or 0) < total_debit:
                raise InsufficientFunds("Not enough balance to cover amount and fee")

            # create transaction
            ins = Transaction(
                source_card_id=locked_src.id,
                dest_card_id=locked_dst.id,
                amount=amount,
                fee=fee,
                status="SUCCESS",
                description=description
            )
            self.db.add(ins)

            # update balances
            await self.db.execute(
                update(Card)
                .where(Card.id == locked_src.id)
                .values(balance=(Card.balance - total_debit))
            )
            await self.db.execute(
                update(Card)
                .where(Card.id == locked_dst.id)
                .values(balance=(Card.balance + amount))
            )

            await self.db.flush()
            return ins
