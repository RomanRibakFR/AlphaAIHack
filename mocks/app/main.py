from fastapi import FastAPI, HTTPException

from app.data import BANK, BKI, FNS, REGISTRY

app = FastAPI(
    title="Моки внешних источников (ЕГРЮЛ/ЕГРИП, ФНС, БКИ)",
    version="0.2.0",
    description="Локальные заглушки внешних сервисов. Отдают синтетические данные по тестовым ИНН.",
)


def find(source: dict, inn: str, what: str) -> dict:
    if inn not in source:
        raise HTTPException(404, f"{what}: нет данных по ИНН {inn}")
    return {"inn": inn, **source[inn]}


@app.get("/health", tags=["service"])
def health() -> dict:
    return {"mocks": "ok"}


@app.get("/registry/{inn}", tags=["ЕГРЮЛ / ЕГРИП"])
def registry(inn: str) -> dict:
    """Выписка из реестра по ИНН."""
    company = REGISTRY.get(inn)
    if company is None:
        raise HTTPException(404, "Компания с таким ИНН не найдена в реестре")
    return company


@app.get("/bki/{inn}", tags=["БКИ"])
def bki(inn: str) -> dict:
    """Кредитная история: действующие кредиты, платежи, просрочки."""
    return find(BKI, inn, "БКИ")


@app.get("/fns/{inn}", tags=["ФНС"])
def fns(inn: str) -> dict:
    """Сведения ФНС: долги по налогам, массовый адрес."""
    return find(FNS, inn, "ФНС")


@app.get("/bank/{inn}/turnover", tags=["Данные банка"])
def turnover(inn: str) -> dict:
    """Обороты по расчётному счёту в нашем банке за 12 месяцев."""
    return find(BANK, inn, "Счёт")
