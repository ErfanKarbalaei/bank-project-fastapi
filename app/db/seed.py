import asyncio
import random
from faker import Faker
from tqdm import tqdm
from datetime import datetime, timedelta

from app.db.session import async_session
from app.db.models.user_model import User
from app.db.models.card_model import Card
from app.db.models.transaction_model import Transaction
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

fake = Faker("fa_IR")  # داده فارسی، برای تنوع می‌تونی en_US هم بذاری


async def seed_data():
    async with async_session() as session:  # type: AsyncSession

        print("🧍‍♂️ Creating users...")
        users = []
        for _ in range(50):  # مثلاً ۵۰ کاربر بسازیم
            users.append(
                User(
                    national_code=str(fake.unique.random_number(digits=10)).zfill(10),
                    full_name=fake.name(),
                    phone_number=fake.phone_number(),
                    email=fake.email(),
                    birth_date=fake.date_of_birth(minimum_age=18, maximum_age=60),
                    is_active=True,
                    hashed_password=fake.password(length=12)
                )
            )
        session.add_all(users)
        await session.commit()

        # دریافت کاربران
        result = await session.execute(select(User))
        users = result.scalars().all()

        print("💳 Creating cards...")
        cards = []
        for user in users:
            for _ in range(random.randint(1, 3)):  # هر کاربر بین ۱ تا ۳ کارت
                cards.append(
                    Card(
                        user_id=user.id,
                        card_number=fake.unique.credit_card_number(),
                        cvv2=f"{random.randint(100,9999)}",
                        expire_date=f"{random.randint(1,12):02d}/{random.randint(25,30)}",
                        balance=random.uniform(1_000_000, 50_000_000),
                        is_active=True,
                    )
                )

        session.add_all(cards)
        await session.commit()

        result = await session.execute(select(Card))
        cards = result.scalars().all()

        print("💰 Creating transactions (this may take a bit)...")
        transactions = []

        for _ in tqdm(range(100_000), desc="Generating transactions"):
            source_card = random.choice(cards)
            dest_card = random.choice(cards)
            while dest_card.id == source_card.id:
                dest_card = random.choice(cards)

            amount = round(random.uniform(10_000, 5_000_000), 2)
            fee = round(amount * 0.01, 2)  # مثلاً ۱٪ کارمزد

            transactions.append(
                Transaction(
                    source_card_id=source_card.id,
                    dest_card_id=dest_card.id,
                    amount=amount,
                    fee=fee,
                    status=random.choice(["SUCCESS", "FAILED", "PENDING"]),
                    description=fake.sentence(nb_words=6),
                    created_at=fake.date_time_between(
                        start_date="-6M", end_date="now"
                    ),
                )
            )

            # هر 2000 تراکنش رو ذخیره می‌کنیم برای سرعت و حافظه
            if len(transactions) >= 2000:
                session.add_all(transactions)
                await session.commit()
                transactions.clear()

        # ذخیره‌ی باقیمانده‌ها
        if transactions:
            session.add_all(transactions)
            await session.commit()

        print("✅ Seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
