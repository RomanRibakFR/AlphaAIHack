#!/usr/bin/env python3
"""Генератор синтетических тестовых компаний для моков внешних сервисов.

Запуск:  python mocks/generate_mocks.py   (затем python mocks/check_mocks.py)
Результат: mocks/companies/<ID>_<ИНН>.json — по одному файлу на компанию.

Все данные вымышлены. ИНН и ОГРН начинаются с кода региона 00 (такого региона нет), поэтому
не совпадут с реальной компанией, но проходят проверку контрольных цифр. Формат — docs/mocks-format.md.
Генератор детерминирован (фиксированный seed).

Параметры денежного потока каждой компании (выручка, маржа, динамика, резерв, концентрация)
подобраны так, чтобы модель PD задачи 2 отнесла компанию к задуманному классу риска.
PD в файлы не вписывается руками: её считает настоящий score.py (через check_mocks.simulate).
"""
import json
import math
import random
import uuid
from datetime import date
from pathlib import Path

import check_mocks as engine

FORMAT_VERSION = "2.0"
REPORT_DATE = engine.APP_DATE          # дата выгрузки данных = дата заявки, 24.10.2026
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


# ---------- вспомогательное ----------

def months_between(d1, d2):
    return (d2.year - d1.year) * 12 + (d2.month - d1.month) - (1 if d2.day < d1.day else 0)


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, min(d.day, 28))


def iso(d):
    return d.isoformat() if d else None


def ym(d):
    return d.strftime("%Y-%m")


def k1000(x):
    return int(round(x / 1000)) * 1000


# ---------- БКИ: договоры в формате кредитного отчёта ----------

BUSINESS_DEBT = {"BUSINESS_LOAN", "CREDIT_LINE", "OVERDRAFT", "LEASING"}  # платятся с расчётного счёта


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
            limit = int(round(engine.annuity_amount(payment, rate, term), -4))
        if outstanding is None:
            outstanding = int(round(engine.annuity_amount(payment, rate, max(1, term - months_active)), -3))
    else:
        limit = limit or int(round(engine.annuity_amount(max(payment, 10000), rate, term), -4))
        outstanding = 0
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


# ---------- внутренние данные банка: счёт клиента ----------

def receipts_series(rng, avg, growth, cv, n):
    """Очищенные поступления по месяцам: средний уровень, колебания и рост последних 3 мес. к предыдущим 3."""
    r = [max(0.3, 1 + rng.gauss(0, cv)) for _ in range(n)]
    k = (1 + growth) * (sum(r[-6:-3]) / 3) / (sum(r[-3:]) / 3)
    r = r[:-3] + [x * k for x in r[-3:]]
    mean = sum(r) / n
    return [int(round(avg * x / mean)) for x in r]


