# app/db/seed.py
import asyncio
import random
from datetime import datetime, timezone, timedelta
from faker import Faker
from tqdm import tqdm

from app.db.session import connect_db_pool, get_pool, close_db_pool
from app.core.security import hash_password

fake = Faker("fa_IR")

# پارامترها
NUM_USERS = 50
MIN_CARDS_PER_USER = 1
MAX_CARDS_PER_USER = 3
NUM_TRANSACTIONS = 100_000
BATCH_TX = 2000

# واحد: ریال
MIN_TX_AMOUNT_RIAL = 10_000        # 1,000 تومان
MAX_TX_AMOUNT_RIAL = 500_000       # 50,000 تومان — کاهش یافته برای تست راحت‌تر
FEE_PERCENT = 0.10
FEE_CAP_RIAL = 1_000_000           # 100,000 تومان = 1,000,000 ریال


async def insert_user(conn, national_code: str, full_name: str, phone: str, email: str, hashed_password: str):
    sql = """
    INSERT INTO users (national_code, full_name, phone_number, email, hashed_password, is_active)
    VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING id;
    """
    rec = await conn.fetchrow(sql, national_code, full_name, phone, email, hashed_password, True)
    return rec["id"]


async def insert_card(conn, user_id: int, card_number: str, cvv2: str, expire_date: str, balance_rial: int):
    sql = """
    INSERT INTO cards (user_id, card_number, cvv2, expire_date, balance, is_active)
    VALUES ($1, $2, $3, $4, $5, $6)
    RETURNING id;
    """
    rec = await conn.fetchrow(sql, user_id, card_number, cvv2, expire_date, balance_rial, True)
    return rec["id"]


def random_datetime_within_last_n_months(months: int = 6) -> datetime:
    now = datetime.now(tz=timezone.utc)
    start = now - timedelta(days=30 * months)
    delta_seconds = int((now - start).total_seconds())
    rand_seconds = random.randint(0, max(0, delta_seconds))
    return start + timedelta(seconds=rand_seconds)


async def seed():
    await connect_db_pool()
    pool = await get_pool()
    if pool is None:
        raise RuntimeError("Database pool could not be initialized")

    async with pool.acquire() as conn:
        print("🧍‍♂️ ایجاد کاربران...")
        user_ids = []

        for _ in range(NUM_USERS):
            national_code = str(fake.unique.random_number(digits=10)).zfill(10)
            full_name = fake.name()
            phone = f"09{random.randint(100000000, 999999999)}"
            email = fake.unique.email()
            hashed_password = hash_password("bank123")
            uid = await insert_user(conn, national_code, full_name, phone, email, hashed_password)
            user_ids.append(uid)

        print("💳 ایجاد کارت‌ها...")
        card_ids = []

        def generate_card_number():
            prefix = random.choice(["6037", "6274", "5892", "6104"])
            rest = "".join(str(random.randint(0, 9)) for _ in range(12))
            return prefix + rest

        for uid in user_ids:
            n_cards = random.randint(MIN_CARDS_PER_USER, MAX_CARDS_PER_USER)
            for _ in range(n_cards):
                card_number = generate_card_number()
                cvv2 = f"{random.randint(100, 9999)}"
                expire_date = f"{random.randint(1, 12):02d}/{random.randint(25, 30)}"
                balance = random.randint(1_000_000, 50_000_000)
                cid = await insert_card(conn, uid, card_number, cvv2, expire_date, balance)
                card_ids.append({"id": cid, "user_id": uid})

        if not card_ids:
            raise RuntimeError("No cards created — aborting seed")

        print("💰 ایجاد تراکنش‌ها (ممکن است چند دقیقه طول بکشد)...")
        tx_sql = """
        INSERT INTO transactions
        (source_card_id, dest_card_id, amount, fee, status, description, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        statuses = ["SUCCESS", "FAILED", "PENDING"]
        tx_batch = []

        for _ in tqdm(range(NUM_TRANSACTIONS), desc="Generating transactions"):
            src = random.choice(card_ids)
            dst = random.choice(card_ids)
            while dst["id"] == src["id"]:
                dst = random.choice(card_ids)

            # مقدار تراکنش کوچک‌تر (برای جلوگیری از رسیدن سریع به سقف در تست)
            amount = random.randint(MIN_TX_AMOUNT_RIAL, MAX_TX_AMOUNT_RIAL)
            fee = int(min(amount * FEE_PERCENT, FEE_CAP_RIAL))
            status = random.choices(statuses, weights=[0.85, 0.10, 0.05])[0]
            description = fake.sentence(nb_words=6)

            # تاریخ تصادفی در 6 ماه گذشته (نه همه امروز)
            created_at = random_datetime_within_last_n_months(6)

            tx_batch.append((src["id"], dst["id"], amount, fee, status, description, created_at))

            if len(tx_batch) >= BATCH_TX:
                await conn.executemany(tx_sql, tx_batch)
                tx_batch.clear()

        if tx_batch:
            await conn.executemany(tx_sql, tx_batch)

        print("✅ Seed کامل شد.")

    await close_db_pool()


if __name__ == "__main__":
    asyncio.run(seed())
