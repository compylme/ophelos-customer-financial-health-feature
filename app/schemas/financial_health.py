import enum
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.models import Direction


class AffordabilityStatus(enum.Enum):
    CRITICAL = "CRITICAL"
    MANAGEABLE = "MANAGEABLE"
    HEALTHY = "HEALTHY"


class FinancialItemInput(BaseModel):
    direction: Direction
    description: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)


class SubmitSnapshotRequest(BaseModel):
    user_id: UUID
    items: list[FinancialItemInput] = Field(min_length=1)


class AssessmentResult(BaseModel):
    total_income: Decimal
    total_expenditure: Decimal
    disposable_income: Decimal
    disposable_income_ratio: Decimal
    status: AffordabilityStatus
    explanation: str