def bank_account(rng, spec, accounts_spec, accounts):
    c = spec["cash"]
    n = spec.get("months_with_bank", 12)
    months = MONTHS[-n:]
    net = receipts_series(rng, c["receipts"], c["growth"], c["cv"], n)
    mean_net = sum(net) / n
    raw = [mean_net * (1 - c["margin"]) * (0.45 + 0.55 * x / mean_net) * math.exp(rng.gauss(0, 0.03)) for x in net]
    scale = mean_net * (1 - c["margin"]) / (sum(raw) / n)
    opex = [int(round(x * scale)) for x in raw]

    # платежи по кредитам с расчётного счёта: бизнес-кредиты, активные в этом месяце
    debt = [0] * n
    loans_received = [0] * n
    for a, acc in zip(accounts_spec, accounts):
        if a["type"] not in BUSINESS_DEBT or a.get("relationship", "BORROWER") != "BORROWER":
            continue
        start = ym(a["opened"])
        end = ym(a["closed"]) if a.get("status") == "CLOSED" else "9999-99"
        for i, m in enumerate(months):
            if start < m <= end:
                debt[i] += a.get("payment", 0)
            if m == start and a["type"] != "LEASING":
                loans_received[i] += acc["credit_limit"]

    existing = engine.existing_debt_service({"bki": {"accounts": accounts}})
    reserve = int(round((mean_net * (1 - c["margin"]) + existing) * c["reserve_m"]))
    own_in_frac = [rng.uniform(0.03, 0.10) for _ in months]
    refund_frac = [rng.uniform(0.003, 0.012) for _ in months]
    target_frac = [max(0.3, 1 + rng.gauss(0, 0.1)) for _ in months]

    def ledger(opening):
        """Остатки по месяцам: излишек выше целевого остатка владелец выводит, нехватку — докладывает."""
        balance, rows = opening, []
        for i, m in enumerate(months):
            own_in = int(round(net[i] * own_in_frac[i]))
            refunds = int(round(net[i] * refund_frac[i]))
            credit_total = net[i] + own_in + refunds + loans_received[i]
            own_out = max(0, int(round(balance + credit_total - opex[i] - debt[i] - target_frac[i] * reserve)))
            close = balance + credit_total - opex[i] - debt[i] - own_out
            floor = int(round(0.95 * reserve)) if i == len(months) - 1 else int(round(0.05 * reserve))
            if close < floor:  # владелец докладывает свои деньги (в конце периода — до уровня остатка на дату заявки)
                inject = floor - close
                own_in, credit_total, close = own_in + inject, credit_total + inject, close + inject
            rows.append({
                "month": m,
                "credit_total": credit_total,
                "credit_net": net[i],
                "excluded": {"own_transfers": own_in, "loans_received": loans_received[i], "refunds": refunds},
                "debit_total": opex[i] + debt[i] + own_out,
                "debit_operating": opex[i],
                "debit_debt_service": debt[i],
                "debit_own_transfers": own_out,
                "balance_open": balance,
                "balance_close": close,
            })
            balance = close
        return rows

    rows = ledger(int(round(reserve * 0.9)))

    # крупнейшие плательщики за 12 месяцев
    total = sum(net)
    payers = []
    share = c["top_share"]
    for j, name in enumerate(spec["customers"]):
        payers.append({"name": name, "inn": inn_legal(500 + spec["seq"] * 10 + j), "kind": "LEGAL",
                       "amount": int(round(total * share))})
        share *= rng.uniform(0.45, 0.75)
    if c.get("retail_share"):  # оплаты физлиц — не «покупатель», в долю крупнейшего покупателя не входят
        retail = min(c["retail_share"], 0.95 - sum(p["amount"] for p in payers) / total)
        payers.append({"name": "Оплаты покупателей картами и через СБП (эквайринг)", "inn": None,
                       "kind": "RETAIL_ACQUIRING", "amount": int(round(total * retail))})
    payers.sort(key=lambda p: -p["amount"])
    for p in payers:
        p["share"] = round(p["amount"] / total, 4)

    own_loans = [{"contract_uid": acc["contract_uid"], "product": acc["account_type"],
                  "opened_at": acc["opened_at"], "amount": acc["credit_limit"],
                  "outstanding": acc["outstanding"], "monthly_payment": acc["monthly_payment"],
                  "current_overdue_days": acc["current_overdue_days"]}
                 for acc in accounts if acc["creditor_kind"] == "OWN_BANK" and acc["status"] == "ACTIVE"]
    reg = spec["reg"]
    return {
        "client_since": iso(reg if n < 12 else add_months(reg, 1)),
        "account_type": "40702" if spec["type"] == "LEGAL" else "40802",
        "current_balance": reserve,
        "current_balance_date": iso(REPORT_DATE),
        "turnover_months": rows,
        "top_payers_12m": payers,
        "own_loans": own_loans,
    }


# ---------- ГИР БО: годовая бухгалтерская отчётность юрлица за 2025 год ----------

def financials(spec, bank):
    f = spec.get("fin")
    if f is None:
        return None
    revenue = f.get("revenue") or sum(r["credit_net"] for r in bank["turnover_months"]) * f.get("prior_year_factor", 0.95)
    assets = revenue / f["asset_turnover"]
    cl = assets * f["cl_assets"]
    return {
        "source": "GIR_BO",
        "year": 2025,
        "report_form": "SIMPLIFIED" if spec["msp"] == "MICRO" else "FULL",
        "unit": "RUB",
        "lines": {
            "1600": k1000(assets),                          # баланс (активы)
            "1300": k1000(assets * f["equity_assets"]),     # капитал и резервы
            "1200": k1000(cl * f["current_ratio"]),         # оборотные активы
            "1500": k1000(cl),                              # краткосрочные обязательства
            "2110": k1000(revenue),                         # выручка
            "2120": k1000(revenue * f["expenses_revenue"]), # себестоимость (полная) / расходы по обычной деятельности (упрощённая), по модулю
            "2400": k1000(revenue * f["net_margin"]),       # чистая прибыль (убыток)
        },
        "submitted_at": "2026-03-27",
    }


def msp_category(employees, income):
    if employees <= 15 and income <= 120e6:
        return "MICRO"
    if employees <= 100 and income <= 800e6:
        return "SMALL"
    return "MEDIUM"


# ---------- описание компаний ----------
# cash: receipts — средние очищенные поступления в месяц; margin — денежная операционная маржа;
#       growth — рост поступлений последних 3 мес. к предыдущим 3; cv — колебания по месяцам;
#       reserve_m — резерв на счёте в месяцах (операционные выплаты + платежи по кредитам);
#       top_share — доля крупнейшего покупателя-организации; retail_share — доля оплат физлиц (эквайринг).
# fin (юрлица): отношения для отчётности 2025 года из ГИР БО.
# expected: задуманный путь, исход, причина и класс риска — check_mocks.py проверяет их настоящей моделью.

