# app/db/base.py
from sqlalchemy.orm import declarative_base

# تعریف Base برای استفاده در مدل‌های ORM (فقط برای Alembic)
Base = declarative_base()