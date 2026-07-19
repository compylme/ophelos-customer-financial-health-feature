"""Wipe and seed the demo database with a user and 11 months of history."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from app.db.session import SessionFactory, engine
from app.models.models import (
    Base,
    Direction,
    FinancialItem,
    MonthlyAssessment,
    MonthlySnapshot,
    User,
)
from app.schemas.financial_health import FinancialItemInput
from app.services.financial_health_service import FinancialHealthService

logger = logging.getLogger(__name__)

DEMO_USER_ID = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
DEMO_USER_NAME = "Demo User"
DEMO_USER_EMAIL = "demo@ophelos.com"

# Month offsets from oldest (11 months ago) to newest (1 month ago).
# Amounts tell a story: healthy start → dip → critical stretch → recovery.
_MONTHLY_ITEMS: list[list[FinancialItemInput]] = [
    # Month 1 — HEALTHY
    [
        FinancialItemInput(
            direction=Direction.INCOME, description="Salary", amount=Decimal("3200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE, description="Rent", amount=Decimal("1200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Groceries",
            amount=Decimal("350.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Transport",
            amount=Decimal("120.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Subscriptions",
            amount=Decimal("45.00"),
        ),
    ],
    # Month 2 — HEALTHY
    [
        FinancialItemInput(
            direction=Direction.INCOME, description="Salary", amount=Decimal("3200.00")
        ),
        FinancialItemInput(
            direction=Direction.INCOME,
            description="Freelance work",
            amount=Decimal("400.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE, description="Rent", amount=Decimal("1200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Utilities",
            amount=Decimal("140.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Groceries",
            amount=Decimal("380.00"),
        ),
    ],
    # Month 3 — HEALTHY
    [
        FinancialItemInput(
            direction=Direction.INCOME, description="Salary", amount=Decimal("3200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE, description="Rent", amount=Decimal("1200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Groceries",
            amount=Decimal("400.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Transport",
            amount=Decimal("130.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Utilities",
            amount=Decimal("160.00"),
        ),
    ],
    # Month 4 — MANAGEABLE (~18% disposable)
    [
        FinancialItemInput(
            direction=Direction.INCOME, description="Salary", amount=Decimal("3200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE, description="Rent", amount=Decimal("1200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Groceries",
            amount=Decimal("520.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Medical expenses",
            amount=Decimal("650.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Utilities",
            amount=Decimal("250.00"),
        ),
    ],
    # Month 5 — BREAK_EVEN (income equals expenditure)
    [
        FinancialItemInput(
            direction=Direction.INCOME, description="Salary", amount=Decimal("3200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE, description="Rent", amount=Decimal("1200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Groceries",
            amount=Decimal("800.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Transport",
            amount=Decimal("600.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Subscriptions",
            amount=Decimal("600.00"),
        ),
    ],
    # Month 6 — CRITICAL (income drop, ~5% disposable)
    [
        FinancialItemInput(
            direction=Direction.INCOME, description="Salary", amount=Decimal("2200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE, description="Rent", amount=Decimal("1200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Groceries",
            amount=Decimal("500.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Utilities",
            amount=Decimal("220.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Transport",
            amount=Decimal("180.00"),
        ),
    ],
    # Month 7 — DEFICIT (expenditure exceeds income)
    [
        FinancialItemInput(
            direction=Direction.INCOME, description="Salary", amount=Decimal("2200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE, description="Rent", amount=Decimal("1200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Groceries",
            amount=Decimal("480.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Medical expenses",
            amount=Decimal("450.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Utilities",
            amount=Decimal("200.00"),
        ),
    ],
    # Month 8 — MANAGEABLE (starting recovery, ~17% disposable)
    [
        FinancialItemInput(
            direction=Direction.INCOME, description="Salary", amount=Decimal("2800.00")
        ),
        FinancialItemInput(
            direction=Direction.INCOME,
            description="Freelance work",
            amount=Decimal("200.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE, description="Rent", amount=Decimal("1200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Groceries",
            amount=Decimal("480.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Utilities",
            amount=Decimal("320.00"),
        ),
    ],
    # Month 9 — MANAGEABLE (~20% disposable)
    [
        FinancialItemInput(
            direction=Direction.INCOME, description="Salary", amount=Decimal("3000.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE, description="Rent", amount=Decimal("1200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Groceries",
            amount=Decimal("450.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Transport",
            amount=Decimal("300.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Subscriptions",
            amount=Decimal("250.00"),
        ),
    ],
    # Month 10 — HEALTHY
    [
        FinancialItemInput(
            direction=Direction.INCOME, description="Salary", amount=Decimal("3200.00")
        ),
        FinancialItemInput(
            direction=Direction.INCOME,
            description="Freelance work",
            amount=Decimal("350.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE, description="Rent", amount=Decimal("1200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Groceries",
            amount=Decimal("360.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Utilities",
            amount=Decimal("145.00"),
        ),
    ],
    # Month 11 — HEALTHY (most recent prior month)
    [
        FinancialItemInput(
            direction=Direction.INCOME, description="Salary", amount=Decimal("3200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE, description="Rent", amount=Decimal("1200.00")
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Groceries",
            amount=Decimal("340.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Transport",
            amount=Decimal("110.00"),
        ),
        FinancialItemInput(
            direction=Direction.EXPENSE,
            description="Subscriptions",
            amount=Decimal("40.00"),
        ),
    ],
]


def _historic_periods(count: int = 11) -> list[date]:
    """Return the first day of each of the `count` months before the current month."""
    year = date.today().year
    month = date.today().month
    periods: list[date] = []
    for _ in range(count):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
        periods.append(date(year, month, 1))
    periods.reverse()
    return periods


def seed_database() -> None:
    """Wipe the database and seed a demo user with 11 months of snapshots."""
    logger.info("Seeding demo database...")

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    session = SessionFactory()
    try:
        user = User(
            id=DEMO_USER_ID,
            name=DEMO_USER_NAME,
            email=DEMO_USER_EMAIL,
        )
        session.add(user)
        session.flush()

        service = FinancialHealthService(session)
        periods = _historic_periods(len(_MONTHLY_ITEMS))

        for period, items in zip(periods, _MONTHLY_ITEMS, strict=True):
            assessment_result = service.calculate_assessment(items)
            snapshot = MonthlySnapshot(
                user_id=user.id,
                period=period,
                submitted_at=datetime(
                    period.year, period.month, 15, 10, 0, 0, tzinfo=UTC
                ),
                financial_items=[
                    FinancialItem(
                        direction=item.direction,
                        description=item.description,
                        amount=item.amount,
                    )
                    for item in items
                ],
                assessment=MonthlyAssessment(
                    total_income=assessment_result.total_income,
                    total_expenditure=assessment_result.total_expenditure,
                    disposable_income=assessment_result.disposable_income,
                    status=assessment_result.status.value,
                    explanation=assessment_result.explanation,
                ),
            )
            session.add(snapshot)

        session.commit()
        logger.info(
            "Seeded demo user %s (%s) with %d historic snapshots",
            DEMO_USER_EMAIL,
            DEMO_USER_ID,
            len(_MONTHLY_ITEMS),
        )
    except Exception:
        session.rollback()
        logger.exception("Failed to seed demo database")
        raise
    finally:
        session.close()
