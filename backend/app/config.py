from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://credit:credit@localhost:5432/credit"
    mocks_url: str = "http://localhost:8001"


settings = Settings()
