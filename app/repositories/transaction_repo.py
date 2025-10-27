from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from asyncpg import Connection


class TransactionRepository:
    """Repository برای عملیات تراکنش‌ها با asyncpg."""

    def __init__(self, conn: Connection):
        self.conn = conn

    # ------------------ Card Locking ------------------ #
    async def get_card_by_number_for_update(self, card_number: str) -> dict | None:
        sql = "SELECT * FROM cards WHERE card_number = $1 FOR UPDATE;"
        rec = await self.conn.fetchrow(sql, card_number)
        return dict(rec) if rec else None

    async def get_cards_by_number_for_update(self, src_number: str, dst_number: str) -> tuple[dict, dict]:
        ids_sql = "SELECT id FROM cards WHERE card_number IN ($1, $2)"
        ids = [r["id"] for r in await self.conn.fetch(ids_sql, src_number, dst_number)]
        if len(ids) != 2:
            raise ValueError("Could not find both cards.")
        ids.sort()
        sql = "SELECT * FROM cards WHERE id IN ($1, $2) ORDER BY id FOR UPDATE;"
        records = await self.conn.fetch(sql, ids[0], ids[1])
        card_map = {r["id"]: dict(r) for r in records}
        return card_map[ids[0]], card_map[ids[1]]

    # ------------------ Transaction Queries ------------------ #
    async def create_transaction(
        self,
        source_id: int,
        dest_id: Optional[int],
        amount: Decimal,
        fee: Decimal,
        status: str,
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> dict:
        sql = """
            INSERT INTO transactions 
            (source_card_id, dest_card_id, amount, fee, status, description, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *;
        """
        created_at = created_at or datetime.now(timezone.utc)
        rec = await self.conn.fetchrow(sql, source_id, dest_id, amount, fee, status, description, created_at)
        if not rec:
            raise Exception("Failed to insert transaction.")
        return dict(rec)

    async def recent_for_user(self, user_id: int, limit: int = 10) -> List[dict]:
        sql = """
            SELECT 
                t.*,
                sc.card_number AS source_card_number,
                dc.card_number AS dest_card_number
            FROM transactions t
            JOIN cards sc ON t.source_card_id = sc.id
            LEFT JOIN cards dc ON t.dest_card_id = dc.id
            WHERE COALESCE(sc.user_id, dc.user_id) = $1
            ORDER BY t.created_at DESC
            LIMIT $2;
        """
        rows = await self.conn.fetch(sql, user_id, limit)
        return [dict(r) for r in rows]

    async def fee_sum(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tx_id: Optional[int] = None,
    ) -> Decimal:
        clauses = ["status = 'SUCCESS'"]
        args = []

        if tx_id:
            clauses.append(f"id = ${len(args)+1}")
            args.append(tx_id)
        if date_from:
            clauses.append(f"created_at >= ${len(args)+1}")
            args.append(date_from)
        if date_to:
            clauses.append(f"created_at <= ${len(args)+1}")
            args.append(date_to)

        sql = f"SELECT COALESCE(SUM(fee), 0) FROM transactions WHERE {' AND '.join(clauses)};"
        total = await self.conn.fetchval(sql, *args)
        return Decimal(total or 0)
