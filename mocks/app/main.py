from fastapi import FastAPI, HTTPException

from app.data import REGISTRY

app = FastAPI(
    title="Моки внешних источников (ЕГРЮЛ/ЕГРИП, ФНС, БКИ)",
    version="0.1.0",
    description="Локальные заглушки внешних сервисов. Отдают синтетические данные по тестовым ИНН.",
)


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
