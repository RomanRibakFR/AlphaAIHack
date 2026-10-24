#!/usr/bin/env python3
"""Генератор синтетических тестовых компаний для моков внешних сервисов.

Запуск:  python mocks/generate_mocks.py
Результат: mocks/companies/<ID>_<ИНН>.json — по одному файлу на компанию.

Все данные вымышлены. ИНН и ОГРН начинаются с кода региона 00 (такого региона нет),
поэтому не совпадут с реальной компанией, но проходят проверку контрольных цифр.
Формат файлов описан в docs/mocks-format.md. Генератор детерминирован (фиксированный seed).
"""
import json
import math
import random
import uuid
from datetime import date
from pathlib import Path

FORMAT_VERSION = "1.0"
REPORT_DATE = date(2026, 10, 24)  # дата, на которую «выгружены» данные источников
MONTHS = ["2025-10", "2025-11", "2025-12"] + [f"2026-{m:02d}" for m in range(1, 10)]
OUT = Path(__file__).resolve().parent / "companies"


# ---------- идентификаторы с правильными контрольными цифрами ----------

def _ctrl(digits, weights):
    return sum(int(d) * w for d, w in zip(digits, weights)) % 11 % 10


def inn_legal(n):
    base = f"0001{n:05d}"
    return base + str(_ctrl(base, [2, 4, 10, 3, 5, 9, 4, 6, 8]))


