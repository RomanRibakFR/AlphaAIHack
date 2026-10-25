"""
Мок-сервис внешних источников. Данные — mocks/companies/*.json (их готовит Аскар, формат — docs/mocks-format.md).
Каждый маршрут отдаёт свой раздел файла, без meta и служебного _mock.
"""
import asyncio
import copy
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

DATA_DIR = Path(os.getenv("MOCKS_DATA_DIR", Path(__file__).resolve().parent.parent / "companies"))
TIMEOUT_SLEEP = 30  # «не отвечаем» — дольше любого разумного таймаута бэкенда

# задержки по умолчанию, как у живых сервисов — чтобы в кабинете было видно подшаги
DEFAULT_DELAY_MS = {"egrul": 300, "fns": 200, "zsk": 200, "bank": 100, "bki": 1500}
if os.getenv("MOCKS_NO_DELAY"):
    DEFAULT_DELAY_MS = {k: 0 for k in DEFAULT_DELAY_MS}


def load() -> dict[str, dict]:
    companies = {}
    for file in sorted(DATA_DIR.glob("*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        companies[data["egrul"]["inn"]] = data
    return companies


COMPANIES = load()

app = FastAPI(
    title="Моки внешних источников",
    version="1.0.0",
    description=(
        "ЕГРЮЛ/ЕГРИП, ФНС, ЗСК, БКИ и внутренние данные банка — на синтетических данных из mocks/companies. "
        f"Компаний загружено: {len(COMPANIES)}."
    ),
)


async def section(inn: str, name: str) -> dict:
    company = COMPANIES.get(inn)
    if company is None:
        raise HTTPException(404, f"Нет сведений по ИНН {inn}")

    data = copy.deepcopy(company[name])
    mock = data.pop("_mock", {})
    delay = mock.get("delay_ms", DEFAULT_DELAY_MS[name])
    if delay:
        await asyncio.sleep(delay / 1000)

    mode = mock.get("mode", "ok")
    if mode == "unavailable":
        raise HTTPException(503, f"{name}: сервис временно недоступен")
    if mode == "not_found":
        raise HTTPException(404, f"{name}: нет сведений по ИНН {inn}")
    if mode == "timeout":
        await asyncio.sleep(TIMEOUT_SLEEP)
    return data


@app.get("/health", tags=["service"])
def health() -> dict:
    return {"mocks": "ok", "companies": len(COMPANIES)}


@app.get("/egrul/{inn}", tags=["ЕГРЮЛ / ЕГРИП"])
async def egrul(inn: str) -> dict:
    """Сведения из госреестра: статус, дата регистрации, ОКВЭД, руководитель."""
    return await section(inn, "egrul")


@app.get("/fns/{inn}", tags=["ФНС"])
async def fns(inn: str) -> dict:
    """Налоговая задолженность, приостановления операций по счетам."""
    return await section(inn, "fns")


@app.get("/zsk/{inn}", tags=["ЗСК (115-ФЗ)"])
async def zsk(inn: str) -> dict:
    """Уровень риска на платформе «Знай своего клиента»."""
    return await section(inn, "zsk")


@app.get("/bki/{inn}", tags=["БКИ"])
async def bki(inn: str) -> dict:
    """Кредитный отчёт: договоры, платежи, просрочки."""
    return await section(inn, "bki")


@app.get("/bank/{inn}", tags=["Данные банка"])
async def bank(inn: str) -> dict:
    """Обороты по расчётному счёту за 12 месяцев и кредиты в нашем банке."""
    return await section(inn, "bank")
