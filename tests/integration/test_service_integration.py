"""Service-layer integration tests against the real Postgres test database.

These exercise FinancialHealthService with a live session and repository —
no mocks of either layer.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    Direction,
    FinancialItem,
    MonthlyAssessment,
    MonthlySnapshot,
    User,
)
from app.schemas.financial_health import FinancialItemInput, SubmitSnapshotRequest
from app.services.financial_health_service import FinancialHealthService


@pytest.fixture
def service(db_session: Session) -> FinancialHealthService:
    return FinancialHealthService(db_session)


# ---------------------------------------------------------------------------
# submit_snapshot
# ---------------------------------------------------------------------------


class TestSubmitSnapshot:
    def test_persists_snapshot_with_children_and_assessment(
        self,
        service: FinancialHealthService,
        db_session: Session,
        persisted_user: User,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
    ) -> None:
        request = submit_snapshot_request_factory(user_id=persisted_user.id)

        result = service.submit_snapshot(request)

        snapshots = db_session.scalars(
            select(MonthlySnapshot).where(MonthlySnapshot.user_id == persisted_user.id)
        ).all()
        assert len(snapshots) == 1
        assert snapshots[0].id == result.id
        assert snapshots[0].period == date.today().replace(day=1)

        items = db_session.scalars(
            select(FinancialItem).where(FinancialItem.snapshot_id == result.id)
        ).all()
        assert len(items) == len(request.items)
        item_by_description = {item.description: item for item in items}
        for expected in request.items:
            persisted = item_by_description[expected.description]
            assert persisted.direction == expected.direction
            assert persisted.amount == expected.amount

        assessments = db_session.scalars(
            select(MonthlyAssessment).where(
                MonthlyAssessment.snapshot_id == result.id
            )
        ).all()
        assert len(assessments) == 1
        assert assessments[0].total_income == Decimal("2500.00")
        assert assessments[0].total_expenditure == Decimal("1500.00")
        assert assessments[0].disposable_income == Decimal("1000.00")
        assert assessments[0].status == "HEALTHY"

    def test_returned_snapshot_matches_persisted_data(
        self,
        service: FinancialHealthService,
        persisted_user: User,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
    ) -> None:
        request = submit_snapshot_request_factory(user_id=persisted_user.id)

        returned = service.submit_snapshot(request)
        reloaded = service.get_snapshot(returned.user_id, returned.period)

        assert reloaded.id == returned.id
        assert reloaded.user_id == returned.user_id
        assert reloaded.period == returned.period

        assert len(reloaded.financial_items) == len(returned.financial_items)
        returned_items = sorted(
            returned.financial_items, key=lambda item: item.description
        )
        reloaded_items = sorted(
            reloaded.financial_items, key=lambda item: item.description
        )
        for returned_item, reloaded_item in zip(
            returned_items, reloaded_items, strict=True
        ):
            assert reloaded_item.direction == returned_item.direction
            assert reloaded_item.description == returned_item.description
            assert reloaded_item.amount == returned_item.amount

        assert reloaded.assessment is not None
        assert returned.assessment is not None
        assert reloaded.assessment.total_income == returned.assessment.total_income
        assert (
            reloaded.assessment.total_expenditure
            == returned.assessment.total_expenditure
        )
        assert (
            reloaded.assessment.disposable_income
            == returned.assessment.disposable_income
        )
        assert reloaded.assessment.status == returned.assessment.status
        assert reloaded.assessment.explanation == returned.assessment.explanation

    def test_rollback_on_commit_failure_leaves_no_partial_state(
        self,
        service: FinancialHealthService,
        db_session: Session,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
    ) -> None:
        # Default factory uses a random user_id that does not exist — FK violation.
        request = submit_snapshot_request_factory()

        with pytest.raises(IntegrityError):
            service.submit_snapshot(request)

        assert db_session.scalar(select(func.count()).select_from(MonthlySnapshot)) == 0
        assert db_session.scalar(select(func.count()).select_from(FinancialItem)) == 0
        assert (
            db_session.scalar(select(func.count()).select_from(MonthlyAssessment)) == 0
        )

    def test_deficit_assessment_persists_correctly(
        self,
        service: FinancialHealthService,
        db_session: Session,
        persisted_user: User,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        request = submit_snapshot_request_factory(
            user_id=persisted_user.id,
            items=[
                financial_item_input_factory(
                    direction=Direction.INCOME,
                    description="Salary",
                    amount=Decimal("1000.00"),
                ),
                financial_item_input_factory(
                    direction=Direction.EXPENSE,
                    description="Rent",
                    amount=Decimal("1500.00"),
                ),
            ],
        )

        result = service.submit_snapshot(request)

        assessment = db_session.scalar(
            select(MonthlyAssessment).where(
                MonthlyAssessment.snapshot_id == result.id
            )
        )
        assert assessment is not None
        assert assessment.status == "DEFICIT"
        assert assessment.disposable_income == Decimal("-500.00")
        assert "exceeding your income by" in assessment.explanation
        assert result.assessment is not None
        assert result.assessment.status == "DEFICIT"


# ---------------------------------------------------------------------------
# get_snapshot
# ---------------------------------------------------------------------------


class TestGetSnapshot:
    def test_returns_complete_aggregate(
        self,
        service: FinancialHealthService,
        persisted_user: User,
        snapshot_factory: Callable[..., MonthlySnapshot],
    ) -> None:
        period = date(2026, 7, 1)
        seeded = snapshot_factory(user=persisted_user, period=period)

        result = service.get_snapshot(persisted_user.id, period)

        assert result.id == seeded.id
        assert result.period == period
        assert result.user_id == persisted_user.id

        assert result.assessment is not None
        assert result.assessment.total_income == Decimal("2500.00")
        assert result.assessment.total_expenditure == Decimal("1500.00")
        assert result.assessment.disposable_income == Decimal("1000.00")
        assert result.assessment.status == "HEALTHY"

        assert len(result.financial_items) == 2
        items_by_direction = {item.direction: item for item in result.financial_items}
        assert items_by_direction[Direction.INCOME].amount == Decimal("2500.00")
        assert items_by_direction[Direction.INCOME].description == "Salary"
        assert items_by_direction[Direction.EXPENSE].amount == Decimal("1500.00")
        assert items_by_direction[Direction.EXPENSE].description == "Rent"


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------


class TestGetHistory:
    def test_returns_correct_user_data_in_descending_order(
        self,
        service: FinancialHealthService,
        user_factory: Callable[..., User],
        snapshot_factory: Callable[..., MonthlySnapshot],
    ) -> None:
        user_a = user_factory(name="User A")
        user_b = user_factory(name="User B")

        snapshot_factory(user=user_a, period=date(2025, 11, 1))
        snapshot_factory(user=user_a, period=date(2025, 12, 1))
        snapshot_factory(user=user_a, period=date(2026, 1, 1))
        snapshot_factory(user=user_b, period=date(2025, 12, 1))

        history_a = service.get_history(user_a.id)
        history_b = service.get_history(user_b.id)

        assert len(history_a) == 3
        assert [snapshot.period for snapshot in history_a] == [
            date(2026, 1, 1),
            date(2025, 12, 1),
            date(2025, 11, 1),
        ]
        assert all(snapshot.user_id == user_a.id for snapshot in history_a)

        assert len(history_b) == 1
        assert history_b[0].period == date(2025, 12, 1)
        assert history_b[0].user_id == user_b.id
        assert history_a[1].id != history_b[0].id
