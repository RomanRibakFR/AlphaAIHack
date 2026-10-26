# Модель данных

Схема PostgreSQL. Источник истины — `backend/app/models.py`, миграции — `backend/migrations/versions/`.

```mermaid
erDiagram
    companies ||--o{ applications : "подаёт"
    products ||--o{ applications : "продукт"
    applications ||--o{ status_history : "переходы T01–T22"
    applications ||--o{ check_results : "ответы источников"
    applications ||--o{ decisions : "решения"
    applications ||--o{ offers : "предложения"
    applications ||--o{ info_requests : "дозапросы"
    applications ||--o{ documents : "документы"
    info_requests |o--o{ documents : "по запросу"
    companies ||--o{ chat_messages : "по ИНН"

    companies {
        int id PK
        string inn UK "10 или 12 цифр"
        string ogrn
        string kind "ul / ip"
        string name
        string okved
        date registered_at
    }
    products {
        int id PK
        string code UK "OVERDRAFT, WORKING_CAPITAL, INVESTMENT"
        string name
        decimal min_amount
        decimal max_amount
        int min_term_months
        int max_term_months
        decimal base_rate "% годовых, «от»"
        decimal max_rate
        bool requires_collateral
        int min_business_age_months
    }
    applications {
        int id PK
        int company_id FK
        int product_id FK
        decimal amount
        int term_months
        string purpose
        decimal annual_revenue "со слов клиента"
        string collateral_type
        decimal collateral_value
        string status "draft … issued"
        datetime deadline_at "до когда ждём клиента"
        int check_run "номер прохода проверок"
        string sign_code
        int version "оптимистическая блокировка"
        datetime submitted_at
        datetime issued_at
    }
    status_history {
        int id PK
        int application_id FK
        string transition_id "T01…T22"
        string event
        string from_status
        string to_status
        string actor "client / system / underwriter / timer"
        string reason_code
        datetime created_at
    }
    check_results {
        int id PK
        int application_id FK
        int run
        string source "egrul, fns, zsk, bank, gir_bo, bki"
        string status "ok / not_found / unavailable"
        int attempts
        json response
        datetime started_at
        datetime finished_at
    }
    decisions {
        int id PK
        int application_id FK
        string outcome "AUTO_APPROVED / COUNTER_OFFER / MANUAL_REVIEW / REJECTED"
        string policy_version
        string model_version
        decimal pd
        decimal pd_at_requested_terms
        string grade "A / B / C / D"
        decimal lgd
        decimal product_pd_max "граница C/D"
        json model_inputs "вход score.py"
        json features
        json contributions "вклад в логит"
        json clipping_warnings
        json stop_factors
        json manual_triggers "M1–M8"
        json reason_codes
        decimal max_amount
        string limit_binding
        json recommendation "черновик для специалиста"
        string reason "для клиента"
        string decided_by "system / underwriter"
    }
    offers {
        int id PK
        int application_id FK
        string type "AS_REQUESTED / COUNTER"
        string counter_kind "TERM_EXTENDED / AMOUNT_REDUCED"
        decimal amount
        int term_months
        decimal rate
        decimal monthly_payment
        json alternatives
        json conditions
        datetime valid_until
        int chosen_alternative
    }
    info_requests {
        int id PK
        int application_id FK
        string reason_code "V02_COLLATERAL, DATA_MISMATCH, UNDERWRITER"
        json items
        string requested_by
        datetime resolved_at
    }
    documents {
        int id PK
        int application_id FK
        int info_request_id FK
        string doc_type
        string filename
        int size
        bytes content
        json declared_values "суммы по выписке"
    }
    chat_messages {
        int id PK
        string inn
        string author "client / support"
        string text
        bool read_by_support
        bool read_by_client
    }
```

## Таблицы

| Таблица | Что хранит | Как пишется |
|---|---|---|
| `companies` | карточка компании из реестра | при создании заявки по ответу ЕГРЮЛ/ЕГРИП |
| `products` | каталог продуктов | `app/seed.py` из `config/decision_policy.yaml` при старте |
| `applications` | заявка и её текущий статус | API и конвейер; `version` защищает от одновременных изменений (ответ 409) |
| `status_history` | каждый переход статусной модели, кто его сделал и почему | только через `workflow.fire` — других способов сменить статус нет |
| `check_results` | ответ каждого внешнего источника, число попыток, время | конвейер, шаг `CHECKS`; `run` растёт при повторной проверке после дозапроса |
| `decisions` | решение системы или специалиста со всем, что нужно для объяснения и пересчёта | конвейер (`SCORING`, стоп-факторы) и специалист |
| `offers` | условия, которые видит клиент; варианты суммы и срока | конвейер или специалист |
| `info_requests` | что банк попросил дополнить | конвейер (V02, расхождение) или специалист |
| `documents` | загруженные файлы и заявленные по ним суммы | клиент; в прототипе файл хранится прямо в БД |
| `chat_messages` | переписка с поддержкой, привязана к ИНН, а не к заявке | клиент и поддержка |

Статусы и переходы — [application-states.md](application-states.md). Значения кодов (`SF*`, `M*`, `V*`, `limit_binding`) — [decision-policy.md](decision-policy.md).
