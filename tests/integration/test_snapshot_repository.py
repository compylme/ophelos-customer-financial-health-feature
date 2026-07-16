from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models.models import Direction, FinancialItem, MonthlyAssessment, MonthlySnapshot
from app.repositories.snapshot_repository import SnapshotRepository


# ---------------------------------------------------------------------------
# exists_for_period
# ---------------------------------------------------------------------------


class TestExistsForPeriod:
    def test_returns_true_when_snapshot_exists(
        self, repository: SnapshotRepository, persisted_snapshot: MonthlySnapshot
    ) -> None:
        exists = repository.exists_for_period(
            user_id=persisted_snapshot.user_id,
            period=persisted_snapshot.period,
        )
        assert exists is True

    def test_returns_false_when_no_snapshot_exists(
        self, repository: SnapshotRepository, persisted_user
    ) -> None:
        exists = repository.exists_for_period(
            user_id=persisted_user.id,
            period=date(2026, 7, 1),
        )
        assert exists is False

    def test_returns_false_for_different_user(
        self,
        repository: SnapshotRepository,
        persisted_user,
        second_user,
        snapshot_factory,
    ) -> None:
        period = date(2026, 7, 1)
        snapshot_factory(user=second_user, period=period)

        exists = repository.exists_for_period(
            user_id=persisted_user.id,
            period=period,
        )
        assert exists is False

    def test_returns_false_for_different_period(
        self, repository: SnapshotRepository, persisted_snapshot: MonthlySnapshot
    ) -> None:
        exists = repository.exists_for_period(
            user_id=persisted_snapshot.user_id,
            period=date(2020, 1, 1),
        )
        assert exists is False

    def test_distinguishes_year_boundary_periods(
        self,
        repository: SnapshotRepository,
        year_boundary_snapshots: list[MonthlySnapshot],
        persisted_user,
    ) -> None:
        assert repository.exists_for_period(
            user_id=persisted_user.id, period=date(2025, 12, 1)
        ) is True
        assert repository.exists_for_period(
            user_id=persisted_user.id, period=date(2026, 1, 1)
        ) is True
        assert repository.exists_for_period(
            user_id=persisted_user.id, period=date(2025, 11, 1)
        ) is False


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------


class TestAdd:
    def test_persists_snapshot_with_children(
        self,
        repository: SnapshotRepository,
        db_session,
        uncommitted_snapshot: MonthlySnapshot,
    ) -> None:
        repository.add(uncommitted_snapshot)
        db_session.flush()

        result = repository.get_by_period(
            user_id=uncommitted_snapshot.user_id,
            period=uncommitted_snapshot.period,
        )
        assert result is not None
        assert result.id is not None
        assert result.assessment is not None

    def test_cascades_financial_items_and_assessment(
        self,
        repository: SnapshotRepository,
        db_session,
        uncommitted_snapshot: MonthlySnapshot,
    ) -> None:
        expected_item_count = len(uncommitted_snapshot.financial_items)
        repository.add(uncommitted_snapshot)
        db_session.flush()

        result = repository.get_by_period(
            user_id=uncommitted_snapshot.user_id,
            period=uncommitted_snapshot.period,
        )
        assert result is not None
        assert result.assessment is not None
        # financial_items are lazy-loaded; access via relationship
        assert len(result.financial_items) == expected_item_count

        assessment_rows = db_session.scalars(
            select(MonthlyAssessment).where(
                MonthlyAssessment.snapshot_id == result.id
            )
        ).all()
        assert len(assessment_rows) == 1

        item_rows = db_session.scalars(
            select(FinancialItem).where(FinancialItem.snapshot_id == result.id)
        ).all()
        assert len(item_rows) == expected_item_count

    def test_persists_with_minimal_amounts(
        self,
        repository: SnapshotRepository,
        persisted_user,
        snapshot_factory,
        zero_amount_items,
        assessment_factory,
    ) -> None:
        snapshot = snapshot_factory(
            user=persisted_user,
            period=date(2026, 7, 1),
            financial_items=zero_amount_items,
            assessment=assessment_factory(
                total_income=Decimal("0.01"),
                total_expenditure=Decimal("0.01"),
            ),
        )
        result = repository.get_by_period(persisted_user.id, date(2026, 7, 1))
        assert result is not None
        assert result.id == snapshot.id
        assert all(item.amount == Decimal("0.01") for item in result.financial_items)


