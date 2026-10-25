"""
Что извлекаем из ответов источников: признаки модели F1–F6, стоп-факторы SF01–SF06,
сверку выручки из анкеты с оборотами по счёту. Правила — docs/decision-policy.md, разделы 4–5.
"""
from dataclasses import dataclass
from datetime import date

from app.policy import policy, stop_factor

# дни просрочки по кодам строки платёжной дисциплины (как в НБКИ)
CODE_DAYS = {"A": 29, "B": 7, "C": 29, "С": 29, "2": 59, "3": 89, "4": 119, "5": 120}


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month - (end.day < start.day)


def business_age_months(egrul: dict, today: date) -> int:
    return months_between(date.fromisoformat(egrul["state"]["registration_date"]), today)


def avg_turnover(bank: dict) -> float:
    # только очищенные поступления: переводы себе и полученные кредиты — не выручка
    rows = bank["turnover_months"]
    return sum(r["credit_net"] for r in rows) / len(rows)


def current_payments(bki: dict) -> float:
    # нагрузку считаем только по БКИ: кредиты нашего банка там уже есть (не удваиваем с bank.own_loans)
    return sum(a["monthly_payment"] for a in bki["accounts"] if a["status"] == "ACTIVE" and a["relationship"] == "BORROWER")


def features(egrul: dict, bki: dict, bank: dict, amount: float, today: date) -> dict:
    rows = bank["turnover_months"]
    avg = avg_turnover(bank)
    cv = (sum((r["credit_net"] - avg) ** 2 for r in rows) / len(rows)) ** 0.5 / avg
    accounts = bki["accounts"]
    codes = "".join(a["payment_string"] for a in accounts)
    return {
        "F1_business_age_months": business_age_months(egrul, today),
        "F2_avg_monthly_turnover": round(avg),
        "F3_turnover_cv": round(cv, 3),
        "F4_debt_load": round(current_payments(bki) / avg, 3),
        "F5_overdue_30plus_count_24m": sum(sum(a["overdue_counts_24m"].values()) for a in accounts),
        "F5_max_overdue_days_24m": max([CODE_DAYS.get(c, 0) for c in codes] or [0]),
        "F6_amount_to_turnover": round(amount / avg, 2),
    }


def stop_factors(data: dict, product: dict, today: date) -> list[dict]:
    """Все сработавшие стоп-факторы по тем источникам, что ответили. Порядок — как в политике."""
    egrul, fns, zsk, bki, bank = (data.get(k) for k in ("egrul", "fns", "zsk", "bki", "bank"))
    enabled = {s["code"] for s in policy()["stop_factors"] if s["enabled"]}
    found = []

    if egrul and egrul["state"]["status"] != "ACTIVE":
        found.append({"code": "SF01_COMPANY_INACTIVE", "status": egrul["state"]["status"]})

    overdue = bki and any(a["status"] == "ACTIVE" and a["current_overdue_days"] > 0 for a in bki["accounts"])
    overdue = overdue or (bank and any(l["current_overdue_days"] > 0 for l in bank["own_loans"]))
    if overdue:
        found.append({"code": "SF02_CURRENT_OVERDUE"})

    if fns:
        threshold = stop_factor("SF03_TAX_DEBT")["tax_debt_threshold"]
        suspended = [s for s in fns["account_suspensions"] if s["active"]]
        if fns["tax_debt"]["amount"] > threshold or suspended:
            found.append({"code": "SF03_TAX_DEBT", "tax_debt": fns["tax_debt"]["amount"], "suspensions": len(suspended)})

    if egrul:
        age = business_age_months(egrul, today)
        if age < product["min_business_age_months"]:
            found.append({"code": "SF04_BUSINESS_TOO_YOUNG", "age": age, "min_age": product["min_business_age_months"]})

    if zsk and zsk["risk_level"] == "RED":
        found.append({"code": "SF05_ZSK_RED"})

    if egrul and egrul.get("invalid"):
        found.append({"code": "SF06_EGRUL_UNRELIABLE"})

    return [f for f in found if f["code"] in enabled]


@dataclass
class Revenue:
    bank_annual: float  # обороты по счёту у нас за 12 мес.
    declared: float  # выручка из анкеты
    statement_annual: float | None  # обороты по выписке из другого банка, приведённые к году
    mismatch: float  # насколько заявленная выручка выше подтверждённой
    needs_document: bool  # расхождение есть, а документа ещё нет
    unresolved: bool  # документ есть, но расхождение осталось
    monthly_for_limits: float  # каким оборотом считать лимит


def revenue_check(bank: dict, declared: float, statement: dict | None) -> Revenue:
    """Сверка анкеты и счёта (раздел 4.3 политики)."""
    tol = policy()["data_mismatch"]["tolerance"]
    bank_annual = avg_turnover(bank) * 12
    ratio = declared / bank_annual - 1

    if ratio <= tol:
        return Revenue(bank_annual, declared, None, ratio, False, False, bank_annual / 12)
    if statement is None:
        return Revenue(bank_annual, declared, None, ratio, True, False, bank_annual / 12)

    statement_annual = statement["turnover"] * 12 / statement.get("months", 12)
    verified = bank_annual + statement_annual
    ratio_after = declared / verified - 1
    if ratio_after <= tol:
        return Revenue(bank_annual, declared, statement_annual, ratio_after, False, False, verified / 12)
    # документ не снял расхождение — лимит только по нашим оборотам, решает специалист (M4)
    return Revenue(bank_annual, declared, statement_annual, ratio_after, False, True, bank_annual / 12)
