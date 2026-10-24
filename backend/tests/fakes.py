# Те же данные, что отдаёт мок-сервис, но читаем файлы напрямую — тестам бэка сервис моков не нужен
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from app.external import Fetched
from app.registry import RegistryUnavailable

CANDIDATES = [Path("/app/mocks_companies"), Path(__file__).resolve().parents[2] / "mocks" / "companies"]
REGISTRY_DOWN_INN = "5001007329"  # валидный ИНН, на котором «реестр лежит»


@lru_cache
def companies() -> dict[str, dict]:
    folder = next(p for p in CANDIDATES if p.exists())
    result = {}
    for file in sorted(folder.glob("*.json")):
        d = json.loads(file.read_text(encoding="utf-8"))
        result[d["egrul"]["inn"]] = d
    return result


def by_id(company_id: str) -> dict:
    return next(d for d in companies().values() if d["meta"]["id"] == company_id)


def registry(inn):
    if inn == REGISTRY_DOWN_INN:
        raise RegistryUnavailable("лежит")
    d = companies().get(inn)
    return {k: v for k, v in d["egrul"].items() if k != "_mock"} if d else None


def fetch(source, inn):
    t = datetime(2026, 10, 24, 12, 0)
    section = dict(companies()[inn][source])
    mode = section.pop("_mock", {}).get("mode", "ok")
    if mode in ("unavailable", "timeout"):
        return Fetched(source, "unavailable", 3, None, f"{source}: {mode}", t, t)
    if mode == "not_found":
        return Fetched(source, "not_found", 1, None, "404", t, t)
    return Fetched(source, "ok", 1, section, None, t, t)
