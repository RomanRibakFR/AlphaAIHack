# Умный кредитный кабинет предпринимателя

Прототип цифрового кредитного конвейера для малого и микробизнеса (кейс Альфа-Банка, Альфа-Хак 2026):
личный кабинет клиента, внутренняя обработка заявки, скоринг и кредитное решение в едином процессе.

README пока черновой — архитектуру, API, статусы и тестовые сценарии допишем по ходу.

## Состав

| Сервис | Технологии | Порт | Назначение |
| --- | --- | --- | --- |
| `frontend` | React 18 + TypeScript + Vite, nginx | 3000 | Личный кабинет клиента |
| `backend` | Python 3.12, FastAPI, SQLAlchemy, Alembic | 8000 | Кредитный конвейер, API |
| `mocks` | Python 3.12, FastAPI | 8001 | Заглушки ЕГРЮЛ/ЕГРИП, ФНС, БКИ |
| `db` | PostgreSQL 16 | — | Хранилище заявок |

## Запуск

Требуется Docker Desktop (Docker Engine 24+ с Compose v2).

```bash
docker compose up --build
```

- Кабинет: http://localhost:3000
- Swagger UI: http://localhost:8000/api/docs
- Моки: http://localhost:8001/docs

## Тесты

```bash
docker compose run --rm backend pytest
```
