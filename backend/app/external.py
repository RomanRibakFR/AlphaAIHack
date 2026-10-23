import time

import httpx

from app.config import settings

SOURCES = {
    "registry": "/registry/{inn}",
    "bki": "/bki/{inn}",
    "fns": "/fns/{inn}",
    "bank": "/bank/{inn}/turnover",
}


class ExternalUnavailable(Exception):
    pass


def fetch_all(inn: str, attempts: int = 2) -> dict[str, dict]:
    """Собирает данные из всех внешних источников. Пара попыток, потом сдаёмся."""
    result = {}
    for source, path in SOURCES.items():
        for attempt in range(attempts):
            try:
                r = httpx.get(settings.mocks_url + path.format(inn=inn), timeout=5)
                r.raise_for_status()
                result[source] = r.json()
                break
            except httpx.HTTPError as e:
                if attempt == attempts - 1:
                    raise ExternalUnavailable(f"{source}: {e}") from e
                time.sleep(0.5)
    return result
