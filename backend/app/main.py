import httpx
from fastapi import APIRouter, FastAPI
from sqlalchemy import text

from app.config import settings
from app.db import engine

app = FastAPI(
    title="Умный кредитный кабинет — API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

api = APIRouter(prefix="/api")


@api.get("/health", tags=["service"])
def health() -> dict:
    """Жив ли бэкенд и видит ли он БД и моки."""
    status = {"backend": "ok", "db": "ok", "mocks": "ok"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        status["db"] = "unavailable"
    try:
        httpx.get(f"{settings.mocks_url}/health", timeout=2).raise_for_status()
    except Exception:
        status["mocks"] = "unavailable"
    return status


app.include_router(api)