def inn_person(n):
    base = f"0001{n:06d}"
    c1 = _ctrl(base, [7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
    c2 = _ctrl(base + str(c1), [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
    return base + str(c1) + str(c2)


def ogrn_legal(reg, n):
    base = f"1{reg.year % 100:02d}0001{n:05d}"
    return base + str(int(base) % 11 % 10)


def ogrn_ip(reg, n):
    base = f"3{reg.year % 100:02d}00{n:09d}"
    return base + str(int(base) % 13 % 10)


# ---------- вспомогательные расчёты ----------

def months_between(d1, d2):
    return (d2.year - d1.year) * 12 + (d2.month - d1.month) - (1 if d2.day < d1.day else 0)


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, min(d.day, 28))


def annuity_amount(payment, rate, n):
    i = rate / 12
    return payment * (1 - (1 + i) ** -n) / i


def iso(d):
    return d.isoformat() if d else None


# ---------- внутренние данные банка: очищенные обороты ----------

def turnover_series(rng, avg, noise, season_amp, n_months=12, loans_received=None):
    months = MONTHS[-n_months:]
    factors = []
    for m in months:
        month_no = int(m[5:])
        season = season_amp * math.sin(2 * math.pi * (month_no - 3) / 12)
        factors.append(max(0.25, 1 + season + rng.gauss(0, noise)))
    total = avg * n_months
    net = [round(total * f / sum(factors)) for f in factors]
    net[-1] += total - sum(net)  # среднее ровно равно avg
    rows = []
    for m, v in zip(months, net):
        own = round(v * rng.uniform(0.03, 0.10))
        refunds = round(v * rng.uniform(0.003, 0.012))
        loans = (loans_received or {}).get(m, 0)
        rows.append({
            "month": m,
            "credit_total": v + own + refunds + loans,
            "credit_net": v,
            "excluded": {"own_transfers": own, "loans_received": loans, "refunds": refunds},
            "debit_total": round(v * rng.uniform(0.93, 1.01)),
            "avg_balance": round(v * rng.uniform(0.12, 0.30)),
        })
    return rows


# ---------- БКИ: договоры в формате кредитного отчёта ----------

CODE_DAYS = {"A": 29, "B": 7, "C": 29, "2": 59, "3": 89, "4": 119, "5": 120}


def bki_account(rng, *, type, creditor, opened, term, rate, payment=0, status="ACTIVE",
                closed=None, limit=None, outstanding=None, overdue_days=0,
                string_overrides=None, relationship="BORROWER", collateral=False):
    active_until = REPORT_DATE if status == "ACTIVE" else closed
    months_active = max(1, months_between(opened, active_until))
    length = min(24, months_active)
    codes = ["1"] * length
    for pos, code in (string_overrides or {}).items():
        if pos < length:
            codes[pos] = code
    if overdue_days:
        codes[0] = "A" if overdue_days < 30 else "2"
    if status == "ACTIVE":
        if limit is None:
            limit = int(round(annuity_amount(payment, rate, term), -4))
        if outstanding is None:
            remaining = max(1, term - months_active)
            outstanding = int(round(annuity_amount(payment, rate, remaining), -3))
    else:
        limit = limit or int(round(annuity_amount(max(payment, 10000), rate, term), -4))
        outstanding, payment = 0, 0
    counts = {"d30_59": codes.count("2"), "d60_89": codes.count("3"),
              "d90_plus": codes.count("4") + codes.count("5")}
    return {
        "contract_uid": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
        "account_type": type,
        "relationship": relationship,
        "creditor_kind": creditor,
        "opened_at": iso(opened),
        "planned_close_at": iso(add_months(opened, term)),
        "status": status,
        "closed_at": iso(closed),
        "currency": "RUB",
        "credit_limit": limit,
        "rate": rate,
        "outstanding": outstanding,
        "monthly_payment": payment if status == "ACTIVE" else 0,
        "next_payment_date": iso(date(2026, 11, 10)) if status == "ACTIVE" else None,
        "overdue_amount": payment if overdue_days else 0,
        "current_overdue_days": overdue_days,
        "overdue_counts_24m": counts,
        "payment_string": "".join(codes),
        "collateral": collateral,
    }


# ---------- описание компаний ----------
# grade/pd — допущение о том, в какой класс риска модель задачи 2 должна отнести компанию.

COMPANIES = [
    dict(id="C01", title="Кофейня — автоодобрение", type="LEGAL",
         name="Утренний кофе", reg=date(2018, 4, 12), okved=("56.10", "Деятельность ресторанов и услуги по доставке продуктов питания"),
         city="630099, г. Новосибирск, ул. Примерная, д. 12, офис 3", director="Смирнова Анна Викторовна",
         tax="USN", employees=18, turnover=2_500_000, noise=0.05, season=0.05,
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 3, 14), term=36, rate=0.17, payment=100_000)],
         inquiries=(1, 3),
         scenario=dict(product="WORKING_CAPITAL", amount=3_000_000, term=24,
                       purpose="Оборудование и запасы для второй кофейни", revenue_factor=1.05),
         expected=dict(scenario_id="S01", path=["T01", "T02", "T03", "T07", "T10", "T17", "T19"],
                       outcome="AUTO_APPROVED", reason=None, grade="A", pd=0.02)),

    dict(id="C02", title="ИП в торговле — автоодобрение", type="INDIVIDUAL",
         fio=("Кузнецов", "Дмитрий", "Олегович"), reg=date(2021, 2, 20),
         okved=("47.11", "Торговля розничная преимущественно пищевыми продуктами, включая напитки, и табачными изделиями в неспециализированных магазинах"),
         city="г. Барнаул", tax="USN", employees=4, turnover=1_800_000, noise=0.05, season=0.08,
         accounts=[dict(type="CAR_LOAN", creditor="OTHER_BANK", opened=date(2023, 6, 5), term=60, rate=0.16, payment=35_000),
                   dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 8, 20), term=24, rate=0.19, payment=25_000)],
         inquiries=(1, 4),
         scenario=dict(product="WORKING_CAPITAL", amount=1_500_000, term=12,
                       purpose="Закупка товара к новогоднему сезону", revenue_factor=1.0),
         expected=dict(scenario_id="S01", path=["T01", "T02", "T03", "T07", "T10", "T17", "T19"],
                       outcome="AUTO_APPROVED", reason=None, grade="A", pd=0.02)),

    dict(id="C03", title="Перевозчик — предложение с бо́льшим сроком", type="LEGAL",
         name="Сибирский маршрут", reg=date(2016, 9, 1), okved=("49.41", "Деятельность автомобильного грузового транспорта"),
         city="644000, г. Омск, ул. Складская, д. 7", director="Орлов Павел Андреевич",
         tax="OSNO", employees=42, turnover=3_000_000, noise=0.07, season=0.06,
         accounts=[dict(type="BUSINESS_LOAN", creditor="OWN_BANK", opened=date(2024, 5, 16), term=48, rate=0.16, payment=90_000),
                   dict(type="LEASING", creditor="LEASING_COMPANY", opened=date(2025, 1, 22), term=36, rate=0.20, payment=60_000, collateral=True)],
         inquiries=(2, 5),
         scenario=dict(product="WORKING_CAPITAL", amount=8_000_000, term=18,
                       purpose="Пополнение оборотных средств: топливо и ремонт парка", revenue_factor=1.08),
         expected=dict(scenario_id="S02", path=["T01", "T02", "T03", "T07", "T11", "T17", "T19"],
                       outcome="COUNTER_OFFER", reason="TERM_EXTENDED", grade="B", pd=0.04)),

    dict(id="C04", title="Стройматериалы — предложение с меньшей суммой", type="LEGAL",
         name="СтройБаза Юг", reg=date(2019, 6, 18), okved=("46.73", "Торговля оптовая лесоматериалами, строительными материалами и санитарно-техническим оборудованием"),
         city="350000, г. Краснодар, ул. Промышленная, д. 21", director="Ткаченко Сергей Иванович",
         tax="USN", employees=15, turnover=1_500_000, noise=0.08, season=0.12,
         accounts=[dict(type="CREDIT_LINE", creditor="OTHER_BANK", opened=date(2025, 2, 10), term=24, rate=0.19, payment=70_000),
                   dict(type="BUSINESS_LOAN", creditor="OWN_BANK", opened=date(2024, 11, 5), term=36, rate=0.17, payment=50_000)],
         inquiries=(2, 6),
         scenario=dict(product="WORKING_CAPITAL", amount=6_000_000, term=24,
                       purpose="Закупка стройматериалов к весеннему сезону", revenue_factor=1.10),
         expected=dict(scenario_id="S02", path=["T01", "T02", "T03", "T07", "T11", "T17", "T19"],
                       outcome="COUNTER_OFFER", reason="AMOUNT_REDUCED", grade="B", pd=0.05)),

    dict(id="C05", title="Мебельная мастерская — серая зона, к специалисту", type="LEGAL",
         name="Мастерская Кедр", reg=date(2023, 3, 10), okved=("31.09", "Производство прочей мебели"),
         city="664000, г. Иркутск, ул. Деревообработчиков, д. 4", director="Лебедев Артём Николаевич",
         tax="USN", employees=11, turnover=2_000_000, noise=0.25, season=0.10,
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2024, 6, 3), term=36, rate=0.21, payment=50_000,
                        string_overrides={11: "A", 12: "2"}),
                   dict(type="BUSINESS_LOAN", creditor="MFO", opened=date(2024, 1, 15), term=6, rate=0.45, payment=40_000,
                        status="CLOSED", closed=date(2024, 7, 15), string_overrides={2: "A", 3: "A"})],
         inquiries=(4, 11),
         scenario=dict(product="WORKING_CAPITAL", amount=2_000_000, term=24,
                       purpose="Материалы под крупный заказ", revenue_factor=1.12),
         expected=dict(scenario_id="S05", path=["T01", "T02", "T03", "T07", "T12", "T14", "T17", "T19"],
                       outcome="MANUAL_REVIEW", reason="M1_GREY_ZONE", grade="C", pd=0.11)),

    dict(id="C06", title="IT-компания — крупная сумма, к специалисту", type="LEGAL",
         name="Цифровые решения", reg=date(2015, 11, 5), okved=("62.01", "Разработка компьютерного программного обеспечения"),
         city="630090, г. Новосибирск, ул. Инженерная, д. 20", director="Волкова Мария Сергеевна",
         tax="OSNO", employees=60, turnover=6_000_000, noise=0.04, season=0.03,
         accounts=[dict(type="BUSINESS_LOAN", creditor="OWN_BANK", opened=date(2024, 9, 12), term=36, rate=0.16, payment=120_000),
                   dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 4, 8), term=24, rate=0.17, payment=80_000)],
         inquiries=(1, 3),
         scenario=dict(product="WORKING_CAPITAL", amount=15_000_000, term=36,
                       purpose="Финансирование разработки по крупному контракту", revenue_factor=1.03,
                       documents_at_submit=["financial_statements"]),
         expected=dict(scenario_id="S05", path=["T01", "T02", "T03", "T07", "T12", "T14", "T17", "T19"],
                       outcome="MANUAL_REVIEW", reason="M2_LARGE_AMOUNT", grade="A", pd=0.02,
                       note="Без загруженной отчётности заявка сначала уйдёт в «Требуется дополнение» (T04, правило V03)")),

    dict(id="C07", title="Пекарня — инвестиционный кредит с залогом, к специалисту", type="LEGAL",
         name="Хлебный дом", reg=date(2012, 7, 23), okved=("10.71", "Производство хлеба и мучных кондитерских изделий, тортов и пирожных недлительного хранения"),
         city="620000, г. Екатеринбург, ул. Мельничная, д. 15", director="Морозов Виктор Алексеевич",
         tax="OSNO", employees=85, turnover=5_000_000, noise=0.04, season=0.04,
         accounts=[dict(type="BUSINESS_LOAN", creditor="OWN_BANK", opened=date(2023, 10, 2), term=60, rate=0.15, payment=130_000, collateral=True),
                   dict(type="LEASING", creditor="LEASING_COMPANY", opened=date(2025, 6, 17), term=36, rate=0.19, payment=70_000, collateral=True)],
         inquiries=(1, 4),
         scenario=dict(product="INVESTMENT", amount=20_000_000, term=84,
                       purpose="Покупка новой линии выпечки", revenue_factor=1.02,
                       collateral=dict(type="REAL_ESTATE", description="Производственное помещение, 1 200 м²", value=35_000_000),
                       documents_at_submit=["financial_statements"]),
         expected=dict(scenario_id="S05", path=["T01", "T02", "T03", "T07", "T12", "T14", "T17", "T19"],
                       outcome="MANUAL_REVIEW", reason="M3_COLLATERAL", grade="B", pd=0.03)),

    dict(id="C08", title="Оптовая торговля — овердрафт меньше запрошенного", type="LEGAL",
         name="Оптовик Плюс", reg=date(2017, 2, 14), okved=("46.90", "Торговля оптовая неспециализированная"),
         city="603000, г. Нижний Новгород, ул. Торговая, д. 3", director="Никитин Олег Валерьевич",
         tax="USN", employees=12, turnover=4_000_000, noise=0.06, season=0.05,
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2022, 3, 1), term=36, rate=0.15, payment=60_000,
                        status="CLOSED", closed=date(2025, 3, 1))],
         inquiries=(1, 2),
         scenario=dict(product="OVERDRAFT", amount=3_000_000, term=12,
                       purpose="Кассовые разрывы при отсрочке платежа покупателям", revenue_factor=1.04),
         expected=dict(scenario_id="S02", path=["T01", "T02", "T03", "T07", "T11", "T17", "T19"],
                       outcome="COUNTER_OFFER", reason="AMOUNT_REDUCED", grade="B", pd=0.03)),

    dict(id="C09", title="Салон красоты — просит слишком много, отказ", type="LEGAL",
         name="Салон Лаванда", reg=date(2020, 8, 3), okved=("96.02", "Предоставление услуг парикмахерскими и салонами красоты"),
         city="420000, г. Казань, ул. Цветочная, д. 9", director="Галиева Алина Рустемовна",
         tax="USN", employees=9, turnover=1_000_000, noise=0.10, season=0.06,
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 5, 20), term=24, rate=0.20, payment=110_000),
                   dict(type="BUSINESS_LOAN", creditor="MFO", opened=date(2026, 6, 1), term=12, rate=0.40, payment=40_000),
                   dict(type="CREDIT_CARD", creditor="OTHER_BANK", opened=date(2024, 2, 1), term=36, rate=0.29, payment=30_000,
                        limit=500_000, outstanding=420_000)],
         inquiries=(5, 14),
         scenario=dict(product="WORKING_CAPITAL", amount=10_000_000, term=24,
                       purpose="Открытие второго салона", revenue_factor=1.05),
         expected=dict(scenario_id="S04", path=["T01", "T02", "T03", "T07", "T13"],
                       outcome="REJECTED", reason="NO_VIABLE_OFFER", grade="B", pd=0.06,
                       note="Исход не зависит от оценки модели: даже при классе B/C лимит меньше 30% запрошенного")),

    dict(id="C10", title="Стройка — высокий риск, отказ", type="LEGAL",
         name="Монолит-Строй", reg=date(2025, 8, 20), okved=("41.20", "Строительство жилых и нежилых зданий"),
         city="400000, г. Волгоград, ул. Строителей, д. 30", director="Ахметов Ринат Ильдарович",
         tax="OSNO", employees=27, turnover=2_000_000, noise=0.35, season=0.15, zsk="YELLOW",
         accounts=[dict(type="BUSINESS_LOAN", creditor="MFO", opened=date(2025, 9, 1), term=6, rate=0.50, payment=60_000,
                        status="CLOSED", closed=date(2026, 3, 20), string_overrides={0: "3", 1: "2", 2: "A"}),
                   dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 10, 1), term=12, rate=0.24, payment=90_000,
                        status="CLOSED", closed=date(2026, 8, 1), string_overrides={1: "2", 3: "A", 4: "2"})],
         inquiries=(9, 20),
         scenario=dict(product="WORKING_CAPITAL", amount=2_000_000, term=24,
                       purpose="Пополнение оборотных средств на объект", revenue_factor=1.10),
         expected=dict(scenario_id="S04", path=["T01", "T02", "T03", "T07", "T13"],
                       outcome="REJECTED", reason="HIGH_RISK", grade="D", pd=0.22)),

    dict(id="C11", title="ИП автосервис — долг по налогам, отказ", type="INDIVIDUAL",
         fio=("Захаров", "Игорь", "Петрович"), reg=date(2019, 5, 15),
         okved=("45.20", "Техническое обслуживание и ремонт автотранспортных средств"),
         city="г. Тюмень", tax="PSN", employees=3, turnover=900_000, noise=0.08, season=0.05,
         tax_debt=184_300, suspensions=[dict(number="4512", date=date(2026, 10, 7), reason_code="1", bank="OTHER_BANK")],
         accounts=[dict(type="CONSUMER_LOAN", creditor="OTHER_BANK", opened=date(2024, 10, 10), term=36, rate=0.21, payment=28_000)],
         inquiries=(2, 5),
         scenario=dict(product="WORKING_CAPITAL", amount=1_000_000, term=12,
                       purpose="Диагностическое оборудование", revenue_factor=1.05),
         expected=dict(scenario_id="S03", path=["T01", "T02", "T03", "T08"],
                       outcome="REJECTED", reason="SF03_TAX_DEBT", grade=None, pd=None)),

    dict(id="C12", title="Ресторан — текущая просрочка, отказ", type="LEGAL",
         name="Ресторан Полёт", reg=date(2017, 10, 2), okved=("56.10", "Деятельность ресторанов и услуги по доставке продуктов питания"),
         city="690000, г. Владивосток, ул. Морская, д. 5", director="Ким Евгений Валентинович",
         tax="USN", employees=25, turnover=2_200_000, noise=0.07, season=0.10,
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 1, 15), term=36, rate=0.18, payment=95_000, overdue_days=12)],
         inquiries=(3, 6),
         scenario=dict(product="WORKING_CAPITAL", amount=2_000_000, term=18,
                       purpose="Ремонт зала", revenue_factor=1.05),
         expected=dict(scenario_id="S03", path=["T01", "T02", "T03", "T08"],
                       outcome="REJECTED", reason="SF02_CURRENT_OVERDUE", grade=None, pd=None)),

    dict(id="C13", title="Рекламное агентство — в ликвидации, отказ", type="LEGAL",
         name="Реклама Медиа Групп", reg=date(2014, 3, 27), okved=("73.11", "Деятельность рекламных агентств"),
         city="344000, г. Ростов-на-Дону, ул. Издательская, д. 11", director="Соколов Андрей Михайлович",
         tax="USN", employees=6, turnover=700_000, noise=0.15, season=0.05, status="LIQUIDATING",
         accounts=[], inquiries=(1, 1),
         scenario=dict(product="WORKING_CAPITAL", amount=1_500_000, term=12,
                       purpose="Пополнение оборотных средств", revenue_factor=1.05),
         expected=dict(scenario_id="S03", path=["T01", "T02", "T03", "T08"],
                       outcome="REJECTED", reason="SF01_COMPANY_INACTIVE", grade=None, pd=None)),

    dict(id="C14", title="Интернет-магазин — бизнесу 7 месяцев, отказ с подсказкой", type="LEGAL",
         name="Маркетплейс-Старт", reg=date(2026, 3, 16), okved=("47.91", "Торговля розничная по почте или по информационно-коммуникационной сети Интернет"),
         city="190000, г. Санкт-Петербург, ул. Логистическая, д. 2", director="Фёдорова Дарья Игоревна",
         tax="USN", employees=5, turnover=1_200_000, noise=0.10, season=0.0, months_with_bank=7,
         accounts=[], inquiries=(1, 1),
         scenario=dict(product="WORKING_CAPITAL", amount=2_000_000, term=12,
                       purpose="Закупка товара", revenue_factor=1.0),
         expected=dict(scenario_id="S03", path=["T01", "T02", "T03", "T08"],
                       outcome="REJECTED", reason="SF04_BUSINESS_TOO_YOUNG", grade=None, pd=None,
                       note="В отказе подсказка: овердрафт доступен от 6 месяцев работы")),

    dict(id="C15", title="Продукты оптом — расхождение снято выпиской, автоодобрение", type="LEGAL",
         name="Продовольственная компания Обь", reg=date(2016, 4, 11), okved=("46.39", "Торговля оптовая неспециализированная пищевыми продуктами, напитками и табачными изделиями"),
         city="630005, г. Новосибирск, ул. Оптовая, д. 18", director="Павлов Константин Юрьевич",
         tax="OSNO", employees=22, turnover=2_500_000, noise=0.05, season=0.05,
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 7, 3), term=36, rate=0.17, payment=100_000)],
         inquiries=(1, 3),
         scenario=dict(product="WORKING_CAPITAL", amount=5_000_000, term=24,
                       purpose="Закупка продукции у новых поставщиков", declared_revenue=48_000_000,
                       document_on_request=dict(doc_type="other_bank_statement", turnover_12m=15_000_000)),
         expected=dict(scenario_id="S15", path=["T01", "T02", "T03", "T22", "T05", "T03", "T07", "T10", "T17", "T19"],
                       outcome="AUTO_APPROVED", reason=None, grade="A", pd=0.02,
                       note="Заявлено 48 млн, по счёту 30 млн (+60%) → запрос выписки; с выпиской 45 млн, расхождение 7% — снято")),

    dict(id="C16", title="ИП одежда — расхождение не снято, к специалисту", type="INDIVIDUAL",
         fio=("Белова", "Ольга", "Сергеевна"), reg=date(2020, 11, 2),
         okved=("47.71", "Торговля розничная одеждой в специализированных магазинах"),
         city="г. Красноярск", tax="USN", employees=5, turnover=1_500_000, noise=0.08, season=0.10,
         accounts=[dict(type="CREDIT_CARD", creditor="OTHER_BANK", opened=date(2023, 4, 1), term=36, rate=0.27, payment=15_000,
                        limit=300_000, outstanding=180_000),
                   dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 9, 15), term=24, rate=0.19, payment=45_000)],
         inquiries=(2, 5),
         scenario=dict(product="WORKING_CAPITAL", amount=2_000_000, term=24,
                       purpose="Закупка коллекции весна–лето", declared_revenue=36_000_000,
                       document_on_request=dict(doc_type="other_bank_statement", turnover_12m=6_000_000)),
         expected=dict(scenario_id="S16", path=["T01", "T02", "T03", "T22", "T05", "T03", "T07", "T12", "T14", "T17", "T19"],
                       outcome="MANUAL_REVIEW", reason="M4_DATA_MISMATCH", grade="B", pd=0.04,
                       note="Заявлено 36 млн, по счёту 18 млн (+100%); с выпиской 24 млн, расхождение 50% — не снято")),

    dict(id="C17", title="Склад — бюро кредитных историй не отвечает, к специалисту", type="LEGAL",
         name="Склад-Сервис", reg=date(2015, 1, 19), okved=("52.10", "Деятельность по складированию и хранению"),
         city="443000, г. Самара, ул. Портовая, д. 6", director="Егоров Илья Дмитриевич",
         tax="OSNO", employees=30, turnover=3_500_000, noise=0.05, season=0.04,
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 2, 25), term=36, rate=0.17, payment=110_000)],
         inquiries=(1, 3), bki_mode="unavailable",
         scenario=dict(product="WORKING_CAPITAL", amount=4_000_000, term=24,
                       purpose="Модернизация стеллажного оборудования", revenue_factor=1.03),
         expected=dict(scenario_id="S10", path=["T01", "T02", "T03", "T09", "T14", "T17", "T19"],
                       outcome="MANUAL_REVIEW", reason="M5_CHECKS_INCOMPLETE", grade="A", pd=0.02)),
]