COMPANIES = [
    dict(id="C01", title="Кофейня — автоодобрение", type="LEGAL",
         name="Утренний кофе", reg=date(2018, 4, 12), okved=("56.10", "Деятельность ресторанов и услуги по доставке продуктов питания"),
         city="630099, г. Новосибирск, ул. Примерная, д. 12, офис 3", director="Смирнова Анна Викторовна",
         tax="USN", employees=18,
         cash=dict(receipts=2_500_000, margin=0.16, growth=0.03, cv=0.06, reserve_m=1.8, top_share=0.12, retail_share=0.78),
         customers=["ООО «Офис-Кейтеринг»", "ООО «Бизнес-центр Обь»"],
         fin=dict(equity_assets=0.45, current_ratio=1.6, net_margin=0.08, asset_turnover=2.5, cl_assets=0.35, expenses_revenue=0.65),
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 3, 14), term=36, rate=0.17, payment=100_000)],
         inquiries=(1, 3),
         scenario=dict(product="WORKING_CAPITAL", amount=3_000_000, term=24,
                       purpose="Оборудование и запасы для второй кофейни", revenue_factor=1.05),
         expected=dict(scenario_id="S01", path=["T01", "T02", "T03", "T07", "T10", "T17", "T19"],
                       outcome="AUTO_APPROVED", reason=None, grade="A")),

    dict(id="C02", title="ИП в торговле — автоодобрение", type="INDIVIDUAL",
         fio=("Кузнецов", "Дмитрий", "Олегович"), reg=date(2021, 2, 20),
         okved=("47.11", "Торговля розничная преимущественно пищевыми продуктами, включая напитки, и табачными изделиями в неспециализированных магазинах"),
         city="г. Барнаул", tax="USN", employees=4,
         cash=dict(receipts=1_800_000, margin=0.13, growth=0.04, cv=0.07, reserve_m=1.5, top_share=0.13, retail_share=0.80),
         customers=["ООО «Столовая Заводская»", "ООО «Детский сад Солнышко»"],
         accounts=[dict(type="CAR_LOAN", creditor="OTHER_BANK", opened=date(2023, 6, 5), term=60, rate=0.16, payment=35_000),
                   dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 8, 20), term=24, rate=0.19, payment=25_000)],
         inquiries=(1, 4),
         scenario=dict(product="WORKING_CAPITAL", amount=1_500_000, term=12,
                       purpose="Закупка товара к новогоднему сезону", revenue_factor=1.0),
         expected=dict(scenario_id="S01", path=["T01", "T02", "T03", "T07", "T10", "T17", "T19"],
                       outcome="AUTO_APPROVED", reason=None, grade="A")),

    dict(id="C03", title="Перевозчик — предложение с бо́льшим сроком", type="LEGAL",
         name="Сибирский маршрут", reg=date(2016, 9, 1), okved=("49.41", "Деятельность автомобильного грузового транспорта"),
         city="644000, г. Омск, ул. Складская, д. 7", director="Орлов Павел Андреевич",
         tax="OSNO", employees=42,
         cash=dict(receipts=4_000_000, margin=0.12, growth=0.01, cv=0.08, reserve_m=0.58, top_share=0.34),
         customers=["ООО «СибАгроТорг»", "ООО «Омский завод упаковки»", "ООО «Логистик-Центр»"],
         fin=dict(equity_assets=0.35, current_ratio=1.3, net_margin=0.05, asset_turnover=1.8, cl_assets=0.40, expenses_revenue=0.80),
         accounts=[dict(type="BUSINESS_LOAN", creditor="OWN_BANK", opened=date(2024, 5, 16), term=48, rate=0.16, payment=90_000),
                   dict(type="LEASING", creditor="LEASING_COMPANY", opened=date(2025, 1, 22), term=36, rate=0.20, payment=60_000, collateral=True)],
         inquiries=(2, 5),
         scenario=dict(product="WORKING_CAPITAL", amount=8_000_000, term=18,
                       purpose="Пополнение оборотных средств: топливо и ремонт парка", revenue_factor=1.08),
         expected=dict(scenario_id="S02", path=["T01", "T02", "T03", "T07", "T11", "T17", "T19"],
                       outcome="COUNTER_OFFER", reason="TERM_EXTENDED", grade="B")),

    dict(id="C04", title="Стройматериалы — предложение с меньшей суммой", type="LEGAL",
         name="СтройБаза Юг", reg=date(2019, 6, 18), okved=("46.73", "Торговля оптовая лесоматериалами, строительными материалами и санитарно-техническим оборудованием"),
         city="350000, г. Краснодар, ул. Промышленная, д. 21", director="Ткаченко Сергей Иванович",
         tax="USN", employees=15,
         cash=dict(receipts=1_500_000, margin=0.12, growth=-0.02, cv=0.10, reserve_m=0.69, top_share=0.38),
         customers=["ООО «ЮгСтройИнвест»", "ООО «Кубань-Ремонт»", "ООО «Дом под ключ»"],
         fin=dict(equity_assets=0.25, current_ratio=1.2, net_margin=0.04, asset_turnover=2.2, cl_assets=0.50, expenses_revenue=0.93),
         accounts=[dict(type="CREDIT_LINE", creditor="OTHER_BANK", opened=date(2025, 2, 10), term=24, rate=0.19, payment=55_000),
                   dict(type="BUSINESS_LOAN", creditor="OWN_BANK", opened=date(2024, 11, 5), term=36, rate=0.17, payment=42_000)],
         inquiries=(2, 6),
         scenario=dict(product="WORKING_CAPITAL", amount=6_000_000, term=24,
                       purpose="Закупка стройматериалов к весеннему сезону", revenue_factor=1.10),
         expected=dict(scenario_id="S02", path=["T01", "T02", "T03", "T07", "T11", "T17", "T19"],
                       outcome="COUNTER_OFFER", reason="AMOUNT_REDUCED", grade="B")),

    dict(id="C05", title="Мебельная мастерская — пограничная оценка, к специалисту", type="LEGAL",
         name="Мастерская Кедр", reg=date(2023, 3, 10), okved=("31.09", "Производство прочей мебели"),
         city="664000, г. Иркутск, ул. Деревообработчиков, д. 4", director="Лебедев Артём Николаевич",
         tax="USN", employees=11,
         cash=dict(receipts=2_000_000, margin=0.07, growth=-0.08, cv=0.24, reserve_m=0.44, top_share=0.46, retail_share=0.30),
         customers=["ООО «Интерьер-Проект»", "ООО «Гостиница Ангара»"],
         fin=dict(equity_assets=0.10, current_ratio=1.0, net_margin=0.01, asset_turnover=2.0, cl_assets=0.65, expenses_revenue=0.97),
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2024, 6, 3), term=36, rate=0.21, payment=50_000,
                        string_overrides={11: "A", 12: "2"}),
                   dict(type="BUSINESS_LOAN", creditor="MFO", opened=date(2024, 1, 15), term=6, rate=0.45, payment=40_000,
                        status="CLOSED", closed=date(2024, 7, 15), string_overrides={2: "A", 3: "A"})],
         inquiries=(4, 11),
         scenario=dict(product="WORKING_CAPITAL", amount=2_000_000, term=24,
                       purpose="Материалы под крупный заказ", revenue_factor=1.12),
         expected=dict(scenario_id="S05", path=["T01", "T02", "T03", "T07", "T12", "T14", "T17", "T19"],
                       outcome="MANUAL_REVIEW", reason="M1_GREY_ZONE", grade="C")),

    dict(id="C06", title="IT-компания — крупная сумма, к специалисту", type="LEGAL",
         name="Цифровые решения", reg=date(2015, 11, 5), okved=("62.01", "Разработка компьютерного программного обеспечения"),
         city="630090, г. Новосибирск, ул. Инженерная, д. 20", director="Волкова Мария Сергеевна",
         tax="OSNO", employees=60,
         cash=dict(receipts=6_500_000, margin=0.20, growth=0.05, cv=0.07, reserve_m=2.5, top_share=0.30),
         customers=["ООО «РегионТелеком»", "ООО «Сибирская энергосбытовая»", "ООО «Ритейл-Системы»"],
         fin=dict(equity_assets=0.60, current_ratio=2.5, net_margin=0.15, asset_turnover=1.5, cl_assets=0.25, expenses_revenue=0.55),
         accounts=[dict(type="BUSINESS_LOAN", creditor="OWN_BANK", opened=date(2024, 9, 12), term=36, rate=0.16, payment=120_000),
                   dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 4, 8), term=24, rate=0.17, payment=80_000)],
         inquiries=(1, 3),
         scenario=dict(product="WORKING_CAPITAL", amount=15_000_000, term=36,
                       purpose="Финансирование разработки по крупному контракту", revenue_factor=1.03),
         expected=dict(scenario_id="S05", path=["T01", "T02", "T03", "T07", "T12", "T14", "T17", "T19"],
                       outcome="MANUAL_REVIEW", reason="M2_LARGE_AMOUNT", grade="A")),

    dict(id="C07", title="Пекарня — инвестиционный кредит с залогом, к специалисту", type="LEGAL",
         name="Хлебный дом", reg=date(2012, 7, 23), okved=("10.71", "Производство хлеба и мучных кондитерских изделий, тортов и пирожных недлительного хранения"),
         city="620000, г. Екатеринбург, ул. Мельничная, д. 15", director="Морозов Виктор Алексеевич",
         tax="OSNO", employees=85,
         cash=dict(receipts=5_000_000, margin=0.14, growth=0.02, cv=0.07, reserve_m=1.4, top_share=0.28),
         customers=["ООО «Сеть магазинов Уральский»", "ООО «Школьное питание»", "ООО «Кафе-Партнёр»"],
         fin=dict(equity_assets=0.50, current_ratio=1.4, net_margin=0.07, asset_turnover=1.2, cl_assets=0.30, expenses_revenue=0.75),
         accounts=[dict(type="BUSINESS_LOAN", creditor="OWN_BANK", opened=date(2023, 10, 2), term=60, rate=0.15, payment=130_000, collateral=True),
                   dict(type="LEASING", creditor="LEASING_COMPANY", opened=date(2025, 6, 17), term=36, rate=0.19, payment=70_000, collateral=True)],
         inquiries=(1, 4),
         scenario=dict(product="INVESTMENT", amount=20_000_000, term=84,
                       purpose="Покупка новой линии выпечки", revenue_factor=1.02,
                       collateral=dict(type="REAL_ESTATE", description="Производственное помещение, 1 200 м²", value=35_000_000)),
         expected=dict(scenario_id="S05", path=["T01", "T02", "T03", "T07", "T12", "T14", "T17", "T19"],
                       outcome="MANUAL_REVIEW", reason="M3_COLLATERAL", grade="A")),

    dict(id="C08", title="Оптовая торговля — овердрафт меньше запрошенного", type="LEGAL",
         name="Оптовик Плюс", reg=date(2017, 2, 14), okved=("46.90", "Торговля оптовая неспециализированная"),
         city="603000, г. Нижний Новгород, ул. Торговая, д. 3", director="Никитин Олег Валерьевич",
         tax="USN", employees=12,
         cash=dict(receipts=4_000_000, margin=0.10, growth=0.0, cv=0.07, reserve_m=0.27, top_share=0.32),
         customers=["ООО «Продмаркет-НН»", "ООО «Волга-Опт»", "ООО «Магазин у дома»"],
         fin=dict(equity_assets=0.30, current_ratio=1.3, net_margin=0.03, asset_turnover=3.0, cl_assets=0.55, expenses_revenue=0.95),
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2022, 3, 1), term=36, rate=0.15, payment=60_000,
                        status="CLOSED", closed=date(2025, 3, 1))],
         inquiries=(1, 2),
         scenario=dict(product="OVERDRAFT", amount=3_000_000, term=12,
                       purpose="Кассовые разрывы при отсрочке платежа покупателям", revenue_factor=1.04),
         expected=dict(scenario_id="S02", path=["T01", "T02", "T03", "T07", "T11", "T17", "T19"],
                       outcome="COUNTER_OFFER", reason="AMOUNT_REDUCED", grade="B")),

    dict(id="C09", title="Салон красоты — кредитная нагрузка уже предельная, отказ", type="LEGAL",
         name="Салон Лаванда", reg=date(2020, 8, 3), okved=("96.02", "Предоставление услуг парикмахерскими и салонами красоты"),
         city="420000, г. Казань, ул. Цветочная, д. 9", director="Галиева Алина Рустемовна",
         tax="USN", employees=9,
         cash=dict(receipts=1_000_000, margin=0.15, growth=0.01, cv=0.10, reserve_m=0.8, top_share=0.12, retail_share=0.82),
         customers=["ООО «Свадебное агентство Лето»"],
         fin=dict(equity_assets=0.15, current_ratio=1.0, net_margin=0.02, asset_turnover=2.0, cl_assets=0.50, expenses_revenue=0.96),
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 5, 20), term=24, rate=0.20, payment=110_000),
                   dict(type="BUSINESS_LOAN", creditor="MFO", opened=date(2026, 6, 1), term=12, rate=0.40, payment=40_000),
                   dict(type="CREDIT_CARD", creditor="OTHER_BANK", opened=date(2024, 2, 1), term=36, rate=0.29, payment=30_000,
                        limit=500_000, outstanding=420_000)],
         inquiries=(5, 14),
         scenario=dict(product="WORKING_CAPITAL", amount=10_000_000, term=24,
                       purpose="Открытие второго салона", revenue_factor=1.05),
         expected=dict(scenario_id="S04", path=["T01", "T02", "T03", "T07", "T13"],
                       outcome="REJECTED", reason="NO_VIABLE_OFFER", grade=None)),

    dict(id="C10", title="Стройка — высокий риск, отказ", type="LEGAL",
         name="Монолит-Строй", reg=date(2025, 8, 20), okved=("41.20", "Строительство жилых и нежилых зданий"),
         city="400000, г. Волгоград, ул. Строителей, д. 30", director="Ахметов Ринат Ильдарович",
         tax="OSNO", employees=27, zsk="YELLOW",
         cash=dict(receipts=2_000_000, margin=0.02, growth=-0.20, cv=0.33, reserve_m=0.55, top_share=0.62),
         customers=["ООО «Волга-Девелопмент»", "ООО «ЖилСтройЗаказ»"],
         fin=dict(equity_assets=0.05, current_ratio=0.8, net_margin=-0.06, asset_turnover=1.0, cl_assets=0.90, expenses_revenue=1.03,
                  revenue=5_000_000),  # 2025 год — неполный: компания зарегистрирована в августе
         accounts=[dict(type="BUSINESS_LOAN", creditor="MFO", opened=date(2025, 9, 1), term=6, rate=0.50, payment=60_000,
                        status="CLOSED", closed=date(2026, 3, 20), string_overrides={0: "3", 1: "2", 2: "A"}),
                   dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 10, 1), term=12, rate=0.24, payment=90_000,
                        status="CLOSED", closed=date(2026, 8, 1), string_overrides={1: "2", 3: "A", 4: "2"})],
         inquiries=(9, 20),
         scenario=dict(product="WORKING_CAPITAL", amount=2_000_000, term=24,
                       purpose="Пополнение оборотных средств на объект", revenue_factor=1.10),
         expected=dict(scenario_id="S04", path=["T01", "T02", "T03", "T07", "T13"],
                       outcome="REJECTED", reason="HIGH_RISK", grade="D")),

    dict(id="C11", title="ИП автосервис — долг по налогам, отказ", type="INDIVIDUAL",
         fio=("Захаров", "Игорь", "Петрович"), reg=date(2019, 5, 15),
         okved=("45.20", "Техническое обслуживание и ремонт автотранспортных средств"),
         city="г. Тюмень", tax="PSN", employees=3,
         tax_debt=184_300, suspensions=[dict(number="4512", date=date(2026, 10, 7), reason_code="1", bank="OTHER_BANK")],
         cash=dict(receipts=900_000, margin=0.14, growth=0.0, cv=0.08, reserve_m=0.6, top_share=0.15, retail_share=0.70),
         customers=["ООО «Такси-Сервис»"],
         accounts=[dict(type="CONSUMER_LOAN", creditor="OTHER_BANK", opened=date(2024, 10, 10), term=36, rate=0.21, payment=28_000)],
         inquiries=(2, 5),
         scenario=dict(product="WORKING_CAPITAL", amount=1_000_000, term=12,
                       purpose="Диагностическое оборудование", revenue_factor=1.05),
         expected=dict(scenario_id="S03", path=["T01", "T02", "T03", "T08"],
                       outcome="REJECTED", reason="SF03_TAX_DEBT", grade=None)),

    dict(id="C12", title="Ресторан — текущая просрочка, отказ", type="LEGAL",
         name="Ресторан Полёт", reg=date(2017, 10, 2), okved=("56.10", "Деятельность ресторанов и услуги по доставке продуктов питания"),
         city="690000, г. Владивосток, ул. Морская, д. 5", director="Ким Евгений Валентинович",
         tax="USN", employees=25,
         cash=dict(receipts=2_200_000, margin=0.10, growth=-0.03, cv=0.09, reserve_m=0.7, top_share=0.12, retail_share=0.80),
         customers=["ООО «Морской вокзал»"],
         fin=dict(equity_assets=0.30, current_ratio=1.2, net_margin=0.04, asset_turnover=2.0, cl_assets=0.45, expenses_revenue=0.85),
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 1, 15), term=36, rate=0.18, payment=95_000, overdue_days=12)],
         inquiries=(3, 6),
         scenario=dict(product="WORKING_CAPITAL", amount=2_000_000, term=18,
                       purpose="Ремонт зала", revenue_factor=1.05),
         expected=dict(scenario_id="S03", path=["T01", "T02", "T03", "T08"],
                       outcome="REJECTED", reason="SF02_CURRENT_OVERDUE", grade=None)),

    dict(id="C13", title="Рекламное агентство — в ликвидации, отказ", type="LEGAL",
         name="Реклама Медиа Групп", reg=date(2014, 3, 27), okved=("73.11", "Деятельность рекламных агентств"),
         city="344000, г. Ростов-на-Дону, ул. Издательская, д. 11", director="Соколов Андрей Михайлович",
         tax="USN", employees=6, status="LIQUIDATING",
         cash=dict(receipts=700_000, margin=0.03, growth=-0.15, cv=0.15, reserve_m=0.5, top_share=0.40),
         customers=["ООО «Ростов-Авто»", "ООО «Медицинский центр Дон»"],
         fin=dict(equity_assets=0.05, current_ratio=0.9, net_margin=-0.03, asset_turnover=1.5, cl_assets=0.60, expenses_revenue=1.0),
         accounts=[], inquiries=(1, 1),
         scenario=dict(product="WORKING_CAPITAL", amount=1_500_000, term=12,
                       purpose="Пополнение оборотных средств", revenue_factor=1.05),
         expected=dict(scenario_id="S03", path=["T01", "T02", "T03", "T08"],
                       outcome="REJECTED", reason="SF01_COMPANY_INACTIVE", grade=None)),

    dict(id="C14", title="Интернет-магазин — бизнесу 7 месяцев, отказ с подсказкой", type="LEGAL",
         name="Маркетплейс-Старт", reg=date(2026, 3, 16), okved=("47.91", "Торговля розничная по почте или по информационно-коммуникационной сети Интернет"),
         city="190000, г. Санкт-Петербург, ул. Логистическая, д. 2", director="Фёдорова Дарья Игоревна",
         tax="USN", employees=5, months_with_bank=7, fin=None,
         cash=dict(receipts=1_200_000, margin=0.10, growth=0.15, cv=0.10, reserve_m=0.6, top_share=0.85),
         customers=["ООО «Маркетплейс Площадка»"],
         accounts=[], inquiries=(1, 1),
         scenario=dict(product="WORKING_CAPITAL", amount=2_000_000, term=12,
                       purpose="Закупка товара", revenue_factor=1.0),
         expected=dict(scenario_id="S03", path=["T01", "T02", "T03", "T08"],
                       outcome="REJECTED", reason="SF04_BUSINESS_TOO_YOUNG", grade=None,
                       note="В отказе подсказка: овердрафт доступен от 6 месяцев работы. Отчётности за 2025 год нет — компания зарегистрирована в 2026")),

    dict(id="C15", title="Продукты оптом — расхождение снято выпиской, автоодобрение", type="LEGAL",
         name="Продовольственная компания Обь", reg=date(2016, 4, 11), okved=("46.39", "Торговля оптовая неспециализированная пищевыми продуктами, напитками и табачными изделиями"),
         city="630005, г. Новосибирск, ул. Оптовая, д. 18", director="Павлов Константин Юрьевич",
         tax="OSNO", employees=22,
         cash=dict(receipts=2_500_000, margin=0.15, growth=0.02, cv=0.06, reserve_m=1.8, top_share=0.25),
         customers=["ООО «Сеть Продукты 24»", "ООО «Новосибирский хладокомбинат»", "ООО «Кафе Сибирь»"],
         fin=dict(equity_assets=0.40, current_ratio=1.5, net_margin=0.06, asset_turnover=2.5, cl_assets=0.35, expenses_revenue=0.82,
                  revenue=45_000_000),
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 7, 3), term=36, rate=0.17, payment=100_000)],
         inquiries=(1, 3),
         scenario=dict(product="WORKING_CAPITAL", amount=4_000_000, term=24,
                       purpose="Закупка продукции у новых поставщиков", declared_revenue=48_000_000,
                       document_on_request=dict(doc_type="other_bank_statement", turnover_12m=15_000_000)),
         expected=dict(scenario_id="S15", path=["T01", "T02", "T03", "T22", "T05", "T03", "T07", "T10", "T17", "T19"],
                       outcome="AUTO_APPROVED", reason=None, grade="A",
                       note="Заявлено 48 млн, по нашему счёту 30 млн (+60%) → запрос выписки; с выпиской 45 млн, расхождение 7% — снято")),

    dict(id="C16", title="ИП одежда — расхождение не снято, к специалисту", type="INDIVIDUAL",
         fio=("Белова", "Ольга", "Сергеевна"), reg=date(2020, 11, 2),
         okved=("47.71", "Торговля розничная одеждой в специализированных магазинах"),
         city="г. Красноярск", tax="USN", employees=5,
         cash=dict(receipts=1_500_000, margin=0.12, growth=0.0, cv=0.09, reserve_m=0.41, top_share=0.14, retail_share=0.80),
         customers=["ООО «Корпоративная форма»"],
         accounts=[dict(type="CREDIT_CARD", creditor="OTHER_BANK", opened=date(2023, 4, 1), term=36, rate=0.27, payment=15_000,
                        limit=300_000, outstanding=180_000),
                   dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 9, 15), term=24, rate=0.19, payment=45_000)],
         inquiries=(2, 5),
         scenario=dict(product="WORKING_CAPITAL", amount=2_000_000, term=24,
                       purpose="Закупка коллекции весна–лето", declared_revenue=36_000_000,
                       document_on_request=dict(doc_type="other_bank_statement", turnover_12m=6_000_000)),
         expected=dict(scenario_id="S16", path=["T01", "T02", "T03", "T22", "T05", "T03", "T07", "T12", "T14", "T17", "T19"],
                       outcome="MANUAL_REVIEW", reason="M4_DATA_MISMATCH", grade="B",
                       note="Заявлено 36 млн, по нашему счёту 18 млн (+100%); с выпиской 24 млн, расхождение 50% — не снято")),

    dict(id="C17", title="Склад — бюро кредитных историй не отвечает, к специалисту", type="LEGAL",
         name="Склад-Сервис", reg=date(2015, 1, 19), okved=("52.10", "Деятельность по складированию и хранению"),
         city="443000, г. Самара, ул. Портовая, д. 6", director="Егоров Илья Дмитриевич",
         tax="OSNO", employees=30, bki_mode="unavailable",
         cash=dict(receipts=3_500_000, margin=0.15, growth=0.02, cv=0.05, reserve_m=1.5, top_share=0.30),
         customers=["ООО «Самара-Ритейл»", "ООО «Транспортная компания Волга»", "ООО «Фармсклад»"],
         fin=dict(equity_assets=0.45, current_ratio=1.5, net_margin=0.06, asset_turnover=1.2, cl_assets=0.30, expenses_revenue=0.70),
         accounts=[dict(type="BUSINESS_LOAN", creditor="OTHER_BANK", opened=date(2025, 2, 25), term=36, rate=0.17, payment=110_000)],
         inquiries=(1, 3),
         scenario=dict(product="WORKING_CAPITAL", amount=4_000_000, term=24,
                       purpose="Модернизация стеллажного оборудования", revenue_factor=1.03),
         expected=dict(scenario_id="S10", path=["T01", "T02", "T03", "T09", "T14", "T17", "T19"],
                       outcome="MANUAL_REVIEW", reason="M5_CHECKS_INCOMPLETE", grade=None)),
]


