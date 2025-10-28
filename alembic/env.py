from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context

from app.db.base import Base
from app.db.models.user_model import User
from app.db.models.card_model import Card
from app.db.models.transaction_model import Transaction
from app.core.config import settings

# Alembic Config object
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata برای Auto-generate
target_metadata = Base.metadata

# ✅ نکته مهم: Alembic از engine معمولی استفاده می‌کند (نه async)
# چون create_async_engine با psycopg2 کار نمی‌کند.
DATABASE_URL = settings.database_url.replace("+asyncpg", "")  # در صورت وجود asyncpg حذف می‌شود


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode (sync engine for Alembic)."""
    connectable = create_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
