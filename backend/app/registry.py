import httpx

from app.config import settings


class RegistryUnavailable(Exception):
    pass


def fetch_company(inn: str) -> dict | None:
    """Выписка из ЕГРЮЛ/ЕГРИП (у нас — из сервиса моков). None, если не нашли."""
    try:
        r = httpx.get(f"{settings.mocks_url}/registry/{inn}", timeout=5)
    except httpx.HTTPError as e:
        raise RegistryUnavailable(str(e)) from e
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise RegistryUnavailable(f"реестр ответил {r.status_code}")
    return r.json()


def get_registry():
    # через зависимость, чтобы в тестах подменять на фейк
    return fetch_company
