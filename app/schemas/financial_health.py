from datetime import date, datetime
import enum
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import Direction


class AffordabilityStatus(enum.Enum):
    DEFICIT = "DEFICIT"
    BREAK_EVEN = "BREAK_EVEN"
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

#API response schemas

class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_income: Decimal
    total_expenditure: Decimal
    disposable_income: Decimal
    explanation: str
    currency: str

class SnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    period: date
    submitted_at: datetime
    currency: str
    assessment: AssessmentResponse
