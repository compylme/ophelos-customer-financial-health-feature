from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.exceptions import (
    InvalidHistoryLimit,
    SnapshotAlreadyExists,
    SnapshotNotFound,
)
from app.models.models import Direction, FinancialItem, MonthlySnapshot
from app.repositories.snapshot_repository import SnapshotRepository
from app.schemas.financial_health import (
    AffordabilityStatus,
    FinancialItemInput,
    SubmitSnapshotRequest,
)
from app.services.financial_health_service import FinancialHealthService


@pytest.fixture
def mock_session() -> MagicMock:
    return MagicMock(spec=Session)


@pytest.fixture
def mock_repository() -> MagicMock:
    return MagicMock(spec=SnapshotRepository)


@pytest.fixture
def service(
    mock_session: MagicMock, mock_repository: MagicMock
) -> FinancialHealthService:
    svc = FinancialHealthService(mock_session)
    svc._repository = mock_repository
    return svc


def _items(
    factory: Callable[..., FinancialItemInput],
    income: Decimal,
    expense: Decimal,
) -> list[FinancialItemInput]:
    items: list[FinancialItemInput] = []
    if income > 0:
        items.append(
            factory(
                direction=Direction.INCOME,
                description="Income",
                amount=income,
            )
        )
    if expense > 0:
        items.append(
            factory(
                direction=Direction.EXPENSE,
                description="Expense",
                amount=expense,
            )
        )
    return items


# ---------------------------------------------------------------------------
# calculate_assessment
# ---------------------------------------------------------------------------


class TestCalculateAssessment:
    def test_healthy_status(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("2500"), Decimal("1500"))
        )
        assert result.status == AffordabilityStatus.HEALTHY
        assert result.disposable_income_ratio == Decimal("0.4")

    def test_manageable_status(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("800"))
        )
        assert result.status == AffordabilityStatus.MANAGEABLE
        assert result.disposable_income_ratio == Decimal("0.2")

    def test_critical_when_ratio_below_ten_percent(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("920"))
        )
        assert result.status == AffordabilityStatus.CRITICAL
        assert result.disposable_income_ratio == Decimal("0.08")

    def test_break_even_when_disposable_income_is_zero(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("1000"))
        )
        assert result.status == AffordabilityStatus.BREAK_EVEN
        assert result.disposable_income == Decimal("0")

    def test_deficit_when_disposable_income_is_negative(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("1500"))
        )
        assert result.status == AffordabilityStatus.DEFICIT
        assert result.disposable_income == Decimal("-500")

    def test_deficit_when_zero_income(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        # Zero income is represented as expense-only items (amounts must be > 0).
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("0"), Decimal("500"))
        )
        assert result.status == AffordabilityStatus.DEFICIT
        assert result.total_income == Decimal("0")
        assert result.disposable_income_ratio == Decimal("0")

    def test_deficit_status(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("1500"))
        )
        assert result.status == AffordabilityStatus.DEFICIT
        assert "exceeding your income by" in result.explanation

    def test_break_even_status(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("1000"))
        )
        assert result.status == AffordabilityStatus.BREAK_EVEN
        assert "no surplus" in result.explanation

    def test_deficit_explanation_contains_figures(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("1500"))
        )
        assert "1000" in result.explanation
        assert "1500" in result.explanation
        assert "-500" in result.explanation

    def test_break_even_explanation_contains_figures(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("1000"))
        )
        assert "1000" in result.explanation
        assert "0" in result.explanation

    def test_exactly_ten_percent_is_manageable(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("900"))
        )
        assert result.disposable_income_ratio == Decimal("0.1")
        assert result.status == AffordabilityStatus.MANAGEABLE

    def test_just_below_ten_percent_is_critical(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("10000"), Decimal("9001"))
        )
        assert result.status == AffordabilityStatus.CRITICAL
        assert result.disposable_income_ratio < Decimal("0.10")

    def test_exactly_twenty_five_percent_is_healthy(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("750"))
        )
        assert result.disposable_income_ratio == Decimal("0.25")
        assert result.status == AffordabilityStatus.HEALTHY

    def test_just_below_twenty_five_percent_is_manageable(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("10000"), Decimal("7501"))
        )
        assert result.status == AffordabilityStatus.MANAGEABLE
        assert result.disposable_income_ratio < Decimal("0.25")

    def test_sums_income_and_expenditure_correctly(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        items = [
            financial_item_input_factory(
                direction=Direction.INCOME, description="Salary", amount=Decimal("2000")
            ),
            financial_item_input_factory(
                direction=Direction.INCOME, description="Bonus", amount=Decimal("500")
            ),
            financial_item_input_factory(
                direction=Direction.EXPENSE, description="Rent", amount=Decimal("900")
            ),
            financial_item_input_factory(
                direction=Direction.EXPENSE, description="Food", amount=Decimal("300")
            ),
        ]
        result = service.calculate_assessment(items)
        assert result.total_income == Decimal("2500")
        assert result.total_expenditure == Decimal("1200")

    def test_computes_disposable_income(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("2500"), Decimal("1500"))
        )
        assert result.disposable_income == Decimal("1000")

    def test_explanation_contains_computed_figures(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("2500"), Decimal("1500"))
        )
        assert "2500" in result.explanation
        assert "1500" in result.explanation
        assert "1000" in result.explanation
        assert "40" in result.explanation

    def test_explanation_maps_to_status(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        deficit = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("1500"))
        )
        break_even = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("1000"))
        )
        critical = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("920"))
        )
        manageable = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("1000"), Decimal("800"))
        )
        healthy = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("2500"), Decimal("1500"))
        )

        assert deficit.status == AffordabilityStatus.DEFICIT
        assert "exceeding your income by" in deficit.explanation

        assert break_even.status == AffordabilityStatus.BREAK_EVEN
        assert "no surplus" in break_even.explanation

        assert critical.status == AffordabilityStatus.CRITICAL
        assert "small portion" in critical.explanation

        assert manageable.status == AffordabilityStatus.MANAGEABLE
        assert "moderate portion" in manageable.explanation

        assert healthy.status == AffordabilityStatus.HEALTHY
        assert "substantial portion" in healthy.explanation

    def test_income_only_items(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("2500"), Decimal("0"))
        )
        assert result.total_expenditure == Decimal("0")
        assert result.disposable_income_ratio == Decimal("1")
        assert result.status == AffordabilityStatus.HEALTHY


