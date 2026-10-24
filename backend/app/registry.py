import httpx

from app.config import settings


class RegistryUnavailable(Exception):
    pass


def fetch_company(inn: str) -> dict | None:
    """Выписка из ЕГРЮЛ/ЕГРИП (у нас — из сервиса моков). None, если не нашли."""
    try:
        r = httpx.get(f"{settings.mocks_url}/egrul/{inn}", timeout=5)
    except httpx.HTTPError as e:
        raise RegistryUnavailable(str(e)) from e
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise RegistryUnavailable(f"реестр ответил {r.status_code}")
    return r.json()


def company_card(egrul: dict) -> dict:
    """Короткая карточка компании из ответа ЕГРЮЛ — для автозаполнения анкеты."""
    legal = egrul["type"] == "LEGAL"
    return {
        "inn": egrul["inn"],
        "ogrn": egrul.get("ogrn"),
        "kind": "ul" if legal else "ip",
        "name": egrul["name"]["short_with_opf"],
        "okved": egrul.get("okved"),
        "okved_name": egrul.get("okved_name"),
        "registered_at": egrul["state"]["registration_date"],
        "status": egrul["state"]["status"],
        "address": (egrul.get("address") or {}).get("value"),
        "director": (egrul.get("management") or {}).get("name") if legal else egrul["name"]["short_with_opf"],
    }


def get_registry():
    # через зависимость, чтобы в тестах подменять на фейк
    return fetch_company
