"""Shared test fixtures for unit and integration tests.

Repository integration tests require a separate Postgres database (run once):

    CREATE DATABASE financial_assessment_test;
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.models.models import (
    Base,
    Direction,
    FinancialItem,
    MonthlyAssessment,
    MonthlySnapshot,
    User,
)
from app.repositories.snapshot_repository import SnapshotRepository
from app.schemas.financial_health import FinancialItemInput, SubmitSnapshotRequest

# Separate DB on the same Postgres instance — never points at the dev database.
# Override via TEST_DATABASE_URL for CI or non-local Postgres.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://admin@localhost:5432/financial_assessment_test",
)


# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def test_engine() -> Iterator[Engine]:
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    """Per-test session joined to an outer transaction that is always rolled back."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def repository(db_session: Session) -> SnapshotRepository:
    return SnapshotRepository(db_session)


# ---------------------------------------------------------------------------
# Factory fixtures (return callables for configurable variants)
# ---------------------------------------------------------------------------


@pytest.fixture
def user_factory(db_session: Session) -> Callable[..., User]:
    def _create(name: str = "Test User", email: str | None = None) -> User:
        user = User(name=name, email=email or f"{uuid4()}@test.com")
        db_session.add(user)
        db_session.flush()
        return user

    return _create


@pytest.fixture
def financial_item_factory() -> Callable[..., FinancialItem]:
    def _create(
        direction: Direction = Direction.INCOME,
        description: str = "Salary",
        amount: Decimal = Decimal("2500.00"),
    ) -> FinancialItem:
        return FinancialItem(
            direction=direction,
            description=description,
            amount=amount,
        )

    return _create


@pytest.fixture
def financial_item_input_factory() -> Callable[..., FinancialItemInput]:
    def _create(
        direction: Direction = Direction.INCOME,
        description: str = "Salary",
        amount: Decimal = Decimal("2500.00"),
    ) -> FinancialItemInput:
        return FinancialItemInput(
            direction=direction,
            description=description,
            amount=amount,
        )

    return _create


@pytest.fixture
def submit_snapshot_request_factory(
    financial_item_input_factory: Callable[..., FinancialItemInput],
) -> Callable[..., SubmitSnapshotRequest]:
    def _create(
        user_id: UUID | None = None,
        items: list[FinancialItemInput] | None = None,
    ) -> SubmitSnapshotRequest:
        if items is None:
            items = [
                financial_item_input_factory(
                    direction=Direction.INCOME,
                    description="Salary",
                    amount=Decimal("2500.00"),
                ),
                financial_item_input_factory(
                    direction=Direction.EXPENSE,
                    description="Rent",
                    amount=Decimal("1500.00"),
                ),
            ]
        return SubmitSnapshotRequest(
            user_id=user_id or uuid4(),
            items=items,
        )

    return _create


@pytest.fixture
def assessment_factory() -> Callable[..., MonthlyAssessment]:
    def _create(
        total_income: Decimal = Decimal("2500.00"),
        total_expenditure: Decimal = Decimal("1500.00"),
        disposable_income: Decimal | None = None,
        status: str = "HEALTHY",
        explanation: str = "Test explanation",
    ) -> MonthlyAssessment:
        if disposable_income is None:
            disposable_income = total_income - total_expenditure
        return MonthlyAssessment(
            total_income=total_income,
            total_expenditure=total_expenditure,
            disposable_income=disposable_income,
            status=status,
            explanation=explanation,
        )

    return _create


