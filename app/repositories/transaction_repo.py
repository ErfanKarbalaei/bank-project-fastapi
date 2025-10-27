from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from asyncpg import Connection


async def get_card_by_number_for_update(self, card_number: str) -> Optional[dict]:
    sql = "SELECT * FROM cards WHERE card_number = $1 FOR UPDATE;"
    record = await self.conn.fetchrow(sql, card_number)
    return dict(record) if record else None

async def get_cards_by_id_for_update(self, id1: int, id2: int) -> tuple[dict, dict]:
    ids = sorted([id1, id2])
    sql = "SELECT * FROM cards WHERE id IN ($1, $2) ORDER BY id FOR UPDATE;"
    locked_records = await self.conn.fetch(sql, ids[0], ids[1])

    if len(locked_records) != 2:
        raise ValueError("Could not lock both cards during transfer.")

    locked_cards = [dict(r) for r in locked_records]
    card_map = {c['id']: c for c in locked_cards}
    return card_map[id1], card_map[id2]

async def create_transaction(
        self,
        source_id: int,
        dest_id: Optional[int],
        amount: Decimal,
        fee: Decimal,
        status: str,
        description: Optional[str] = None,
) -> dict:
    sql = """
        INSERT INTO transactions 
        (source_card_id, dest_card_id, amount, fee, status, description, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *;
    """
    now = datetime.now()
    record = await self.conn.fetchrow(
        sql,
        source_id,
        dest_id,
        amount,
        fee,
        status,
        description,
        now
    )

    if record is None:
        raise Exception("Failed to create transaction record.")

    return dict(record)

async def recent_for_user(self, user_id: int, limit: int = 10) -> List[dict]:
    sql = """
        SELECT 
            t.*,
            sc.card_number as source_card_number,
            dc.card_number as dest_card_number
        FROM transactions t
        JOIN cards sc ON t.source_card_id = sc.id 
        LEFT JOIN cards dc ON t.dest_card_id = dc.id 
        WHERE sc.user_id = $1 
        OR dc.user_id = $1 
        ORDER BY t.created_at DESC
        LIMIT $2;
    """
    records = await self.conn.fetch(sql, user_id, limit)
    return [dict(record) for record in records]

async def fee_sum(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tx_id: Optional[int] = None,
) -> Decimal:
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