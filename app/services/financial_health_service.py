import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.exceptions import (
    InvalidHistoryLimit,
    SnapshotAlreadyExists,
    SnapshotNotFound,
)
from app.models.models import (
    Direction,
    FinancialItem,
    MonthlyAssessment,
    MonthlySnapshot,
)
from app.repositories.snapshot_repository import SnapshotRepository
from app.schemas.financial_health import (
    AffordabilityStatus,
    AssessmentResult,
    FinancialItemInput,
    SubmitSnapshotRequest,
)

logger = logging.getLogger(__name__)

CRITICAL_THRESHOLD = Decimal("0.10")
MANAGEABLE_THRESHOLD = Decimal("0.25")

_EXPLANATION_TEMPLATES: dict[AffordabilityStatus, str] = {
    AffordabilityStatus.DEFICIT: (
        "Based on the financial information provided, your total monthly income"
        " is {total_income} and your total monthly expenditure is"
        " {total_expenditure}. This leaves a disposable income of"
        " {disposable_income}, which represents {ratio}% of your income."
        " Your total expenditure currently exceeds your total income."
    ),
    AffordabilityStatus.BREAK_EVEN: (
        "Based on the financial information provided, your total monthly income"
        " is {total_income} and your total monthly expenditure is"
        " {total_expenditure}. This leaves a disposable income of"
        " {disposable_income}, which represents {ratio}% of your income."
        " Your income and expenditure are currently equal, leaving"
        " no surplus for the month."
    ),
    AffordabilityStatus.CRITICAL: (
        "Based on the financial information provided, your total monthly income"
        " is {total_income} and your total monthly expenditure is"
        " {total_expenditure}. This leaves a disposable income of"
        " {disposable_income}, which represents {ratio}% of your income."
        " This indicates that your current financial position may require"
        " immediate attention, as your spending is consuming most"
        " of your income."
    ),
    AffordabilityStatus.MANAGEABLE: (
        "Based on the financial information provided, your total monthly income"
        " is {total_income} and your total monthly expenditure is"
        " {total_expenditure}. This leaves a disposable income of"
        " {disposable_income}, which represents {ratio}% of your income."
        " Your financial position shows some room for flexibility, though"
        " there may be limited capacity to absorb unexpected costs."
    ),
    AffordabilityStatus.HEALTHY: (
        "Based on the financial information provided, your total monthly income"
        " is {total_income} and your total monthly expenditure is"
        " {total_expenditure}. This leaves a disposable income of"
        " {disposable_income}, which represents {ratio}% of your income."
        " Your financial position indicates a healthy balance between income"
        " and expenditure, with capacity to manage variability in costs."
    ),
}


class FinancialHealthService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = SnapshotRepository(session)

    def submit_snapshot(self, request: SubmitSnapshotRequest) -> MonthlySnapshot:
        period = date.today().replace(day=1)

        if self._repository.exists_for_period(request.user_id, period):
            raise SnapshotAlreadyExists(
                f"A snapshot already exists for user {request.user_id}"
                f" for the period {period.strftime('%B %Y')}"
            )

        assessment_result = self.calculate_assessment(request.items)

        snapshot = MonthlySnapshot(
            user_id=request.user_id,
            period=period,
            submitted_at=datetime.now(UTC),
            financial_items=[
                FinancialItem(
                    direction=item.direction,
                    description=item.description,
                    amount=item.amount,
                )
                for item in request.items
            ],
            assessment=MonthlyAssessment(
                total_income=assessment_result.total_income,
                total_expenditure=assessment_result.total_expenditure,
                disposable_income=assessment_result.disposable_income,
                status=assessment_result.status.value,
                explanation=assessment_result.explanation,
            ),
        )

        try:
            self._repository.add(snapshot)
            self._session.commit()
            logger.info(
                "Snapshot submitted for user %s, period %s",
                request.user_id,
                period,
            )
        except Exception:
            self._session.rollback()
            logger.exception(
                "Failed to persist snapshot for user %s, period %s",
                request.user_id,
                period,
            )
            raise

        return snapshot

    def calculate_assessment(
        self, items: list[FinancialItemInput]
    ) -> AssessmentResult:
        total_income = sum(
            (item.amount for item in items if item.direction == Direction.INCOME),
            Decimal("0"),
        )
        total_expenditure = sum(
            (item.amount for item in items if item.direction == Direction.EXPENSE),
            Decimal("0"),
        )

        disposable_income = total_income - total_expenditure

        if total_income > 0:
            disposable_income_ratio = disposable_income / total_income
        else:
            disposable_income_ratio = Decimal("0")

        if disposable_income < 0:
            status = AffordabilityStatus.DEFICIT
        elif disposable_income == 0:
            status = AffordabilityStatus.BREAK_EVEN
        elif disposable_income_ratio < CRITICAL_THRESHOLD:
            status = AffordabilityStatus.CRITICAL
        elif disposable_income_ratio < MANAGEABLE_THRESHOLD:
            status = AffordabilityStatus.MANAGEABLE
        else:
            status = AffordabilityStatus.HEALTHY

        ratio_percentage = (disposable_income_ratio * 100).quantize(Decimal("0.1"))

        explanation = _EXPLANATION_TEMPLATES[status].format(
            total_income=total_income,
            total_expenditure=total_expenditure,
            disposable_income=disposable_income,
            ratio=ratio_percentage,
        )

        return AssessmentResult(
            total_income=total_income,
            total_expenditure=total_expenditure,
            disposable_income=disposable_income,
            disposable_income_ratio=disposable_income_ratio,
            status=status,
            explanation=explanation,
        )

    def get_snapshot(self, user_id: UUID, period: date) -> MonthlySnapshot:
        snapshot = self._repository.get_by_period(user_id, period)
        if snapshot is None:
            raise SnapshotNotFound(
                f"No snapshot found for user {user_id}"
                f" for the period {period.strftime('%B %Y')}"
            )
        return snapshot

    def get_history(
        self, user_id: UUID, limit: int = 12
    ) -> list[MonthlySnapshot]:
        if limit < 1 or limit > 12:
            raise InvalidHistoryLimit(
                f"History limit must be between 1 and 12, got {limit}"
            )
        return self._repository.get_history(user_id, limit)
