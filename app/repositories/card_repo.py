from decimal import Decimal
from asyncpg import Connection, UniqueViolationError
from datetime import datetime, timezone
from typing import Optional


class CardRepository:
    """Repository برای انجام عملیات مرتبط با کارت‌ها با asyncpg."""

    def __init__(self, conn: Connection):
        self.conn = conn

    # ------------------ Retrieval Methods ------------------ #

    async def get_by_id(self, card_id: int) -> dict | None:
        sql = "SELECT * FROM cards WHERE id = $1;"
        record = await self.conn.fetchrow(sql, card_id)
        return dict(record) if record else None

    async def get_by_number(self, card_number: str) -> dict | None:
        sql = "SELECT * FROM cards WHERE card_number = $1;"
        record = await self.conn.fetchrow(sql, card_number)
        return dict(record) if record else None

    async def list_by_user(self, user_id: int) -> list[dict]:
        sql = "SELECT * FROM cards WHERE user_id = $1 ORDER BY id;"
        records = await self.conn.fetch(sql, user_id)
        return [dict(record) for record in records]

    # ------------------ Creation ------------------ #

    async def create_card(self, user_id: int, card_number: str, cvv2: str, expire_date: str) -> dict:
        sql = """
            INSERT INTO cards (user_id, card_number, cvv2, expire_date, balance, is_active)
            VALUES ($1, $2, $3, $4, 0.00, TRUE)
            RETURNING *;
        """
        try:
            record = await self.conn.fetchrow(sql, user_id, card_number, cvv2, expire_date)
            return dict(record)
        except UniqueViolationError:
            raise ValueError("Card number already exists")

    # ------------------ Update / Lock Methods ------------------ #

    async def lock_by_id(self, card_id: int) -> dict:
        sql = "SELECT * FROM cards WHERE id = $1 FOR UPDATE;"
        record = await self.conn.fetchrow(sql, card_id)
        if not record:
            raise ValueError(f"Card with id {card_id} not found for update")
        return dict(record)

    async def change_balance(self, card_id: int, amount: Decimal) -> Optional[Decimal]:
        sql = "UPDATE cards SET balance = balance + $1 WHERE id = $2 RETURNING balance;"
        new_balance = await self.conn.fetchval(sql, amount, card_id)
        return Decimal(new_balance) if new_balance is not None else None

    # ------------------ Aggregation Methods ------------------ #

    async def daily_total_for_card(self, card_id: int, date_from: datetime, date_to: datetime) -> Decimal:
        if date_from.tzinfo is None:
            date_from = date_from.replace(tzinfo=timezone.utc)
        if date_to.tzinfo is None:
            date_to = date_to.replace(tzinfo=timezone.utc)

        sql = """
            SELECT COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE source_card_id = $1
              AND created_at >= $2
              AND created_at < $3
              AND status = 'SUCCESS';
        """
        total = await self.conn.fetchval(sql, card_id, date_from, date_to)
        return Decimal(total or 0)
