"""Shared test fixtures for unit and integration tests.

Repository integration tests require a separate Postgres database (run once):

    CREATE DATABASE financial_assessment_test;
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.api.dependencies import get_financial_health_service
from app.main import app
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
from app.services.financial_health_service import FinancialHealthService

# Separate DB on the same Postgres instance — never points at the dev database.
# Override via TEST_DATABASE_URL for CI or non-local Postgres.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://admin@localhost:5432/financial_assessment_test",
)

# Deterministic values for in-memory API route fixtures.
API_USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
API_SNAPSHOT_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
API_INCOME_ITEM_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
API_EXPENSE_ITEM_ID = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
API_ASSESSMENT_ID = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
API_PERIOD = date(2026, 7, 1)
API_SUBMITTED_AT = datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC)


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


# ---------------------------------------------------------------------------
# API route test fixtures (no database)
# ---------------------------------------------------------------------------


@pytest.fixture
def in_memory_snapshot_factory() -> Callable[..., MonthlySnapshot]:
    """Build a fully-populated MonthlySnapshot without a database session."""

    def _create(
        *,
        snapshot_id: UUID = API_SNAPSHOT_ID,
        user_id: UUID = API_USER_ID,
        period: date = API_PERIOD,
    ) -> MonthlySnapshot:
        return MonthlySnapshot(
            id=snapshot_id,
            user_id=user_id,
            period=period,
            submitted_at=API_SUBMITTED_AT,
            financial_items=[
                FinancialItem(
                    id=API_INCOME_ITEM_ID,
                    snapshot_id=snapshot_id,
                    direction=Direction.INCOME,
                    description="Salary",
                    amount=Decimal("2500.00"),
                ),
                FinancialItem(
                    id=API_EXPENSE_ITEM_ID,
                    snapshot_id=snapshot_id,
                    direction=Direction.EXPENSE,
                    description="Rent",
                    amount=Decimal("1500.00"),
                ),
            ],
            assessment=MonthlyAssessment(
                id=API_ASSESSMENT_ID,
                snapshot_id=snapshot_id,
                total_income=Decimal("2500.00"),
                total_expenditure=Decimal("1500.00"),
                disposable_income=Decimal("1000.00"),
                status="HEALTHY",
                explanation="Test explanation",
            ),
        )

    return _create


@pytest.fixture
def sample_snapshot(
    in_memory_snapshot_factory: Callable[..., MonthlySnapshot],
) -> MonthlySnapshot:
    return in_memory_snapshot_factory()


@pytest.fixture
def valid_submit_payload_factory() -> Callable[..., dict]:
    def _create(user_id: UUID = API_USER_ID) -> dict:
        return {
            "user_id": str(user_id),
            "items": [
                {
                    "direction": "INCOME",
                    "description": "Salary",
                    "amount": "2500.00",
                },
                {
                    "direction": "EXPENSE",
                    "description": "Rent",
                    "amount": "1500.00",
                },
            ],
        }

    return _create


@pytest.fixture
def mock_service() -> MagicMock:
    return MagicMock(spec=FinancialHealthService)


@pytest.fixture
def client(mock_service: MagicMock) -> Iterator[TestClient]:
    app.dependency_overrides[get_financial_health_service] = lambda: mock_service
    with patch("app.main.seed_database"):
        with TestClient(app) as test_client:
            yield test_client
    app.dependency_overrides.clear()
