# app/repositories/transaction_repo.py

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
import asyncpg
from asyncpg import Connection


# ⚠️ ایمپورت‌های SQLAlchemy حذف می‌شوند

class TransactionRepository:
    """Repository برای عملیات پایگاه داده مرتبط با تراکنش‌ها و کارت‌ها با asyncpg."""

    # ⚠️ تغییر type hint
    def __init__(self, conn: Connection):
        self.conn = conn

    # ------------------ Card Locking (In-Transaction) ------------------ #

    async def get_card_by_number_for_update(self, card_number: str) -> dict | None:
        """واکشی کارت با شماره کارت و قفل‌گذاری (SELECT ... FOR UPDATE) با کوئری خام."""
        # فرض می‌شود که این متد در داخل یک بلوک async with conn.transaction(): فراخوانی می‌شود.
        sql = "SELECT * FROM cards WHERE card_number = $1 FOR UPDATE;"
        record = await self.conn.fetchrow(sql, card_number)
        return dict(record) if record else None

    async def get_cards_by_id_for_update(self, id1: int, id2: int) -> tuple[dict, dict]:
        """
        واکشی و قفل دو کارت به‌صورت ترتیبی برای جلوگیری از Deadlock (با کوئری خام).
        """
        ids = sorted([id1, id2])

        # ⚠️ اجرای قفل‌گذاری بر اساس ID مرتب شده
        sql = "SELECT * FROM cards WHERE id IN ($1, $2) FOR UPDATE ORDER BY id;"

        # استفاده از fetch برای دریافت دو رکورد
        locked_records = await self.conn.fetch(sql, ids[0], ids[1])

        if len(locked_records) != 2:
            raise ValueError("Could not lock both cards during transfer.")

        # تبدیل Row به دیکشنری
        locked_cards = [dict(r) for r in locked_records]

        # نگاشت مجدد به IDهای اصلی (id1, id2)
        card_map = {c['id']: c for c in locked_cards}

        return card_map[id1], card_map[id2]

    # ------------------ Transaction Queries ------------------ #

    async def recent_for_user(self, user_id: int, limit: int = 10) -> List[dict]:
        """
        دریافت تراکنش‌های اخیر کاربر (چه مبدأ و چه مقصد) (با کوئری خام).
        از LEFT JOIN برای کارت مقصد (dest_card_id=NULL) استفاده می‌شود.
        """
        sql = """
            SELECT 
                t.*,
                sc.card_number as source_card_number,
                -- ⚠️ dest_card_number می‌تواند NULL باشد
                dc.card_number as dest_card_number
            FROM transactions t
            -- INNER JOIN برای کارت مبدأ (source_card_id همیشه مقدار دارد)
            JOIN cards sc ON t.source_card_id = sc.id 
            -- ✅ LEFT JOIN برای کارت مقصد (dest_card_id می‌تواند NULL باشد)
            LEFT JOIN cards dc ON t.dest_card_id = dc.id 
            -- شرط: کارت مبدأ متعلق به کاربر باشد (تراکنش‌های برداشت و واریز)
            -- یا کارت مقصد متعلق به کاربر باشد (تراکنش‌های دریافتی/واریز به کارت کاربر)
            WHERE sc.user_id = $1 
            -- ✅ OR برای شامل شدن تراکنش‌هایی که dest_card_id آنها NULL است (برداشت)
            -- همچنین تراکنش‌های واریز به کارت‌های این کاربر را هم شامل می‌شود.
            OR dc.user_id = $1 
            ORDER BY t.created_at DESC
            LIMIT $2;
        """
        records = await self.conn.fetch(sql, user_id, limit)
        return [dict(record) for record in records]

    # ------------------ Aggregation ------------------ #

    async def fee_sum(
            self,
            date_from: Optional[datetime] = None,
            date_to: Optional[datetime] = None,
            tx_id: Optional[int] = None,
    ) -> Decimal:
        """محاسبه مجموع کارمزد تراکنش‌های موفق با فیلترهای اختیاری (با کوئری خام)."""

        base_sql = "SELECT COALESCE(SUM(fee), 0) FROM transactions WHERE status = 'SUCCESS'"
        args = []
        i = 1

        if tx_id is not None:
            base_sql += f" AND id = ${i}"
            args.append(tx_id)
            i += 1

        if date_from:
            base_sql += f" AND created_at >= ${i}"
            args.append(date_from)
            i += 1

        if date_to:
            base_sql += f" AND created_at <= ${i}"
            args.append(date_to)
            i += 1

        total = await self.conn.fetchval(base_sql, *args)

        return Decimal(total or 0)