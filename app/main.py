from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.errors import domain_error_handler
from app.api.routes import router
from app.db.seed import seed_database
from app.exceptions import DomainError


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_database()
    yield


app = FastAPI(
    title="Financial Health API",
    description="API for submitting and retrieving monthly financial assessments.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
app.add_exception_handler(
    DomainError,
    domain_error_handler,
)


@app.get("/")
def index() -> dict[str, str]:
    return {"message": "Financial Health API is running"}


@app.get("/demo", response_class=HTMLResponse, include_in_schema=False)
def demo() -> HTMLResponse:
    html_path = Path(__file__).parent / "static" / "demo.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))
