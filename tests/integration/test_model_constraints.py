"""Database / schema constraint enforcement tests.

These assert Postgres enforces model rules (unique keys, CHECKs).
They do not exercise SnapshotRepository.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import Direction, MonthlySnapshot, User


class TestMonthlySnapshotUniqueConstraint:
    def test_rejects_duplicate_user_period(
        self,
        db_session: Session,
        persisted_snapshot: MonthlySnapshot,
        snapshot_factory,
        persisted_user,
    ) -> None:
        with pytest.raises(IntegrityError):
            snapshot_factory(
                user=persisted_user,
                period=persisted_snapshot.period,
            )
            db_session.flush()

    def test_allows_same_period_for_different_users(
        self,
        persisted_user,
        second_user,
        snapshot_factory,
    ) -> None:
        period = date(2026, 7, 1)
        snapshot_a = snapshot_factory(user=persisted_user, period=period)
        snapshot_b = snapshot_factory(user=second_user, period=period)

        assert snapshot_a.id != snapshot_b.id
        assert snapshot_a.user_id == persisted_user.id
        assert snapshot_b.user_id == second_user.id
        assert snapshot_a.period == snapshot_b.period == period


class TestFinancialItemAmountCheckConstraint:
    def test_rejects_zero_amount(
        self,
        db_session: Session,
        persisted_user,
        snapshot_factory,
        financial_item_factory,
        assessment_factory,
    ) -> None:
        with pytest.raises(IntegrityError):
            snapshot_factory(
                user=persisted_user,
                period=date(2026, 7, 1),
                financial_items=[
                    financial_item_factory(
                        direction=Direction.INCOME,
                        description="Invalid",
                        amount=Decimal("0"),
                    )
                ],
                assessment=assessment_factory(
                    total_income=Decimal("0"),
                    total_expenditure=Decimal("0"),
                ),
            )
            db_session.flush()

    def test_rejects_negative_amount(
        self,
        db_session: Session,
        persisted_user,
        snapshot_factory,
        financial_item_factory,
        assessment_factory,
    ) -> None:
        with pytest.raises(IntegrityError):
            snapshot_factory(
                user=persisted_user,
                period=date(2026, 7, 1),
                financial_items=[
                    financial_item_factory(
                        direction=Direction.INCOME,
                        description="Invalid negative",
                        amount=Decimal("-0.01"),
                    )
                ],
                assessment=assessment_factory(
                    total_income=Decimal("-0.01"),
                    total_expenditure=Decimal("0"),
                ),
            )
            db_session.flush()


class TestUserCurrencyConstraint:
    def test_rejects_unsupported_currency(
        self,
        db_session: Session,
    ) -> None:
        with pytest.raises(IntegrityError):
            db_session.add(
                User(
                    name="Bad Currency User",
                    email=f"{uuid4()}@test.com",
                    country_code="GB",
                    currency="XXX",
                )
            )
            db_session.flush()


class TestUserCountryCodeConstraint:
    def test_rejects_unsupported_country_code(
        self,
        db_session: Session,
    ) -> None:
        with pytest.raises(IntegrityError):
            db_session.add(
                User(
                    name="Bad Country User",
                    email=f"{uuid4()}@test.com",
                    country_code="ZZ",
                    currency="GBP",
                )
            )
            db_session.flush()


class TestSnapshotCurrencyConstraint:
    def test_rejects_unsupported_currency(
        self,
        db_session: Session,
        persisted_user,
        snapshot_factory,
        assessment_factory,
    ) -> None:
        with pytest.raises(IntegrityError):
            snapshot_factory(
                user=persisted_user,
                period=date(2026, 8, 1),
                currency="XXX",
                assessment=assessment_factory(currency="GBP"),
            )
            db_session.flush()


class TestAssessmentCurrencyConstraint:
    def test_rejects_unsupported_currency(
        self,
        db_session: Session,
        persisted_user,
        snapshot_factory,
        assessment_factory,
    ) -> None:
        with pytest.raises(IntegrityError):
            snapshot_factory(
                user=persisted_user,
                period=date(2026, 8, 1),
                assessment=assessment_factory(currency="XXX"),
            )
            db_session.flush()