@pytest.fixture
def snapshot_factory(
    db_session: Session,
    financial_item_factory: Callable[..., FinancialItem],
    assessment_factory: Callable[..., MonthlyAssessment],
) -> Callable[..., MonthlySnapshot]:
    def _create(
        user: User,
        period: date = date(2026, 7, 1),
        submitted_at: datetime | None = None,
        financial_items: list[FinancialItem] | None = None,
        assessment: MonthlyAssessment | None = None,
    ) -> MonthlySnapshot:
        if financial_items is None:
            financial_items = [
                financial_item_factory(
                    direction=Direction.INCOME,
                    description="Salary",
                    amount=Decimal("2500.00"),
                ),
                financial_item_factory(
                    direction=Direction.EXPENSE,
                    description="Rent",
                    amount=Decimal("1500.00"),
                ),
            ]
        if assessment is None:
            assessment = assessment_factory()

        snapshot = MonthlySnapshot(
            user_id=user.id,
            period=period,
            submitted_at=submitted_at or datetime.now(UTC),
            financial_items=financial_items,
            assessment=assessment,
        )
        db_session.add(snapshot)
        db_session.flush()
        return snapshot

    return _create


# ---------------------------------------------------------------------------
# Pre-built data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def persisted_user(user_factory: Callable[..., User]) -> User:
    return user_factory()


@pytest.fixture
def second_user(user_factory: Callable[..., User]) -> User:
    return user_factory(name="Second User")


@pytest.fixture
def persisted_snapshot(
    persisted_user: User,
    snapshot_factory: Callable[..., MonthlySnapshot],
) -> MonthlySnapshot:
    return snapshot_factory(user=persisted_user, period=date(2026, 7, 1))


@pytest.fixture
def year_boundary_snapshots(
    persisted_user: User,
    snapshot_factory: Callable[..., MonthlySnapshot],
) -> list[MonthlySnapshot]:
    december = snapshot_factory(user=persisted_user, period=date(2025, 12, 1))
    january = snapshot_factory(user=persisted_user, period=date(2026, 1, 1))
    return [december, january]


@pytest.fixture
def snapshot_history(
    persisted_user: User,
    snapshot_factory: Callable[..., MonthlySnapshot],
) -> list[MonthlySnapshot]:
    """12 monthly snapshots from Aug 2025 through Jul 2026."""
    periods = [
        date(2025, 8, 1),
        date(2025, 9, 1),
        date(2025, 10, 1),
        date(2025, 11, 1),
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
        date(2026, 4, 1),
        date(2026, 5, 1),
        date(2026, 6, 1),
        date(2026, 7, 1),
    ]
    return [snapshot_factory(user=persisted_user, period=period) for period in periods]


@pytest.fixture
def multi_user_snapshots(
    persisted_user: User,
    second_user: User,
    snapshot_factory: Callable[..., MonthlySnapshot],
) -> dict[str, MonthlySnapshot]:
    period = date(2026, 7, 1)
    return {
        "user_a": snapshot_factory(user=persisted_user, period=period),
        "user_b": snapshot_factory(user=second_user, period=period),
    }


@pytest.fixture
def zero_amount_items(
    financial_item_factory: Callable[..., FinancialItem],
) -> list[FinancialItem]:
    """Smallest valid monetary amounts (DB constraint requires amount > 0)."""
    return [
        financial_item_factory(
            direction=Direction.INCOME,
            description="Minimal income",
            amount=Decimal("0.01"),
        ),
        financial_item_factory(
            direction=Direction.EXPENSE,
            description="Minimal expense",
            amount=Decimal("0.01"),
        ),
    ]


@pytest.fixture
def uncommitted_snapshot(
    persisted_user: User,
    financial_item_factory: Callable[..., FinancialItem],
    assessment_factory: Callable[..., MonthlyAssessment],
) -> MonthlySnapshot:
    """Snapshot with children attached but not added to the session."""
    return MonthlySnapshot(
        user_id=persisted_user.id,
        period=date(2026, 7, 1),
        submitted_at=datetime.now(UTC),
        financial_items=[
            financial_item_factory(
                direction=Direction.INCOME,
                description="Salary",
                amount=Decimal("2500.00"),
            ),
            financial_item_factory(
                direction=Direction.EXPENSE,
                description="Rent",
                amount=Decimal("1500.00"),
            ),
        ],
        assessment=assessment_factory(),
    )
