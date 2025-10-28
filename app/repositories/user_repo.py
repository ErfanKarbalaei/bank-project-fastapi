from typing import Optional
from asyncpg import Connection

class UserRepository:

    def __init__(self, conn: Connection):
        self.conn = conn

    async def get_by_phone(self, phone_number: str) -> Optional[dict]:
        sql = "SELECT * FROM users WHERE phone_number = $1;"
        record = await self.conn.fetchrow(sql, phone_number)
        return dict(record) if record else None

    async def get_by_id(self, user_id: int) -> Optional[dict]:
        sql = "SELECT * FROM users WHERE id = $1;"
        record = await self.conn.fetchrow(sql, user_id)
        return dict(record) if record else None

    async def get_by_national_code(self, national_code: str) -> Optional[dict]:
        sql = "SELECT * FROM users WHERE national_code = $1;"
        record = await self.conn.fetchrow(sql, national_code)
        return dict(record) if record else None

    async def create(self, user_in: dict) -> dict:
        sql = """
            INSERT INTO users (national_code, full_name, phone_number, email, hashed_password, is_active)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *;
        """
        record = await self.conn.fetchrow(
            sql,
            user_in["national_code"],
            user_in["full_name"],
            user_in["phone_number"],
            user_in["email"],
            user_in["hashed_password"],
            True
        )
        return dict(record)
