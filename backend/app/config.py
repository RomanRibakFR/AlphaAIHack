from datetime import date

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True)

    database_url: str = "postgresql+psycopg://credit:credit@localhost:5432/credit"
    mocks_url: str = "http://localhost:8001"
    # на какую дату считаем срок бизнеса; данные моков выгружены на 24.10.2026, пусто — сегодня
    data_as_of: date | None = None

    external_timeout: float = 5.0  # секунд на один запрос к источнику
    external_attempts: int = 3  # сколько раз пробуем, прежде чем считать источник недоступным

    # сроки ожидания клиента в минутах — только чтобы показать истечение на демо; по умолчанию из политики
    timeout_info_requested_minutes: int | None = None
    timeout_offer_minutes: int | None = None
    timeout_signing_minutes: int | None = None
    timer_interval_seconds: int = 60  # как часто проверяем просроченные заявки


settings = Settings()


def today() -> date:
    return settings.data_as_of or date.today()
