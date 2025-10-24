from decimal import Decimal
from app.repositories.transaction_repo import TransactionRepository

DAILY_LIMIT = Decimal("50000000")
MIN_AMOUNT = Decimal("1000")
MAX_AMOUNT = Decimal("50000000")

class TransactionService:
    def __init__(self, repo: TransactionRepository):
        self.repo = repo

    async def transfer(self, src_card_number: str, dst_card_number: str, amount: Decimal, description: str | None):
        if amount < MIN_AMOUNT or amount > MAX_AMOUNT:
            raise ValueError("مبلغ تراکنش خارج از محدوده مجاز است.")

        cards = await self.repo.get_cards_with_lock(src_card_number, dst_card_number)
        source = next((c for c in cards if c.card_number == src_card_number), None)
        dest = next((c for c in cards if c.card_number == dst_card_number), None)

        if not source or not dest:
            raise ValueError("کارت مبدأ یا مقصد پیدا نشد.")
        if source.id == dest.id:
            raise ValueError("نمی‌توان به کارت خود انتقال داد.")
        if not source.is_active or not dest.is_active:
            raise ValueError("کارت غیرفعال است.")

        daily_sum = await self.repo.get_daily_total(source.id)
        if daily_sum + amount > DAILY_LIMIT:
            raise ValueError("سقف روزانه انتقال وجه پر شده است.")

        fee = min(amount * Decimal("0.01"), Decimal("100000"))
        total = amount + fee

        if source.balance < total:
            raise ValueError("موجودی کافی نیست.")

        # بروزرسانی مانده حساب‌ها
        source.balance -= total
        dest.balance += amount

        # ایجاد رکورد تراکنش
        tx = await self.repo.create_transaction(source.id, dest.id, amount, fee, description)
        return tx