# ---------------------------------------------------------------------------
# get_by_period
# ---------------------------------------------------------------------------


class TestGetByPeriod:
    def test_returns_snapshot_for_matching_period(
        self, repository: SnapshotRepository, persisted_snapshot: MonthlySnapshot
    ) -> None:
        result = repository.get_by_period(
            user_id=persisted_snapshot.user_id,
            period=persisted_snapshot.period,
        )
        assert result is not None
        assert result.id == persisted_snapshot.id
        assert result.user_id == persisted_snapshot.user_id
        assert result.period == persisted_snapshot.period

    def test_returns_none_when_no_snapshot_exists(
        self, repository: SnapshotRepository, persisted_user
    ) -> None:
        result = repository.get_by_period(
            user_id=persisted_user.id,
            period=date(2026, 7, 1),
        )
        assert result is None

    def test_eagerly_loads_assessment(
        self,
        repository: SnapshotRepository,
        db_session,
        persisted_snapshot: MonthlySnapshot,
    ) -> None:
        result = repository.get_by_period(
            user_id=persisted_snapshot.user_id,
            period=persisted_snapshot.period,
        )
        assert result is not None
        assert result.assessment is not None
        assert result.assessment.assessment == "HEALTHY"

        # Expire the session so subsequent attribute access would trigger a lazy load
        # if the relationship were not already eagerly loaded.
        db_session.expire(result)
        # Re-fetch with eager load to confirm assessment is still available via repo
        reloaded = repository.get_by_period(
            user_id=persisted_snapshot.user_id,
            period=persisted_snapshot.period,
        )
        assert reloaded is not None
        assert reloaded.assessment is not None

    def test_retrieves_december_snapshot(
        self,
        repository: SnapshotRepository,
        year_boundary_snapshots: list[MonthlySnapshot],
        persisted_user,
    ) -> None:
        result = repository.get_by_period(persisted_user.id, date(2025, 12, 1))
        assert result is not None
        assert result.period == date(2025, 12, 1)

    def test_preserves_decimal_precision(
        self,
        repository: SnapshotRepository,
        persisted_user,
        snapshot_factory,
        financial_item_factory,
        assessment_factory,
    ) -> None:
        amount = Decimal("1234.56")
        snapshot_factory(
            user=persisted_user,
            period=date(2026, 7, 1),
            financial_items=[
                financial_item_factory(
                    direction=Direction.INCOME,
                    description="Precise salary",
                    amount=amount,
                )
            ],
            assessment=assessment_factory(
                total_income=amount,
                total_expenditure=Decimal("0.00"),
            ),
        )
        result = repository.get_by_period(persisted_user.id, date(2026, 7, 1))
        assert result is not None
        assert result.assessment is not None
        assert result.assessment.total_income == amount
        assert result.financial_items[0].amount == amount


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------