# ---------------------------------------------------------------------------
# submit_snapshot
# ---------------------------------------------------------------------------


class TestSubmitSnapshot:
    def test_happy_path_returns_snapshot(
        self,
        service: FinancialHealthService,
        mock_session: MagicMock,
        mock_repository: MagicMock,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
    ) -> None:
        mock_repository.exists_for_period.return_value = False
        request = submit_snapshot_request_factory()

        result = service.submit_snapshot(request)

        assert isinstance(result, MonthlySnapshot)
        mock_repository.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_snapshot_period_is_first_of_month(
        self,
        service: FinancialHealthService,
        mock_repository: MagicMock,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
    ) -> None:
        mock_repository.exists_for_period.return_value = False
        request = submit_snapshot_request_factory()

        with patch("app.services.financial_health_service.date") as mock_date:
            mock_date.today.return_value = date(2026, 7, 15)
            result = service.submit_snapshot(request)

        assert result.period == date(2026, 7, 1)

    def test_raises_snapshot_already_exists(
        self,
        service: FinancialHealthService,
        mock_session: MagicMock,
        mock_repository: MagicMock,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
    ) -> None:
        mock_repository.exists_for_period.return_value = True
        request = submit_snapshot_request_factory()

        with pytest.raises(SnapshotAlreadyExists):
            service.submit_snapshot(request)

        mock_repository.add.assert_not_called()
        mock_session.commit.assert_not_called()

    def test_calls_repo_add_before_commit(
        self,
        service: FinancialHealthService,
        mock_session: MagicMock,
        mock_repository: MagicMock,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
    ) -> None:
        mock_repository.exists_for_period.return_value = False
        call_order: list[str] = []
        mock_repository.add.side_effect = lambda _snapshot: call_order.append("add")
        mock_session.commit.side_effect = lambda: call_order.append("commit")

        service.submit_snapshot(submit_snapshot_request_factory())

        assert call_order == ["add", "commit"]
        added = mock_repository.add.call_args.args[0]
        assert isinstance(added, MonthlySnapshot)

    def test_builds_financial_items_from_request(
        self,
        service: FinancialHealthService,
        mock_repository: MagicMock,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        mock_repository.exists_for_period.return_value = False
        items = [
            financial_item_input_factory(
                direction=Direction.INCOME,
                description="Salary",
                amount=Decimal("3000.00"),
            ),
            financial_item_input_factory(
                direction=Direction.EXPENSE,
                description="Rent",
                amount=Decimal("1200.00"),
            ),
        ]
        request = submit_snapshot_request_factory(items=items)

        service.submit_snapshot(request)

        snapshot: MonthlySnapshot = mock_repository.add.call_args.args[0]
        assert len(snapshot.financial_items) == 2
        assert all(isinstance(item, FinancialItem) for item in snapshot.financial_items)
        assert snapshot.financial_items[0].description == "Salary"
        assert snapshot.financial_items[0].amount == Decimal("3000.00")
        assert snapshot.financial_items[1].description == "Rent"
        assert snapshot.financial_items[1].amount == Decimal("1200.00")

    def test_builds_assessment_from_calculation(
        self,
        service: FinancialHealthService,
        mock_repository: MagicMock,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
    ) -> None:
        mock_repository.exists_for_period.return_value = False
        # Default factory: income 2500, expense 1500 -> HEALTHY
        service.submit_snapshot(submit_snapshot_request_factory())

        snapshot: MonthlySnapshot = mock_repository.add.call_args.args[0]
        assert snapshot.assessment is not None
        assert snapshot.assessment.total_income == Decimal("2500.00")
        assert snapshot.assessment.total_expenditure == Decimal("1500.00")
        assert snapshot.assessment.disposable_income == Decimal("1000.00")
        assert snapshot.assessment.status == AffordabilityStatus.HEALTHY.value
        assert "substantial portion" in snapshot.assessment.explanation

    def test_commits_on_success(
        self,
        service: FinancialHealthService,
        mock_session: MagicMock,
        mock_repository: MagicMock,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
    ) -> None:
        mock_repository.exists_for_period.return_value = False

        service.submit_snapshot(submit_snapshot_request_factory())

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    def test_rollback_and_reraise_on_failure(
        self,
        service: FinancialHealthService,
        mock_session: MagicMock,
        mock_repository: MagicMock,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
    ) -> None:
        mock_repository.exists_for_period.return_value = False
        mock_session.commit.side_effect = RuntimeError("db failure")

        with pytest.raises(RuntimeError, match="db failure"):
            service.submit_snapshot(submit_snapshot_request_factory())

        mock_session.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# get_snapshot
# ---------------------------------------------------------------------------


class TestGetSnapshot:
    def test_returns_snapshot_when_found(
        self,
        service: FinancialHealthService,
        mock_repository: MagicMock,
    ) -> None:
        expected = MagicMock(spec=MonthlySnapshot)
        mock_repository.get_by_period.return_value = expected
        user_id = uuid4()
        period = date(2026, 7, 1)

        result = service.get_snapshot(user_id, period)

        assert result is expected

    def test_raises_snapshot_not_found(
        self,
        service: FinancialHealthService,
        mock_repository: MagicMock,
    ) -> None:
        mock_repository.get_by_period.return_value = None

        with pytest.raises(SnapshotNotFound):
            service.get_snapshot(uuid4(), date(2026, 7, 1))

    def test_delegates_to_repository(
        self,
        service: FinancialHealthService,
        mock_repository: MagicMock,
    ) -> None:
        mock_repository.get_by_period.return_value = MagicMock(spec=MonthlySnapshot)
        user_id = uuid4()
        period = date(2026, 7, 1)

        service.get_snapshot(user_id, period)

        mock_repository.get_by_period.assert_called_once_with(user_id, period)


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------


class TestGetHistory:
    def test_returns_history_from_repository(
        self,
        service: FinancialHealthService,
        mock_repository: MagicMock,
    ) -> None:
        expected = [MagicMock(spec=MonthlySnapshot)]
        mock_repository.get_history.return_value = expected
        user_id = uuid4()

        result = service.get_history(user_id, limit=5)

        assert result is expected
        mock_repository.get_history.assert_called_once_with(user_id, 5)

    def test_raises_invalid_limit_when_zero(
        self, service: FinancialHealthService, mock_repository: MagicMock
    ) -> None:
        with pytest.raises(InvalidHistoryLimit):
            service.get_history(uuid4(), limit=0)
        mock_repository.get_history.assert_not_called()

    def test_raises_invalid_limit_when_negative(
        self, service: FinancialHealthService, mock_repository: MagicMock
    ) -> None:
        with pytest.raises(InvalidHistoryLimit):
            service.get_history(uuid4(), limit=-1)
        mock_repository.get_history.assert_not_called()

    def test_raises_invalid_limit_when_above_twelve(
        self, service: FinancialHealthService, mock_repository: MagicMock
    ) -> None:
        with pytest.raises(InvalidHistoryLimit):
            service.get_history(uuid4(), limit=13)
        mock_repository.get_history.assert_not_called()

    def test_accepts_boundary_limits(
        self, service: FinancialHealthService, mock_repository: MagicMock
    ) -> None:
        mock_repository.get_history.return_value = []
        user_id = uuid4()

        service.get_history(user_id, limit=1)
        service.get_history(user_id, limit=12)

        assert mock_repository.get_history.call_count == 2
        mock_repository.get_history.assert_any_call(user_id, 1)
        mock_repository.get_history.assert_any_call(user_id, 12)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_expense_only_items(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            _items(financial_item_input_factory, Decimal("0"), Decimal("500"))
        )
        assert result.total_income == Decimal("0")
        assert result.total_expenditure == Decimal("500")
        assert result.disposable_income == Decimal("-500")
        assert result.disposable_income_ratio == Decimal("0")
        assert result.status == AffordabilityStatus.DEFICIT

    def test_single_item_submission(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        result = service.calculate_assessment(
            [
                financial_item_input_factory(
                    direction=Direction.INCOME,
                    description="Salary",
                    amount=Decimal("2000"),
                )
            ]
        )
        assert result.total_income == Decimal("2000")
        assert result.total_expenditure == Decimal("0")
        assert result.status == AffordabilityStatus.HEALTHY

    def test_many_small_items(
        self,
        service: FinancialHealthService,
        financial_item_input_factory: Callable[..., FinancialItemInput],
    ) -> None:
        items = [
            financial_item_input_factory(
                direction=Direction.INCOME,
                description=f"Income {i}",
                amount=Decimal("100.00"),
            )
            for i in range(15)
        ] + [
            financial_item_input_factory(
                direction=Direction.EXPENSE,
                description=f"Expense {i}",
                amount=Decimal("50.00"),
            )
            for i in range(10)
        ]
        result = service.calculate_assessment(items)
        assert result.total_income == Decimal("1500.00")
        assert result.total_expenditure == Decimal("500.00")
        assert result.disposable_income == Decimal("1000.00")
        assert result.status == AffordabilityStatus.HEALTHY

    def test_submitted_at_is_utc_aware(
        self,
        service: FinancialHealthService,
        mock_repository: MagicMock,
        submit_snapshot_request_factory: Callable[..., SubmitSnapshotRequest],
    ) -> None:
        mock_repository.exists_for_period.return_value = False

        result = service.submit_snapshot(submit_snapshot_request_factory())

        assert isinstance(result.submitted_at, datetime)
        assert result.submitted_at.tzinfo is not None
        assert result.submitted_at.tzinfo == UTC
