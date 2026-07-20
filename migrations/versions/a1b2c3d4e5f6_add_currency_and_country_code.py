"""add currency and country_code columns

Revision ID: a1b2c3d4e5f6
Revises: 8d488d333771
Create Date: 2026-07-20 22:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "8d488d333771"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("country_code", sa.String(length=2), nullable=False, server_default="GB"),
    )
    op.add_column(
        "users",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="GBP"),
    )
    op.create_check_constraint(
        "ck_users_country_code",
        "users",
        "country_code IN ('GB', 'FR', 'US')",
    )
    op.create_check_constraint(
        "ck_users_currency",
        "users",
        "currency IN ('GBP', 'EUR', 'USD')",
    )
    op.alter_column("users", "country_code", server_default=None)
    op.alter_column("users", "currency", server_default=None)

    op.add_column(
        "monthly_snapshots",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="GBP"),
    )
    op.create_check_constraint(
        "ck_monthly_snapshots_currency",
        "monthly_snapshots",
        "currency IN ('GBP', 'EUR', 'USD')",
    )
    op.alter_column("monthly_snapshots", "currency", server_default=None)

    op.add_column(
        "monthly_assessments",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="GBP"),
    )
    op.create_check_constraint(
        "ck_monthly_assessments_currency",
        "monthly_assessments",
        "currency IN ('GBP', 'EUR', 'USD')",
    )
    op.alter_column("monthly_assessments", "currency", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_monthly_assessments_currency", "monthly_assessments", type_="check")
    op.drop_column("monthly_assessments", "currency")

    op.drop_constraint("ck_monthly_snapshots_currency", "monthly_snapshots", type_="check")
    op.drop_column("monthly_snapshots", "currency")

    op.drop_constraint("ck_users_currency", "users", type_="check")
    op.drop_constraint("ck_users_country_code", "users", type_="check")
    op.drop_column("users", "currency")
    op.drop_column("users", "country_code")
