"""
Что извлекаем из ответов источников: вход модели PD, стоп-факторы SF01–SF06,
сверку выручки из анкеты с оборотами по счёту. Правила — docs/decision-policy.md, разделы 4–5,
вход модели — docs/mocks-format.md, раздел 5 (эталон — model_inputs в mocks/check_mocks.py).
"""
import statistics
from dataclasses import dataclass
from datetime import date

from app.policy import policy, stop_factor


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month - (end.day < start.day)


def business_age_months(egrul: dict, today: date) -> int:
    return months_between(date.fromisoformat(egrul["state"]["registration_date"]), today)


def avg_turnover(bank: dict) -> float:
    # только очищенные поступления: переводы себе и полученные кредиты — не выручка
    return statistics.fmean(r["credit_net"] for r in bank["turnover_months"])


def current_payments(bki: dict) -> float:
    # нагрузку считаем только по БКИ: кредиты нашего банка там уже есть (не удваиваем с bank.own_loans)
    return sum(a["monthly_payment"] for a in bki["accounts"] if a["status"] == "ACTIVE" and a["relationship"] == "BORROWER")


def model_inputs(data: dict, new_payment: float, today: date) -> dict:
    """Вход модели PD в формате score.py. new_payment — платёж по новому кредиту по потолку ставки продукта."""
    egrul, fns, bank = data["egrul"], data["fns"], data["bank"]
    rows = bank["turnover_months"]
    net = [r["credit_net"] for r in rows]
    receipts = statistics.fmean(net)
    # оплаты физлиц картами — тысячи людей, а не один покупатель
    customers = [p["amount"] for p in bank["top_payers_12m"] if p["kind"] != "RETAIL_ACQUIRING"]
    inputs = {
        "business_age_years": (today - date.fromisoformat(egrul["state"]["registration_date"])).days / 365.25,
        "msp_category": (fns["msp_register"]["category"] or "").lower(),
        "okved_main": egrul["okved"],
        "monthly_receipts_rub": receipts,
        "monthly_operating_outflows_rub": statistics.fmean(r["debit_operating"] for r in rows),
        "existing_monthly_debt_service_rub": float(current_payments(data["bki"])),
        "new_monthly_debt_service_rub": new_payment,
        "receipts_growth_6m_pct": (statistics.fmean(net[-3:]) / statistics.fmean(net[-6:-3]) - 1) * 100,
        "receipts_cv_pct": statistics.pstdev(net) / receipts * 100,
        "cash_reserve_rub": float(bank["current_balance"]),
        "largest_customer_share_pct": max(customers, default=0) / sum(net) * 100,
    }
    fin = data.get("gir_bo")
    if egrul["type"] == "LEGAL" and fin:  # без отчётности модель юрлица не считается → M6
        lines = fin["lines"]
        inputs.update({
            "unit": "rub",
            "report_form": fin["report_form"].lower(),
            "assets": float(lines["1600"]),
            "equity": float(lines["1300"]),
            "current_assets": float(lines["1200"]),
            "current_liabilities": float(lines["1500"]),
            "revenue": float(lines["2110"]),
            "net_profit": float(lines["2400"]),
            "ordinary_expenses": None if lines["2120"] is None else float(lines["2120"]),
        })
    return inputs


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


def revenue_check(bank: dict, declared: float, statement: dict | None) -> Revenue:
    """Сверка анкеты и счёта (раздел 4.3 политики). Выписка подтверждает анкету, но лимит не увеличивает."""
    tol = policy()["data_mismatch"]["tolerance"]
    bank_annual = avg_turnover(bank) * 12
    ratio = declared / bank_annual - 1

    if ratio <= tol:
        return Revenue(bank_annual, declared, None, ratio, False, False)
    if statement is None:
        return Revenue(bank_annual, declared, None, ratio, True, False)

    statement_annual = statement["turnover"] * 12 / statement.get("months", 12)
    ratio_after = declared / (bank_annual + statement_annual) - 1
    # документ не снял расхождение — решает специалист (M4)
    return Revenue(bank_annual, declared, statement_annual, ratio_after, False, ratio_after > tol)
