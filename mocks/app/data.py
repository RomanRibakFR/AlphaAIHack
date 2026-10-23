# Выдуманные компании для демо. ИНН с правильной контрольной суммой, но реальным фирмам не принадлежат.
# В комментарии — каким исходом должна закончиться заявка и с какой суммой это проверяли

REGISTRY = {
    # одобрение (оборотный, 5 млн на 24 мес.)
    "7701123451": {
        "inn": "7701123451",
        "ogrn": "1157746123456",
        "kind": "ul",
        "name": "ООО «Северный ветер»",
        "okved": "46.90",
        "okved_name": "Торговля оптовая неспециализированная",
        "registered_at": "2015-03-12",
        "status": "active",
        "address": "г. Москва, ул. Тверская, д. 10",
        "director": "Ковалёв Игорь Петрович",
    },
    # одобрение (овердрафт, 2 млн на 12 мес.)
    "772045678925": {
        "inn": "772045678925",
        "ogrn": "316774600123456",
        "kind": "ip",
        "name": "ИП Кузнецов Олег Николаевич",
        "okved": "47.11",
        "okved_name": "Торговля розничная в неспециализированных магазинах",
        "registered_at": "2016-04-05",
        "status": "active",
        "address": "г. Москва, ул. Профсоюзная, д. 32",
        "director": "Кузнецов Олег Николаевич",
    },
    # контрпредложение (оборотный, 3 млн на 24 мес.) — платежи по старым кредитам съедают оборот
    "7802543212": {
        "inn": "7802543212",
        "ogrn": "1227800054321",
        "kind": "ul",
        "name": "ООО «Пекарня Колосок»",
        "okved": "10.71",
        "okved_name": "Производство хлеба и мучных кондитерских изделий",
        "registered_at": "2022-06-01",
        "status": "active",
        "address": "г. Санкт-Петербург, Невский пр., д. 55",
        "director": "Лебедева Мария Андреевна",
    },
    # дозапрос (оборотный, 5 млн на 24 мес., выручка в анкете 30 млн) — выручка в анкете сильно больше оборотов у нас
    "6602345677": {
        "inn": "6602345677",
        "ogrn": "1196658012345",
        "kind": "ul",
        "name": "ООО «Техно Плюс»",
        "okved": "62.01",
        "okved_name": "Разработка компьютерного программного обеспечения",
        "registered_at": "2019-04-15",
        "status": "active",
        "address": "г. Екатеринбург, ул. Малышева, д. 51",
        "director": "Широков Павел Андреевич",
    },
    # ручная проверка (оборотный, 1 млн на 12 мес.) — молодой ИП без кредитной истории
    "540612345667": {
        "inn": "540612345667",
        "ogrn": "324540000012345",
        "kind": "ip",
        "name": "ИП Смирнова Анна Сергеевна",
        "okved": "96.02",
        "okved_name": "Предоставление услуг парикмахерскими и салонами красоты",
        "registered_at": "2024-02-20",
        "status": "active",
        "address": "г. Новосибирск, ул. Ленина, д. 3",
        "director": "Смирнова Анна Сергеевна",
    },
    # отказ по скорингу (оборотный, 2 млн на 24 мес.) — просрочки и высокая нагрузка
    "5403987653": {
        "inn": "5403987653",
        "ogrn": "1255400098765",
        "kind": "ul",
        "name": "ООО «Быстрый старт»",
        "okved": "47.91",
        "okved_name": "Торговля розничная по почте или через интернет",
        "registered_at": "2025-01-15",
        "status": "active",
        "address": "г. Новосибирск, Красный пр., д. 100",
        "director": "Орлов Денис Викторович",
    },
    # отказ сразу: ликвидация и долг по налогам
    "7711234560": {
        "inn": "7711234560",
        "ogrn": "1187746234560",
        "kind": "ul",
        "name": "ООО «Закат»",
        "okved": "56.10",
        "okved_name": "Деятельность ресторанов и услуги по доставке продуктов питания",
        "registered_at": "2018-09-03",
        "status": "liquidating",
        "address": "г. Москва, ул. Арбат, д. 20",
        "director": "Морозов Алексей Иванович",
    },
}

# кредитная история: history_months=0 — истории нет вообще
BKI = {
    "7701123451": dict(history_months=96, active_loans=2, total_debt=2_500_000, monthly_payments=150_000,
                       max_overdue_days_12m=0, current_overdue_days=0),
    "772045678925": dict(history_months=84, active_loans=1, total_debt=400_000, monthly_payments=50_000,
                         max_overdue_days_12m=0, current_overdue_days=0),
    "7802543212": dict(history_months=40, active_loans=3, total_debt=6_800_000, monthly_payments=350_000,
                       max_overdue_days_12m=0, current_overdue_days=0),
    "6602345677": dict(history_months=60, active_loans=2, total_debt=3_000_000, monthly_payments=200_000,
                       max_overdue_days_12m=0, current_overdue_days=0),
    "540612345667": dict(history_months=0, active_loans=0, total_debt=0, monthly_payments=0,
                         max_overdue_days_12m=0, current_overdue_days=0),
    "5403987653": dict(history_months=20, active_loans=4, total_debt=3_900_000, monthly_payments=250_000,
                       max_overdue_days_12m=45, current_overdue_days=0),
    "7711234560": dict(history_months=70, active_loans=1, total_debt=1_200_000, monthly_payments=90_000,
                       max_overdue_days_12m=15, current_overdue_days=0),
}

FNS = {
    "7701123451": dict(tax_debt=0, mass_address=False),
    "772045678925": dict(tax_debt=0, mass_address=False),
    "7802543212": dict(tax_debt=0, mass_address=False),
    "6602345677": dict(tax_debt=0, mass_address=False),
    "540612345667": dict(tax_debt=0, mass_address=False),
    "5403987653": dict(tax_debt=0, mass_address=True),
    "7711234560": dict(tax_debt=184_300, mass_address=False),
}


def _months(avg: int, spread: float) -> list[int]:
    # 12 месяцев вокруг среднего: чем больше spread, тем «рванее» обороты
    return [round(avg * (1 + spread * (1 if i % 2 else -1))) for i in range(12)]


# обороты по расчётному счёту у нас в банке за последние 12 месяцев
BANK = {
    "7701123451": dict(client_since="2016-02-01", monthly_turnover=_months(4_000_000, 0.08)),
    "772045678925": dict(client_since="2016-05-10", monthly_turnover=_months(1_500_000, 0.10)),
    "7802543212": dict(client_since="2022-07-01", monthly_turnover=_months(900_000, 0.12)),
    "6602345677": dict(client_since="2023-03-01", monthly_turnover=_months(800_000, 0.15)),
    "540612345667": dict(client_since="2024-03-01", monthly_turnover=_months(350_000, 0.40)),
    "5403987653": dict(client_since="2025-02-01", monthly_turnover=_months(500_000, 0.50)),
    "7711234560": dict(client_since="2018-10-01", monthly_turnover=_months(1_100_000, 0.30)),
}
