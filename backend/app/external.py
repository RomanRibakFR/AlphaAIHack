"""Обращения к внешним источникам (моки). Порядок фиксирован: сначала компания, потом кредитная история."""
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from app.config import settings

SOURCES = ["egrul", "fns", "zsk", "bank", "gir_bo", "bki"]
COMPANY_SOURCES = SOURCES[:-1]
# отчётность юрлица (ГИР БО); у ИП её нет — «нет сведений» тут нормальный ответ, а не сбой
OPTIONAL = {"gir_bo"}
PATHS = {"gir_bo": "gir-bo"}


@dataclass
class Fetched:
    source: str
    status: str  # ok, not_found, unavailable
    attempts: int
    response: dict | None
    error: str | None
    started_at: datetime
    finished_at: datetime


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fetch(source: str, inn: str) -> Fetched:
    started = _now()
    error = None
    for attempt in range(1, settings.external_attempts + 1):
        try:
            r = httpx.get(f"{settings.mocks_url}/{PATHS.get(source, source)}/{inn}", timeout=settings.external_timeout)
            if r.status_code == 404:
                return Fetched(source, "not_found", attempt, None, r.text, started, _now())
            r.raise_for_status()
            return Fetched(source, "ok", attempt, r.json(), None, started, _now())
        except httpx.HTTPError as e:
            error = f"{type(e).__name__}: {e}"
            time.sleep(0.3 * attempt)
    return Fetched(source, "unavailable", settings.external_attempts, None, error, started, _now())


def get_fetch():
    # через зависимость, чтобы в тестах подменять на чтение файлов
    return fetch
