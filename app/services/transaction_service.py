# app/services/transaction_service.py

from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta, timezone
from typing import Optional

# ❌ حذف ایمپورت‌های SQLAlchemy
# from sqlalchemy import select, update, func, literal
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.exc import NoResultFound

# ✅ اضافه کردن ایمپورت‌های مورد نیاز
from asyncpg import Connection
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.card_repo import CardRepository  # نیاز به CardRepository برای تغییر موجودی

# ⚠️ حذف ایمپورت مدل‌های SQLAlchemy (چون دیگر از آن‌ها استفاده نمی‌شود)
# from app.db.models.card_model import Card 
# from app.db.models.transaction_model import Transaction 


# پارامترهای کسب‌وکار (بدون تغییر)
MIN_TX = Decimal("1000")
MAX_TX = Decimal("50000000")
FEE_RATE = Decimal("0.10")
FEE_CAP = Decimal("100000")
CARD_DAILY_CAP = Decimal("50000000")


# کلاس‌های خطای سفارشی (بدون تغییر)
class InsufficientFunds(Exception): pass


class BusinessRuleViolation(Exception): pass


class ForbiddenOperation(Exception): pass


class TransactionService:
    """
    مدیریت منطق تراکنش‌ها و اعتبارسنجی‌های کسب‌وکار.
    """

    # ⚠️ تغییرات: ورودی را به Connection و هر دو Repository تغییر می‌دهیم
    def __init__(self, conn: Connection, tx_repo: TransactionRepository, card_repo: CardRepository):
        self.conn = conn  # ⚠️ اتصال asyncpg برای مدیریت تراکنش
        self.tx_repo = tx_repo
        self.card_repo = card_repo

    def calc_fee(self, amount: Decimal) -> Decimal:
        """محاسبه کارمزد تراکنش با در نظر گرفتن سقف."""
        fee = (amount * FEE_RATE).quantize(Decimal("1."), rounding=ROUND_DOWN)
        return min(fee, FEE_CAP)

    # ❌ حذف متد _daily_total_for_card (چون ORM بود)
    # و استفاده مستقیم از متد مشابه در card_repo

    async def withdraw_from_card(self, card_number: str, amount, description: str | None = None,
                                 user_id: int | None = None):
        """عملیات برداشت از کارت."""
        try:
            amount = Decimal(str(amount))
        except Exception:
            raise BusinessRuleViolation("Invalid amount format")

        if amount < MIN_TX or amount > MAX_TX:
            raise BusinessRuleViolation(f"Amount must be between {MIN_TX} and {MAX_TX} Tomans.")

        # 🌟 مدیریت تراکنش در Service (جایگزین commit/rollback در Endpoint)
        async with self.conn.transaction():
            # 1. قفل کردن ردیف کارت با استفاده از Repository
            # Repository باید کارت را به صورت دیکشنری برگرداند
            card = await self.tx_repo.get_card_by_number_for_update(card_number)

            if card is None:
                raise BusinessRuleViolation("Card not found")

            # 2. اعتبارسنجی مالکیت و وضعیت (استفاده از کلیدهای دیکشنری)
            if card['user_id'] != user_id:
                raise ForbiddenOperation("Card does not belong to the current user.")

            if not card['is_active']:
                raise BusinessRuleViolation("Card not active")

            # 3. بررسی سقف روزانه (استفاده از متد Repository)
            now = datetime.now(timezone.utc)
            start = datetime.combine(now.date(), datetime.min.time()).replace(tzinfo=timezone.utc)
            end = start + timedelta(days=1)

            # ⚠️ فراخوانی متد asyncpg Repository
            daily_total = await self.card_repo.daily_total_for_card(card['id'], start, end)

            if (daily_total + amount) > CARD_DAILY_CAP:
                raise BusinessRuleViolation("Card daily limit exceeded.")

            fee = self.calc_fee(amount)
            total_debit = amount + fee

            # 4. بررسی موجودی
            if Decimal(card['balance'] or 0) < total_debit:
                raise InsufficientFunds("Not enough balance to cover amount and fee.")

            # 5. ثبت تراکنش (فراخوانی متد Repository)
            tx_record = await self.tx_repo.create_transaction(
                source_id=card['id'],
                dest_id=None,  # برای برداشت None
                amount=amount,
                fee=fee,
                status="SUCCESS",
                description=description
            )

            # 6. به‌روزرسانی موجودی (فراخوانی متد Repository)
            await self.card_repo.change_balance(card['id'], -total_debit)

            # در asyncpg، پس از خروج از بلوک transaction، commit به صورت خودکار انجام می‌شود.
            # اگر خطایی رخ دهد، Rollback انجام می‌شود.
            return tx_record  # رکورد دیکشنری تراکنش جدید

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

        # 🌟 مدیریت تراکنش در Service
        async with self.conn.transaction():
            # 1. واکشی دو کارت (بدون قفل)
            src_temp = await self.tx_repo.get_card_by_number_for_update(source_card_number)
            dst_temp = await self.tx_repo.get_card_by_number_for_update(dest_card_number)

            if not src_temp or not dst_temp:
                raise BusinessRuleViolation("Source or destination card not found.")

            # 2. قفل کردن ترتیبی کارت‌ها
            # Repository باید مطمئن شود که این عملیات در داخل همین تراکنش اجرا می‌شود
            locked_src, locked_dst = await self.tx_repo.get_cards_by_id_for_update(src_temp['id'], dst_temp['id'])

            # 3. اعتبارسنجی مالکیت و وضعیت (استفاده از کلیدهای دیکشنری)
            if locked_src['user_id'] != user_id:
                raise ForbiddenOperation("Source card does not belong to the current user.")

            if not locked_src['is_active'] or not locked_dst['is_active']:
                raise BusinessRuleViolation("One of cards is not active.")

            # 4. بررسی سقف روزانه (فراخوانی متد Repository)
            now = datetime.now(timezone.utc)
            start = datetime.combine(now.date(), datetime.min.time()).replace(tzinfo=timezone.utc)
            end = start + timedelta(days=1)

            daily_total = await self.card_repo.daily_total_for_card(locked_src['id'], start, end)

            if (daily_total + amount) > CARD_DAILY_CAP:
                raise BusinessRuleViolation("Card daily limit exceeded.")

            fee = self.calc_fee(amount)
            total_debit = amount + fee

            # 5. بررسی موجودی
            if Decimal(locked_src['balance'] or 0) < total_debit:
                raise InsufficientFunds("Not enough balance to cover amount and fee.")

            # 6. ثبت تراکنش (فراخوانی متد Repository)
            tx_record = await self.tx_repo.create_transaction(
                source_id=locked_src['id'],
                dest_id=locked_dst['id'],
                amount=amount,
                fee=fee,
                status="SUCCESS",
                description=description
            )

            # 7. به‌روزرسانی موجودی‌ها (فراخوانی متد Repository)
            await self.card_repo.change_balance(locked_src['id'], -total_debit)
            await self.card_repo.change_balance(locked_dst['id'], amount)

            return tx_record

    async def get_fee_income(
            self,
            date_from: Optional[datetime],
            date_to: Optional[datetime],
            tx_id: Optional[int]
    ) -> Decimal:
        """فراخوانی Repository برای محاسبه درآمد کل کارمزدها."""
        # این متد نیاز به تراکنش ندارد چون فقط SELECT است.
        return await self.tx_repo.fee_sum(date_from=date_from, date_to=date_to, tx_id=tx_id)