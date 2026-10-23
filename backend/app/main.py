import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import APIRouter, FastAPI
from sqlalchemy import text

from app.api import applications, backoffice, companies, products
from app.config import settings
from app.db import engine
from app.pipeline import resume_unfinished

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        resume_unfinished()
    except Exception:
        logging.exception("не удалось подхватить незаконченные заявки")
    yield


app = FastAPI(
    title="Умный кредитный кабинет — API",
    version="0.2.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
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


api.include_router(products.router)
api.include_router(companies.router)
api.include_router(applications.router)
api.include_router(backoffice.router)

app.include_router(api)
