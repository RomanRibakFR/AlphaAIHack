# Урезанная копия данных моков — чтобы тесты бэка не зависели от сервиса mocks
from app.external import ExternalUnavailable
from app.registry import RegistryUnavailable


def months(avg, spread):
    return [round(avg * (1 + spread * (1 if i % 2 else -1))) for i in range(12)]


COMPANIES = {
    # одобрение
    "7701123451": dict(
        registry=dict(inn="7701123451", ogrn="1157746123456", kind="ul", name="ООО «Северный ветер»",
                      okved="46.90", registered_at="2015-03-12", status="active"),
        bki=dict(history_months=96, active_loans=2, total_debt=2_500_000, monthly_payments=150_000,
                 max_overdue_days_12m=0, current_overdue_days=0),
        fns=dict(tax_debt=0, mass_address=False),
        bank=dict(client_since="2016-02-01", monthly_turnover=months(4_000_000, 0.08)),
    ),
    # контрпредложение
    "7802543212": dict(
        registry=dict(inn="7802543212", kind="ul", name="ООО «Пекарня Колосок»", registered_at="2022-06-01", status="active"),
        bki=dict(history_months=40, active_loans=3, total_debt=6_800_000, monthly_payments=350_000,
                 max_overdue_days_12m=0, current_overdue_days=0),
        fns=dict(tax_debt=0, mass_address=False),
        bank=dict(client_since="2022-07-01", monthly_turnover=months(900_000, 0.12)),
    ),
    # дозапрос выписки
    "6602345677": dict(
        registry=dict(inn="6602345677", kind="ul", name="ООО «Техно Плюс»", registered_at="2019-04-15", status="active"),
        bki=dict(history_months=60, active_loans=2, total_debt=3_000_000, monthly_payments=200_000,
                 max_overdue_days_12m=0, current_overdue_days=0),
        fns=dict(tax_debt=0, mass_address=False),
        bank=dict(client_since="2023-03-01", monthly_turnover=months(800_000, 0.15)),
    ),
    # ручная проверка
    "540612345667": dict(
        registry=dict(inn="540612345667", kind="ip", name="ИП Смирнова Анна Сергеевна", registered_at="2024-02-20", status="active"),
        bki=dict(history_months=0, active_loans=0, total_debt=0, monthly_payments=0,
                 max_overdue_days_12m=0, current_overdue_days=0),
        fns=dict(tax_debt=0, mass_address=False),
        bank=dict(client_since="2024-03-01", monthly_turnover=months(350_000, 0.40)),
    ),
    # стоп-фактор
    "7711234560": dict(
        registry=dict(inn="7711234560", kind="ul", name="ООО «Закат»", registered_at="2018-09-03", status="liquidating"),
        bki=dict(history_months=70, active_loans=1, total_debt=1_200_000, monthly_payments=90_000,
                 max_overdue_days_12m=15, current_overdue_days=0),
        fns=dict(tax_debt=184_300, mass_address=False),
        bank=dict(client_since="2018-10-01", monthly_turnover=months(1_100_000, 0.30)),
    ),
    # в реестре есть, а остальные сервисы «лежат»
    "5403987653": dict(
        registry=dict(inn="5403987653", kind="ul", name="ООО «Быстрый старт»", registered_at="2025-01-15", status="active"),
    ),
}

REGISTRY_DOWN_INN = "5001007329"


def registry(inn):
    if inn == REGISTRY_DOWN_INN:
        raise RegistryUnavailable("лежит")
    return COMPANIES.get(inn, {}).get("registry")


def fetch_all(inn):
    data = COMPANIES[inn]
    if "bki" not in data:
        raise ExternalUnavailable("bki: timeout")
    return data
