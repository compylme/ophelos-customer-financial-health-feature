from fastapi import FastAPI

from app.api.routes import router
from app.api.errors import register_error_handlers
from app.exceptions import DomainError
from app.api.errors import domain_error_handler

app = FastAPI(
    title="Financial Health API",
    description="API for submitting and retrieving monthly financial assessments.",
    version="0.1.0",
)

app.include_router(router)
app.add_exception_handler(
    DomainError,
    domain_error_handler,
)

@app.get("/")
def index() -> dict[str, str]:
    return {"message": "Financial Health API is running"}