class TestGetHistory:
    def test_returns_snapshots_in_descending_period_order(
        self,
        repository: SnapshotRepository,
        snapshot_history: list[MonthlySnapshot],
        persisted_user,
    ) -> None:
        results = repository.get_history(persisted_user.id)
        periods = [s.period for s in results]
        assert periods == sorted(periods, reverse=True)

    def test_returns_all_twelve_when_full_history(
        self,
        repository: SnapshotRepository,
        snapshot_history: list[MonthlySnapshot],
        persisted_user,
    ) -> None:
        results = repository.get_history(persisted_user.id)
        assert len(results) == 12

    def test_respects_explicit_limit(
        self,
        repository: SnapshotRepository,
        snapshot_history: list[MonthlySnapshot],
        persisted_user,
    ) -> None:
        results = repository.get_history(persisted_user.id, limit=3)
        assert len(results) == 3

    def test_returns_empty_list_for_user_with_no_snapshots(
        self, repository: SnapshotRepository, persisted_user
    ) -> None:
        results = repository.get_history(persisted_user.id)
        assert results == []

    def test_returns_only_requesting_users_snapshots(
        self,
        repository: SnapshotRepository,
        multi_user_snapshots: dict[str, MonthlySnapshot],
        persisted_user,
        second_user,
    ) -> None:
        history_a = repository.get_history(persisted_user.id)
        history_b = repository.get_history(second_user.id)

        assert len(history_a) == 1
        assert len(history_b) == 1
        assert history_a[0].user_id == persisted_user.id
        assert history_b[0].user_id == second_user.id
        assert history_a[0].id != history_b[0].id

    def test_orders_correctly_across_year_boundary(
        self,
        repository: SnapshotRepository,
        year_boundary_snapshots: list[MonthlySnapshot],
        persisted_user,
    ) -> None:
        results = repository.get_history(persisted_user.id)
        assert len(results) == 2
        assert results[0].period == date(2026, 1, 1)
        assert results[1].period == date(2025, 12, 1)

    def test_eagerly_loads_assessment_on_all_results(
        self,
        repository: SnapshotRepository,
        snapshot_history: list[MonthlySnapshot],
        persisted_user,
    ) -> None:
        results = repository.get_history(persisted_user.id)
        assert len(results) == 12
        for snapshot in results:
            assert snapshot.assessment is not None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_add_snapshot_with_income_only(
        self,
        repository: SnapshotRepository,
        persisted_user,
        snapshot_factory,
        financial_item_factory,
        assessment_factory,
    ) -> None:
        snapshot = snapshot_factory(
            user=persisted_user,
            period=date(2026, 7, 1),
            financial_items=[
                financial_item_factory(
                    direction=Direction.INCOME,
                    description="Salary only",
                    amount=Decimal("3000.00"),
                )
            ],
            assessment=assessment_factory(
                total_income=Decimal("3000.00"),
                total_expenditure=Decimal("0.00"),
            ),
        )
        result = repository.get_by_period(persisted_user.id, date(2026, 7, 1))
        assert result is not None
        assert result.id == snapshot.id
        assert len(result.financial_items) == 1
        assert result.financial_items[0].direction == Direction.INCOME

    def test_add_snapshot_with_expense_only(
        self,
        repository: SnapshotRepository,
        persisted_user,
        snapshot_factory,
        financial_item_factory,
        assessment_factory,
    ) -> None:
        snapshot = snapshot_factory(
            user=persisted_user,
            period=date(2026, 7, 1),
            financial_items=[
                financial_item_factory(
                    direction=Direction.EXPENSE,
                    description="Rent only",
                    amount=Decimal("1200.00"),
                )
            ],
            assessment=assessment_factory(
                total_income=Decimal("0.00"),
                total_expenditure=Decimal("1200.00"),
            ),
        )
        result = repository.get_by_period(persisted_user.id, date(2026, 7, 1))
        assert result is not None
        assert result.id == snapshot.id
        assert len(result.financial_items) == 1
        assert result.financial_items[0].direction == Direction.EXPENSE

    def test_get_history_with_limit_one(
        self,
        repository: SnapshotRepository,
        snapshot_history: list[MonthlySnapshot],
        persisted_user,
    ) -> None:
        results = repository.get_history(persisted_user.id, limit=1)
        assert len(results) == 1
        assert results[0].period == date(2026, 7, 1)

    def test_get_by_period_non_first_of_month(
        self, repository: SnapshotRepository, persisted_snapshot: MonthlySnapshot
    ) -> None:
        result = repository.get_by_period(
            user_id=persisted_snapshot.user_id,
            period=date(2026, 7, 15),
        )
        assert result is None

    def test_add_preserves_large_monetary_values(
        self,
        repository: SnapshotRepository,
        persisted_user,
        snapshot_factory,
        financial_item_factory,
        assessment_factory,
    ) -> None:
        large_amount = Decimal("9999999999.99")
        snapshot_factory(
            user=persisted_user,
            period=date(2026, 7, 1),
            financial_items=[
                financial_item_factory(
                    direction=Direction.INCOME,
                    description="Large income",
                    amount=large_amount,
                )
            ],
            assessment=assessment_factory(
                total_income=large_amount,
                total_expenditure=Decimal("0.00"),
            ),
        )
        result = repository.get_by_period(persisted_user.id, date(2026, 7, 1))
        assert result is not None
        assert result.assessment is not None
        assert result.assessment.total_income == large_amount
        assert result.financial_items[0].amount == large_amount