def build(spec, seq):
    rng = random.Random(2000 + seq)
    spec["seq"] = seq
    reg = spec["reg"]
    person_seq = 100 + seq * 3

    # --- ЕГРЮЛ / ЕГРИП ---
    if spec["type"] == "LEGAL":
        inn = inn_legal(seq)
        director_inn = inn_person(person_seq)
        egrul = {
            "type": "LEGAL", "inn": inn, "kpp": inn[:4] + "01001", "ogrn": ogrn_legal(reg, seq),
            "name": {"full_with_opf": f"Общество с ограниченной ответственностью «{spec['name']}»",
                     "short_with_opf": f"ООО «{spec['name']}»"},
            "opf": {"code": "12300", "short": "ООО"},
            "state": {"status": spec.get("status", "ACTIVE"), "code": None, "registration_date": iso(reg),
                      "liquidation_date": None, "actuality_date": "2026-10-20"},
            "okved": spec["okved"][0], "okved_name": spec["okved"][1],
            "management": {"name": spec["director"], "inn": director_inn, "post": "ГЕНЕРАЛЬНЫЙ ДИРЕКТОР", "start_date": iso(reg)},
            "founders": [{"name": spec["director"], "inn": director_inn, "type": "PHYSICAL",
                          "share": {"type": "PERCENT", "value": 100}, "start_date": iso(reg)}],
            "address": {"value": spec["city"]},
            "invalid": None,
        }
    else:
        inn = inn_person(seq)
        s, n, p = spec["fio"]
        egrul = {
            "type": "INDIVIDUAL", "inn": inn, "ogrn": ogrn_ip(reg, seq),
            "name": {"full_with_opf": f"Индивидуальный предприниматель {s} {n} {p}",
                     "short_with_opf": f"ИП {s} {n[0]}. {p[0]}."},
            "fio": {"surname": s, "name": n, "patronymic": p},
            "opf": {"code": "50102", "short": "ИП"},
            "state": {"status": spec.get("status", "ACTIVE"), "code": None, "registration_date": iso(reg),
                      "liquidation_date": None, "actuality_date": "2026-10-20"},
            "okved": spec["okved"][0], "okved_name": spec["okved"][1],
            "address": {"value": spec["city"]},
            "invalid": None,
        }
    display = egrul["name"]["short_with_opf"]

    # --- БКИ ---
    accounts = [bki_account(rng, **a) for a in spec["accounts"]]
    bki = {"subject": {"type": spec["type"], "inn": inn, "name": display}, "report_date": iso(REPORT_DATE),
           "accounts": accounts,
           "inquiries": {"last_30d": spec["inquiries"][0], "last_24m": spec["inquiries"][1]}}
    if spec.get("bki_mode"):
        bki["_mock"] = {"mode": spec["bki_mode"]}

    # --- внутренние данные банка и отчётность ---
    bank = bank_account(rng, spec, spec["accounts"], accounts)
    annual_net = sum(r["credit_net"] for r in bank["turnover_months"]) * 12 / len(bank["turnover_months"])
    spec["msp"] = msp_category(spec["employees"], annual_net)
    fin = financials(spec, bank) if spec["type"] == "LEGAL" else None
    if fin:  # категория — по выручке из отчётности; микропредприятия сдают упрощённую форму
        spec["msp"] = msp_category(spec["employees"], fin["lines"]["2110"])
        fin["report_form"] = "SIMPLIFIED" if spec["msp"] == "MICRO" else "FULL"

    # --- ФНС ---
    debt = spec.get("tax_debt", 0)
    fns = {
        "tax_regime": spec["tax"],
        "employee_count": spec["employees"], "employee_count_year": 2025,
        "msp_register": {"category": spec["msp"], "included_at": iso(max(date(2016, 8, 10), add_months(reg, 2)))},
        "tax_debt": {"has_debt": debt > 0, "amount": debt, "as_of": "2026-10-20"},
        "account_suspensions": [{"decision_number": s["number"], "decision_date": iso(s["date"]),
                                 "reason_code": s["reason_code"], "bank": s["bank"], "active": True}
                                for s in spec.get("suspensions", [])],
        "no_reporting_over_year": False,
    }

    # --- ЗСК ---
    zsk = {"risk_level": spec.get("zsk", "GREEN"), "assigned_at": "2026-10-01"}

    # --- сценарий анкеты ---
    sc = spec["scenario"]
    declared = sc.get("declared_revenue") or k1000(annual_net * sc["revenue_factor"])
    meta = {
        "id": spec["id"], "title": spec["title"],
        "scenario": {"product": sc["product"], "amount": sc["amount"], "term_months": sc["term"],
                     "purpose": sc["purpose"], "declared_revenue_12m": declared,
                     "collateral": sc.get("collateral"), "document_on_request": sc.get("document_on_request")},
        "expected": {k: spec["expected"].get(k) for k in ("scenario_id", "path", "outcome", "reason", "grade", "note")},
    }
    d = {"format_version": FORMAT_VERSION, "meta": meta, "egrul": egrul, "fns": fns, "zsk": zsk,
         "bki": bki, "bank": bank, "financials": fin}

    # --- расчёт настоящей моделью: что получится на этих данных ---
    _, _, _, det = engine.simulate(d)
    meta["expected"]["model"] = det.get("model")
    meta["expected"]["offer"] = det.get("offer")
    return d


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
