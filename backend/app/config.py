from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://credit:credit@localhost:5432/credit"
    mocks_url: str = "http://localhost:8001"
    # пауза между шагами конвейера, чтобы в кабинете было видно движение заявки
    pipeline_step_delay: float = 1.5


settings = Settings()
