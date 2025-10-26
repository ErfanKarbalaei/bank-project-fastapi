# app/repositories/card_repo.py

from decimal import Decimal
from asyncpg import Connection, UniqueViolationError
from datetime import date, datetime
from typing import Optional


# ⚠️ حذف ایمپورت‌های SQLAlchemy (select, update, func, AsyncSession)

class CardRepository:
    """Repository برای انجام عملیات مرتبط با کارت‌ها با asyncpg."""

    def __init__(self, conn: Connection):
        self.conn = conn

    # ------------------ Retrieval Methods ------------------ #

    async def get_by_id(self, card_id: int) -> dict | None:
        """دریافت کارت بر اساس ID."""
        sql = "SELECT * FROM cards WHERE id = $1;"
        record = await self.conn.fetchrow(sql, card_id)
        return dict(record) if record else None

    async def get_by_number(self, card_number: str) -> dict | None:
        """دریافت کارت بر اساس شماره کارت."""
        sql = "SELECT * FROM cards WHERE card_number = $1;"
        record = await self.conn.fetchrow(sql, card_number)
        return dict(record) if record else None

    async def list_by_user(self, user_id: int) -> list[dict]:
        """لیست کارت‌های متعلق به کاربر."""
        sql = "SELECT * FROM cards WHERE user_id = $1 ORDER BY id;"
        records = await self.conn.fetch(sql, user_id)
        return [dict(record) for record in records]

    # ------------------ Creation ------------------ #

    async def create_card(self, user_id: int, card_number: str, cvv2: str, expire_date: str) -> dict:
        """ایجاد یک کارت جدید برای کاربر و برگرداندن رکورد جدید."""
        sql = """
            INSERT INTO cards (user_id, card_number, cvv2, expire_date, balance, is_active)
            VALUES ($1, $2, $3, $4, 0.00, TRUE)
            RETURNING *;
        """
        try:
            record = await self.conn.fetchrow(
                sql, user_id, card_number, cvv2, expire_date
            )
            return dict(record)
        except UniqueViolationError:
            # در صورت تکراری بودن شماره کارت
            raise ValueError("Card number already exists")

    # ------------------ Update / Lock Methods ------------------ #

    async def lock_by_id(self, card_id: int) -> dict | None:
        """دریافت کارت با قفل (SELECT ... FOR UPDATE)."""
        sql = "SELECT * FROM cards WHERE id = $1 FOR UPDATE;"
        record = await self.conn.fetchrow(sql, card_id)
        return dict(record) if record else None

    async def change_balance(self, card_id: int, amount: Decimal) -> bool:
        """تغییر موجودی کارت (مقدار می‌تواند منفی باشد)."""
        # ما فقط ID کارت را برای تغییر موجودی نیاز داریم
        sql = "UPDATE cards SET balance = balance + $1 WHERE id = $2;"
        status = await self.conn.execute(sql, amount, card_id)
        # asyncpg نتیجه execute را به صورت 'UPDATE N' برمی‌گرداند.
        return status == "UPDATE 1"

    # ------------------ Aggregation Methods ------------------ #

    async def daily_total_for_card(self, card_id: int, date_from: datetime, date_to: datetime) -> Decimal:
        """محاسبه مجموع تراکنش‌های روزانه موفق برای یک کارت مبدأ در بازه زمانی مشخص."""
        # ما فقط تراکنش‌های موفق را برای سقف روزانه حساب می‌کنیم
        sql = """
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE source_card_id = $1
            AND created_at >= $2
            AND created_at < $3
            AND status = 'SUCCESS';
        """
        # استفاده از fetchval برای دریافت یک مقدار واحد
        total = await self.conn.fetchval(sql, card_id, date_from, date_to)
        return Decimal(total or 0)
