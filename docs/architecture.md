# Архитектура

## Компоненты

```mermaid
flowchart LR
    client(["Клиент<br/>(предприниматель)"])
    staff(["Специалист банка"])

    subgraph docker["docker compose"]
        direction LR
        fe["<b>frontend</b> :3000<br/>React + Vite, nginx<br/>кабинет клиента, рабочее место специалиста"]
        be["<b>backend</b> :8000<br/>FastAPI<br/>API, кредитный конвейер, таймер сроков"]
        db[("<b>db</b><br/>PostgreSQL 16<br/>заявки, решения, журнал")]
        mocks["<b>mocks</b> :8001<br/>FastAPI<br/>внешние источники на синтетике"]
    end

    cfg[/"config/decision_policy.yaml<br/>параметры политики"/]
    model[/"models/pd/&lt;ip|ul&gt;<br/>model.json + score.py"/]
    data[/"mocks/companies/*.json<br/>17 тестовых компаний"/]

    client --> fe
    staff --> fe
    fe -- "/api/* (прокси nginx)" --> be
    be -- "SQLAlchemy, Alembic" --> db
    be -- "HTTP: ЕГРЮЛ, ФНС, ЗСК, банк, ГИР БО, БКИ" --> mocks
    cfg -.-> be
    model -.-> be
    data -.-> mocks
```

| Компонент | Код | Что делает |
|---|---|---|
| `frontend` | `frontend/` | Лендинг с калькулятором. Кабинет клиента: анкета, статус и подшаги, дозапросы, предложение, подписание, чат. Рабочее место специалиста: очередь, разбор заявки, решение, чаты. В контейнере nginx раздаёт статику и проксирует `/api` на бэкенд. |
| `backend` | `backend/app/` | REST API (`api/`), статусная модель (`statuses.py`, `workflow.py`), конвейер (`pipeline.py`), извлечение признаков и стоп-факторов (`features.py`), вызов модели PD (`pd_model.py`), кредитная политика (`decision.py`), тексты для клиента (`texts.py`). |
| `db` | `backend/migrations/` | Заявки, история статусов, ответы источников, решения, предложения, документы, чат. Схема — [data-model.md](data-model.md). |
| `mocks` | `mocks/app/main.py` | Заменяет ЕГРЮЛ/ЕГРИП, ФНС, ЗСК, БКИ, ГИР БО и данные банка. Умеет недоступность, таймаут и задержки (`_mock`). |
| Модель PD | `models/pd/` | Две логистические регрессии (ИП — 11 признаков, ЮЛ — 19). Вызываются из бэкенда как есть. |
| Политика | `config/decision_policy.yaml` | Все числа решения: ставки, LGD, классы риска, лимиты, стоп-факторы, сроки. Меняются без правки кода. |

## Путь заявки через систему

```mermaid
sequenceDiagram
    autonumber
    actor C as Клиент
    participant F as frontend
    participant B as backend (API)
    participant P as конвейер (фоновый поток)
    participant M as mocks
    participant D as PostgreSQL

    C->>F: ИНН, анкета
    F->>B: POST /api/applications
    B->>M: GET /egrul/{inn} (карточка компании)
    B->>D: черновик (DRAFT)
    C->>F: «Отправить»
    F->>B: POST /api/applications/{id}/submit
    B->>D: SUBMITTED (T01)
    B-)P: запуск конвейера
    P->>P: VALIDATION — полнота (V02)
    loop CHECKS: источник за источником
        P->>M: egrul, fns, zsk, bank, gir-bo, bki
        P->>D: check_results (кабинет видит подшаги)
    end
    P->>P: стоп-факторы SF01–SF06, сверка анкеты и счёта
    P->>P: SCORING — лимит и условия, PD (score.py), класс, ставка
    P->>D: decision + offer, новый статус
    F->>B: GET /api/applications/{id} (опрос)
    B-->>F: статус, предложение или причина отказа
    C->>F: принять, подписать кодом
    F->>B: accept → sign
    B->>D: ISSUED, график платежей
```

Конвейер работает в фоновом потоке бэкенда. После рестарта он подхватывает незаконченные заявки (`resume_unfinished`). Отдельный таймер переводит заявки в «Срок истёк», если клиент не ответил вовремя: на дозапрос — 14 дней, на предложение — 30, на подписание — 5.

## Принципы

- **Оценка риска отделена от решения.** Модель отвечает только за PD, политика — за продукты, лимиты и маршрут. Модель переобучается заменой `model.json`, политика меняется в YAML.
- **Каждое решение воспроизводимо.** В `decisions` сохраняются вход модели, вклад признаков, версии модели и политики, LGD и ограничение лимита.
- **Сбой источника не превращается в отказ.** Если источник не ответил после повторов, заявку смотрит специалист (M5).
- **Специалист получает исключения с готовой рекомендацией.** Автоматика не перезаписывает его решение (M7).

Подробности: статусы и переходы — [application-states.md](application-states.md), [диаграмма состояний](diagrams/application-states.png), [BPMN процесса](diagrams/credit-process.png); логика решения — [decision-policy.md](decision-policy.md); API — [api/openapi.json](api/openapi.json).
