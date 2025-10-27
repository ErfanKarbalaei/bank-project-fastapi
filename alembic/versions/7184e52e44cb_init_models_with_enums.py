"""init models with enums

Revision ID: 7184e52e44cb
Revises: df04dba0206c
Create Date: 2025-10-27 04:20:36.093182
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7184e52e44cb'
down_revision: Union[str, Sequence[str], None] = 'df04dba0206c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- تعریف enum در دیتابیس ---
    transaction_status_enum = sa.Enum(
        'SUCCESS', 'FAILED', 'PENDING',
        name='transactionstatus'
    )
    transaction_status_enum.create(op.get_bind(), checkfirst=True)

    # --- تغییر نوع ستون status با استفاده از USING ---
    op.alter_column(
        'transactions',
        'status',
        existing_type=sa.String(length=20),
        type_=transaction_status_enum,
        nullable=False,
        postgresql_using='status::transactionstatus'
    )

    # --- سایر تغییرات ---
    op.alter_column('cards', 'balance',
        existing_type=sa.NUMERIC(precision=15, scale=2),
        type_=sa.Numeric(precision=18, scale=0),
        nullable=False
    )
    op.alter_column('cards', 'user_id',
        existing_type=sa.INTEGER(),
        nullable=False
    )
    op.drop_constraint(op.f('cards_card_number_key'), 'cards', type_='unique')
    op.create_index(op.f('ix_cards_card_number'), 'cards', ['card_number'], unique=True)
    op.drop_constraint(op.f('users_national_code_key'), 'users', type_='unique')
    op.create_index(op.f('ix_users_national_code'), 'users', ['national_code'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_national_code'), table_name='users')
    op.create_unique_constraint(
        op.f('users_national_code_key'),
        'users', ['national_code'],
        postgresql_nulls_not_distinct=False
    )

    op.alter_column(
        'transactions', 'status',
        existing_type=sa.Enum('SUCCESS', 'FAILED', 'PENDING', name='transactionstatus'),
        type_=sa.VARCHAR(length=20),
        nullable=True,
        postgresql_using='status::text'
    )

    op.drop_index(op.f('ix_cards_card_number'), table_name='cards')
    op.create_unique_constraint(
        op.f('cards_card_number_key'),
        'cards', ['card_number'],
        postgresql_nulls_not_distinct=False
    )
    op.alter_column('cards', 'user_id',
        existing_type=sa.INTEGER(),
        nullable=True
    )
    op.alter_column('cards', 'balance',
        existing_type=sa.Numeric(precision=18, scale=0),
        type_=sa.NUMERIC(precision=15, scale=2),
        nullable=True
    )

    # حذف enum در زمان rollback
    sa.Enum(name='transactionstatus').drop(op.get_bind(), checkfirst=True)
