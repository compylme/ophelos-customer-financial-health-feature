from datetime import date
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, selectinload

from app.models.models import MonthlySnapshot

MAX_HISTORY_LIMIT = 12


class SnapshotRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def exists_for_period(self, user_id: UUID, period: date) -> bool:
        stmt = select(
            exists(
                select(MonthlySnapshot.id).where(
                    MonthlySnapshot.user_id == user_id,
                    MonthlySnapshot.period == period,
                )
            )
        )
        return self._session.scalar(stmt) or False

    def add(self, snapshot: MonthlySnapshot) -> None:
        self._session.add(snapshot)

    def get_by_period(self, user_id: UUID, period: date) -> MonthlySnapshot | None:
        stmt = (
            select(MonthlySnapshot)
            .where(
                MonthlySnapshot.user_id == user_id,
                MonthlySnapshot.period == period,
            )
            .options(selectinload(MonthlySnapshot.assessment))
        )
        return self._session.scalar(stmt)

    def get_history(
        self, user_id: UUID, limit: int = MAX_HISTORY_LIMIT
    ) -> list[MonthlySnapshot]:
        limit = min(limit, MAX_HISTORY_LIMIT)
        stmt = (
            select(MonthlySnapshot)
            .where(MonthlySnapshot.user_id == user_id)
            .order_by(MonthlySnapshot.period.desc())
            .limit(limit)
            .options(selectinload(MonthlySnapshot.assessment))
        )
        return list(self._session.scalars(stmt).all())
