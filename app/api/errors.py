from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status

from app.exceptions import (
    DomainError,
    InvalidFinancialItems,
    InvalidHistoryLimit,
    SnapshotAlreadyExists,
    SnapshotNotFound,
    UserNotFound,
)

DOMAIN_STATUS_CODES: dict[type[DomainError], int] = {
    SnapshotAlreadyExists: status.HTTP_409_CONFLICT,
    SnapshotNotFound: status.HTTP_404_NOT_FOUND,
    InvalidFinancialItems: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidHistoryLimit: status.HTTP_422_UNPROCESSABLE_CONTENT,
    UserNotFound: status.HTTP_404_NOT_FOUND,
}


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = DOMAIN_STATUS_CODES.get(type(exc), status.HTTP_400_BAD_REQUEST)
    return JSONResponse(status_code=status_code, content={"detail": exc.message})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
