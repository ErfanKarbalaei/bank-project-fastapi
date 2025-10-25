from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update, func, literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from app.db.models.card_model import Card
from app.db.models.transaction_model import Transaction
from app.repositories.transaction_repo import TransactionRepository

# پارامترهای کسب‌وکار
MIN_TX = Decimal("1000")
MAX_TX = Decimal("50000000")
FEE_RATE = Decimal("0.10")  # کارمزد 0.1 درصد
FEE_CAP = Decimal("100000")  # سقف کارمزد 100 هزار تومان
CARD_DAILY_CAP = Decimal("50000000")  # سقف تراکنش روزانه 50 میلیون تومان


# کلاس‌های خطای سفارشی
class InsufficientFunds(Exception): pass


class BusinessRuleViolation(Exception): pass


class ForbiddenOperation(Exception): pass


class TransactionService:
    """
    مدیریت منطق تراکنش‌ها و اعتبارسنجی‌های کسب‌وکار.
    """

    def __init__(self, db: AsyncSession, tx_repo: TransactionRepository):
        self.db = db
        self.tx_repo = tx_repo

    def calc_fee(self, amount: Decimal) -> Decimal:
        """محاسبه کارمزد تراکنش با در نظر گرفتن سقف."""
        fee = (amount * FEE_RATE).quantize(Decimal("1."), rounding=ROUND_DOWN)
        return min(fee, FEE_CAP)

    async def _daily_total_for_card(self, card_id: int, start, end) -> Decimal:
        """محاسبه مجموع تراکنش‌های موفق روز جاری (به عنوان منبع)."""
        q = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.source_card_id == card_id,
            Transaction.created_at >= start,
            Transaction.created_at < end,
            Transaction.status == "SUCCESS"
        )
        res = await self.db.execute(q)
        return Decimal(res.scalar_one() or 0)

    async def withdraw_from_card(self, card_number: str, amount, description: str | None = None,
                                 user_id: int | None = None):
        """عملیات برداشت از کارت."""
        try:
            amount = Decimal(str(amount))
        except Exception:
            raise BusinessRuleViolation("Invalid amount format")

        if amount < MIN_TX or amount > MAX_TX:
            raise BusinessRuleViolation(f"Amount must be between {MIN_TX} and {MAX_TX} Tomans.")

        # 1. قفل کردن ردیف کارت با استفاده از Repository
        card = await self.tx_repo.get_card_by_number_for_update(card_number)

        if card is None:
            raise BusinessRuleViolation("Card not found")

        # 2. اعتبارسنجی مالکیت و وضعیت
        if card.user_id != user_id:
            raise ForbiddenOperation("Card does not belong to the current user.")

        if not card.is_active:
            raise BusinessRuleViolation("Card not active")

        # 3. بررسی سقف روزانه
        now = datetime.now(timezone.utc)
        start = datetime.combine(now.date(), datetime.min.time()).replace(tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        daily_total = await self._daily_total_for_card(card.id, start, end)
        if (daily_total + amount) > CARD_DAILY_CAP:
            raise BusinessRuleViolation("Card daily limit exceeded.")

        fee = self.calc_fee(amount)
        total_debit = amount + fee

        # 4. بررسی موجودی
        if Decimal(card.balance or 0) < total_debit:
            raise InsufficientFunds("Not enough balance to cover amount and fee.")

        # 5. ثبت تراکنش در Session
        ins = Transaction(
            source_card_id=card.id,
            dest_card_id=None,
            amount=amount,
            fee=fee,
            status="SUCCESS",
            description=description
        )
        self.db.add(ins)

        # 6. به‌روزرسانی موجودی
        await self.db.execute(
            update(Card)
            .where(Card.id == card.id)
            .values(balance=Card.balance - literal(total_debit))
        )

        # flush لازم است تا آبجکت ins دارای ID باشد
        await self.db.flush()
        return ins

    async def transfer(self, source_card_number: str, dest_card_number: str, amount, description: str | None = None,
                       user_id: int | None = None):
        """عملیات انتقال وجه بین دو کارت."""
        try:
            amount = Decimal(str(amount))
        except Exception:
            raise BusinessRuleViolation("Invalid amount format")

        if amount < MIN_TX or amount > MAX_TX:
            raise BusinessRuleViolation(f"Amount must be between {MIN_TX} and {MAX_TX} Tomans.")

        if source_card_number == dest_card_number:
            raise BusinessRuleViolation("Cannot transfer money to the same card.")

        # 1. واکشی و قفل کردن دو کارت (Repository مسئول مدیریت ترتیب قفل است)
        src_temp = await self.tx_repo.get_card_by_number_for_update(source_card_number)
        dst_temp = await self.tx_repo.get_card_by_number_for_update(dest_card_number)

        if not src_temp or not dst_temp:
            raise BusinessRuleViolation("Source or destination card not found.")

        locked_src, locked_dst = await self.tx_repo.get_cards_by_id_for_update(src_temp.id, dst_temp.id)

        # 2. اعتبارسنجی مالکیت و وضعیت
        if locked_src.user_id != user_id:
            raise ForbiddenOperation("Source card does not belong to the current user.")

        if not locked_src.is_active or not locked_dst.is_active:
            raise BusinessRuleViolation("One of cards is not active.")

        # 3. بررسی سقف روزانه
        now = datetime.now(timezone.utc)
        start = datetime.combine(now.date(), datetime.min.time()).replace(tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        daily_total = await self._daily_total_for_card(locked_src.id, start, end)
        if (daily_total + amount) > CARD_DAILY_CAP:
            raise BusinessRuleViolation("Card daily limit exceeded.")

        fee = self.calc_fee(amount)
        total_debit = amount + fee

        # 4. بررسی موجودی
        if Decimal(locked_src.balance or 0) < total_debit:
            raise InsufficientFunds("Not enough balance to cover amount and fee.")

        # 5. ثبت تراکنش در Session
        ins = Transaction(
            source_card_id=locked_src.id,
            dest_card_id=locked_dst.id,
            amount=amount,
            fee=fee,
            status="SUCCESS",
            description=description
        )
        self.db.add(ins)

        # 6. به‌روزرسانی موجودی‌ها
        await self.db.execute(
            update(Card)
            .where(Card.id == locked_src.id)
            .values(balance=Card.balance - literal(total_debit))
        )
        await self.db.execute(
            update(Card)
            .where(Card.id == locked_dst.id)
            .values(balance=Card.balance + literal(amount))
        )

        await self.db.flush()
        return ins

    async def get_fee_income(
            self,
            date_from: Optional[datetime],
            date_to: Optional[datetime],
            tx_id: Optional[int]
    ) -> Decimal:
        """فراخوانی Repository برای محاسبه درآمد کل کارمزدها (نیازمندی 7)."""
        # در اینجا می‌توانید منطق اعتبارسنجی سطح دسترسی کاربر (Role Check) را قرار دهید.
        return await self.tx_repo.fee_sum(date_from=date_from, date_to=date_to, tx_id=tx_id)