def build(spec, seq):
    rng = random.Random(1000 + seq)
    reg = spec["reg"]
    person_seq = 100 + seq * 3

    # --- ЕГРЮЛ / ЕГРИП ---
    if spec["type"] == "LEGAL":
        inn = inn_legal(seq)
        director_inn = inn_person(person_seq)
        egrul = {
            "type": "LEGAL",
            "inn": inn,
            "kpp": inn[:4] + "01001",
            "ogrn": ogrn_legal(reg, seq),
            "name": {"full_with_opf": f"Общество с ограниченной ответственностью «{spec['name']}»",
                     "short_with_opf": f"ООО «{spec['name']}»"},
            "opf": {"code": "12300", "short": "ООО"},
            "state": {"status": spec.get("status", "ACTIVE"), "code": None,
                      "registration_date": iso(reg), "liquidation_date": None,
                      "actuality_date": "2026-10-20"},
            "okved": spec["okved"][0], "okved_name": spec["okved"][1],
            "management": {"name": spec["director"], "inn": director_inn,
                           "post": "ГЕНЕРАЛЬНЫЙ ДИРЕКТОР", "start_date": iso(reg)},
            "founders": [{"name": spec["director"], "inn": director_inn, "type": "PHYSICAL",
                          "share": {"type": "PERCENT", "value": 100}, "start_date": iso(reg)}],
            "address": {"value": spec["city"]},
            "invalid": None,
        }
        display = egrul["name"]["short_with_opf"]
    else:
        inn = inn_person(seq)
        s, n, p = spec["fio"]
        egrul = {
            "type": "INDIVIDUAL",
            "inn": inn,
            "ogrn": ogrn_ip(reg, seq),
            "name": {"full_with_opf": f"Индивидуальный предприниматель {s} {n} {p}",
                     "short_with_opf": f"ИП {s} {n[0]}. {p[0]}."},
            "fio": {"surname": s, "name": n, "patronymic": p},
            "opf": {"code": "50102", "short": "ИП"},
            "state": {"status": spec.get("status", "ACTIVE"), "code": None,
                      "registration_date": iso(reg), "liquidation_date": None,
                      "actuality_date": "2026-10-20"},
            "okved": spec["okved"][0], "okved_name": spec["okved"][1],
            "address": {"value": spec["city"]},
            "invalid": None,
        }
        display = egrul["name"]["short_with_opf"]

    # --- ФНС ---
    debt = spec.get("tax_debt", 0)
    fns = {
        "tax_regime": spec["tax"],
        "employee_count": spec["employees"],
        "employee_count_year": 2025,
        "tax_debt": {"has_debt": debt > 0, "amount": debt, "as_of": "2026-10-20"},
        "account_suspensions": [
            {"decision_number": s["number"], "decision_date": iso(s["date"]),
             "reason_code": s["reason_code"], "bank": s["bank"], "active": True}
            for s in spec.get("suspensions", [])],
        "no_reporting_over_year": False,
    }

    # --- ЗСК ---
    zsk = {"risk_level": spec.get("zsk", "GREEN"), "assigned_at": "2026-10-01"}

    # --- БКИ ---
    accounts = [bki_account(rng, **a) for a in spec["accounts"]]
    bki = {
        "subject": {"type": spec["type"], "inn": inn, "name": display},
        "report_date": iso(REPORT_DATE),
        "accounts": accounts,
        "inquiries": {"last_30d": spec["inquiries"][0], "last_24m": spec["inquiries"][1]},
    }
    if spec.get("bki_mode"):
        bki["_mock"] = {"mode": spec["bki_mode"]}

    # --- внутренние данные банка ---
    n_months = spec.get("months_with_bank", 12)
    loans_received = {}
    for a, acc in zip(spec["accounts"], accounts):
        m = a["opened"].strftime("%Y-%m")
        # деньги по бизнес-кредиту (наш или чужой банк, МФО) зачисляются на расчётный счёт
        if a["type"] in ("BUSINESS_LOAN", "CREDIT_LINE") and m in MONTHS[-n_months:]:
            loans_received[m] = acc["credit_limit"]
    turnover = turnover_series(rng, spec["turnover"], spec["noise"], spec["season"], n_months, loans_received)
    own_loans = [{"contract_uid": acc["contract_uid"], "product": acc["account_type"],
                  "opened_at": acc["opened_at"], "amount": acc["credit_limit"],
                  "outstanding": acc["outstanding"], "monthly_payment": acc["monthly_payment"],
                  "current_overdue_days": acc["current_overdue_days"]}
                 for a, acc in zip(spec["accounts"], accounts)
                 if a["creditor"] == "OWN_BANK" and acc["status"] == "ACTIVE"]
    client_since = reg if n_months < 12 else add_months(reg, 1)
    bank = {
        "client_since": iso(client_since),
        "account_type": "40702" if spec["type"] == "LEGAL" else "40802",
        "turnover_months": turnover,
        "own_loans": own_loans,
    }

    # --- сценарий и ожидаемый результат (мок это не отдаёт) ---
    sc = spec["scenario"]
    annual_bank = sum(r["credit_net"] for r in turnover) * 12 / n_months
    declared = sc.get("declared_revenue") or int(round(annual_bank * sc["revenue_factor"], -5))
    avg = sum(r["credit_net"] for r in turnover) / n_months
    mean = avg
    cv = (sum((r["credit_net"] - mean) ** 2 for r in turnover) / n_months) ** 0.5 / mean
    open_borrower = [a for a in accounts if a["status"] == "ACTIVE" and a["relationship"] == "BORROWER"]
    existing = sum(a["monthly_payment"] for a in open_borrower)
    all_codes = "".join(a["payment_string"] for a in accounts)
    worst = max([CODE_DAYS.get(c, 0) for c in all_codes] or [0])
    meta = {
        "id": spec["id"],
        "title": spec["title"],
        "scenario": {
            "product": sc["product"], "amount": sc["amount"], "term_months": sc["term"],
            "purpose": sc["purpose"], "declared_revenue_12m": declared,
            "collateral": sc.get("collateral"),
            "documents_at_submit": sc.get("documents_at_submit", []),
            "document_on_request": sc.get("document_on_request"),
        },
        "expected": {
            "scenario_id": spec["expected"]["scenario_id"],
            "path": spec["expected"]["path"],
            "outcome": spec["expected"]["outcome"],
            "reason": spec["expected"]["reason"],
            "assumed_grade": spec["expected"]["grade"],
            "assumed_pd": spec["expected"]["pd"],
            "note": spec["expected"].get("note"),
            "features": {
                "F1_business_age_months": months_between(reg, REPORT_DATE),
                "F2_avg_monthly_turnover": round(avg),
                "F3_turnover_cv": round(cv, 3),
                "F4_debt_load": round(existing / avg, 3),
                "F5_overdue_30plus_count_24m": sum(sum(a["overdue_counts_24m"].values()) for a in accounts),
                "F5_max_overdue_days_24m": worst,
                "F6_amount_to_turnover": round(sc["amount"] / avg, 2),
            },
        },
    }
    return {"format_version": FORMAT_VERSION, "meta": meta, "egrul": egrul, "fns": fns,
            "zsk": zsk, "bki": bki, "bank": bank}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for seq, spec in enumerate(COMPANIES, start=1):
        data = build(spec, seq)
        path = OUT / f"{spec['id']}_{data['egrul']['inn']}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{spec['id']}  {data['egrul']['inn']:<12}  {data['egrul']['name']['short_with_opf']:<40}  {spec['title']}")


if __name__ == "__main__":
    main()
