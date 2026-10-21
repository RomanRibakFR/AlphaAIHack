from fastapi import FastAPI

app = FastAPI(
    title="Моки внешних источников (ЕГРЮЛ/ЕГРИП, ФНС, БКИ)",
    version="0.1.0",
    description="Локальные заглушки внешних сервисов. Отдают синтетические данные по тестовым ИНН.",
)


@app.get("/health", tags=["service"])
def health() -> dict:
    return {"mocks": "ok"}
