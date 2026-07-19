from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import SessionFactory
from app.repositories.snapshot_repository import SnapshotRepository
from app.services.financial_health_service import FinancialHealthService


def get_db_session() -> Iterator[Session]:
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()


def get_financial_health_service(
    session: Session = Depends(get_db_session),
) -> FinancialHealthService:
    return FinancialHealthService(session)
