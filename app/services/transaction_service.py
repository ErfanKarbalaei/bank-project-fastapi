from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta, timezone
from typing import Optional
from asyncpg import Connection
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.card_repo import CardRepository

MIN_TX = Decimal("1000")
MAX_TX = Decimal("50000000")
FEE_RATE = Decimal("0.10")
FEE_CAP = Decimal("100000")
CARD_DAILY_CAP = Decimal("50000000")

class InsufficientFunds(Exception): pass
class BusinessRuleViolation(Exception): pass
class ForbiddenOperation(Exception): pass

DecimalLike = str | int | float | Decimal


class TransactionService:
    def __init__(self, conn: Connection, tx_repo: TransactionRepository, card_repo: CardRepository):
        self.conn = conn
        self.tx_repo = tx_repo
        self.card_repo = card_repo

    def calc_fee(self, amount: Decimal) -> Decimal:
        """محاسبه کارمزد با سقف مشخص"""
        fee = (amount * FEE_RATE).quantize(Decimal("1."), rounding=ROUND_DOWN)
        return min(fee, FEE_CAP)

    async def withdraw_from_card(
        self, card_number: str, amount: DecimalLike,
        description: str | None = None, user_id: int | None = None
    ):
        try:
            amount = Decimal(str(amount)).quantize(Decimal("1."), rounding=ROUND_DOWN)
        except Exception:
            raise BusinessRuleViolation("Invalid amount format")

        if amount < MIN_TX or amount > MAX_TX:
            raise BusinessRuleViolation(f"Amount must be between {MIN_TX} and {MAX_TX} Tomans.")

        async with self.conn.transaction():
            card = await self.tx_repo.get_card_by_number_for_update(card_number)
            if not card:
                raise BusinessRuleViolation("Card not found")
            if card["user_id"] != user_id:
                raise ForbiddenOperation("Card does not belong to current user.")
            if not card["is_active"]:
                raise BusinessRuleViolation("Card not active")

            now = datetime.now(timezone.utc)
            start = datetime.combine(now.date(), datetime.min.time()).replace(tzinfo=timezone.utc)
            end = start + timedelta(days=1)

            daily_total = await self.card_repo.daily_total_for_card(card["id"], start, end)
            if (daily_total + amount) > CARD_DAILY_CAP:
                raise BusinessRuleViolation("Card daily limit exceeded.")

            fee = self.calc_fee(amount)
            total_debit = amount + fee

            balance = Decimal(str(card.get("balance") or "0"))
            if balance < total_debit:
                raise InsufficientFunds("Not enough balance.")

            tx_record = await self.tx_repo.create_transaction(
                source_id=card["id"],
                dest_id=None,
                amount=amount,
                fee=fee,
                status="SUCCESS",
                description=description,
            )

            await self.card_repo.change_balance(card["id"], -total_debit)
            return tx_record

    async def transfer(
        self, source_card_number: str, dest_card_number: str, amount: DecimalLike,
        description: str | None = None, user_id: int | None = None
    ):
        try:
            amount = Decimal(str(amount)).quantize(Decimal("1."), rounding=ROUND_DOWN)
        except Exception:
            raise BusinessRuleViolation("Invalid amount format")

        if amount < MIN_TX or amount > MAX_TX:
            raise BusinessRuleViolation(f"Amount must be between {MIN_TX} and {MAX_TX} Tomans.")
        if source_card_number == dest_card_number:
            raise BusinessRuleViolation("Cannot transfer to same card.")

        async with self.conn.transaction():
            # مرحله ۱: پیدا کردن کارت‌ها بر اساس شماره
            src_temp = await self.tx_repo.get_card_by_number_for_update(source_card_number)
            dst_temp = await self.tx_repo.get_card_by_number_for_update(dest_card_number)

            if not src_temp or not dst_temp:
                raise BusinessRuleViolation("Source or destination card not found.")

            # مرحله ۲: قفل نهایی بر اساس ID
            locked_src, locked_dst = await self.tx_repo.get_cards_by_number_for_update(src_temp["card_number"], dst_temp["card_number"])

            if locked_src["user_id"] != user_id:
                raise ForbiddenOperation("Source card does not belong to current user.")
            if not locked_src["is_active"] or not locked_dst["is_active"]:
                raise BusinessRuleViolation("One of the cards is inactive.")

            now = datetime.now(timezone.utc)
            start = datetime.combine(now.date(), datetime.min.time()).replace(tzinfo=timezone.utc)
            end = start + timedelta(days=1)

            daily_total = await self.card_repo.daily_total_for_card(locked_src["id"], start, end)
            if (daily_total + amount) > CARD_DAILY_CAP:
                raise BusinessRuleViolation("Card daily limit exceeded.")

            fee = self.calc_fee(amount)
            total_debit = amount + fee

            src_balance = Decimal(str(locked_src.get("balance") or "0"))
            if src_balance < total_debit:
                raise InsufficientFunds("Not enough balance.")

            tx_record = await self.tx_repo.create_transaction(
                source_id=locked_src["id"],
                dest_id=locked_dst["id"],
                amount=amount,
                fee=fee,
                status="SUCCESS",
                description=description,
            )

            await self.card_repo.change_balance(locked_src["id"], -total_debit)
            await self.card_repo.change_balance(locked_dst["id"], amount)
            return tx_record

    async def get_fee_income(
        self, date_from: Optional[datetime], date_to: Optional[datetime], tx_id: Optional[int]
    ) -> Decimal:
        return await self.tx_repo.fee_sum(date_from=date_from, date_to=date_to, tx_id=tx_id)
