from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_financial_health_service
from app.schemas.financial_health import (
    SnapshotResponse,
    SubmitSnapshotRequest,
)
from app.services.financial_health_service import FinancialHealthService

router = APIRouter(
    prefix="/snapshots",
    tags=["snapshots"],
)


@router.post(
    "",
    response_model=SnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new monthly snapshot",
    description=(
        "Submit a new monthly snapshot for a given user that contains "
        "all their expenses and income for the month"
    ),
)
def submit_snapshot(
    request: SubmitSnapshotRequest,
    service: FinancialHealthService = Depends(get_financial_health_service),
) -> SnapshotResponse:
    snapshot = service.submit_snapshot(request=request)
    return SnapshotResponse.model_validate(snapshot)


@router.get(
    "/{user_id}/history",
    response_model=list[SnapshotResponse],
    summary="Get snapshot history for a user",
    description=(
        "Return the most recent monthly snapshots for a user, "
        "ordered by period descending. Limit defaults to 12."
    ),
)
def get_history(
    user_id: UUID,
    service: FinancialHealthService = Depends(get_financial_health_service),
    limit: int = Query(default=12, ge=1, le=12),
) -> list[SnapshotResponse]:
    snapshots = service.get_history(user_id=user_id, limit=limit)
    return [SnapshotResponse.model_validate(snapshot) for snapshot in snapshots]


@router.get(
    "/{user_id}/{period}",
    response_model=SnapshotResponse,
    summary="Get a monthly snapshot for a period",
    description="Return the snapshot for a given user and monthly period.",
)
def get_snapshot(
    user_id: UUID,
    period: date,
    service: FinancialHealthService = Depends(get_financial_health_service),
) -> SnapshotResponse:
    snapshot = service.get_snapshot(user_id=user_id, period=period)
    return SnapshotResponse.model_validate(snapshot)
