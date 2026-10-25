#!/usr/bin/env python3
"""Проверка тестовых данных моков.

Запуск:  python mocks/check_mocks.py
Что проверяет для каждого файла в mocks/companies/:
  1. Формат: обязательные разделы, допустимые значения, контрольные цифры ИНН/ОГРН,
     согласованность чисел (обороты, коды платёжной дисциплины, кредиты банка в БКИ).
  2. Признаки F1–F6 в meta.expected совпадают с пересчётом из данных.
  3. Сценарий: компания проходит по пути заявки ровно туда, куда задумано.
     Правила берутся из config/decision_policy.yaml, PD — допущение из meta.expected.assumed_pd
     (в системе его выдаёт модель задачи 2).

Это инструмент проверки данных, а не код продукта: правила здесь упрощённо повторяют
docs/decision-policy.md, чтобы поймать ошибку в данных до того, как её увидит жюри.
"""
import json
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
POLICY = yaml.safe_load((ROOT / "config" / "decision_policy.yaml").read_text(encoding="utf-8"))
REPORT_DATE = date(2026, 10, 24)

ALLOWED = {
    "egrul.type": {"LEGAL", "INDIVIDUAL"},
    "egrul.state.status": {"ACTIVE", "LIQUIDATING", "LIQUIDATED", "BANKRUPT", "REORGANIZING"},
    "fns.tax_regime": {"OSNO", "USN", "PSN", "AUSN", "ESHN"},
    "zsk.risk_level": {"GREEN", "YELLOW", "RED"},
    "bki.account_type": {"BUSINESS_LOAN", "CREDIT_LINE", "OVERDRAFT", "LEASING", "CREDIT_CARD",
                         "CONSUMER_LOAN", "CAR_LOAN", "MORTGAGE"},
    "bki.relationship": {"BORROWER", "GUARANTOR"},
    "bki.creditor_kind": {"OWN_BANK", "OTHER_BANK", "MFO", "LEASING_COMPANY"},
    "bki.status": {"ACTIVE", "CLOSED", "SOLD", "WRITTEN_OFF"},
    "mock.mode": {"ok", "unavailable", "not_found", "timeout"},
    "payment_codes": set("01ABC234578 9Z-".replace(" ", "")),
}
CODE_DAYS = {"A": 29, "B": 7, "C": 29, "2": 59, "3": 89, "4": 119, "5": 120}


def _ctrl(digits, weights):
    return sum(int(d) * w for d, w in zip(digits, weights)) % 11 % 10


def inn_ok(inn):
    if len(inn) == 10:
        return int(inn[9]) == _ctrl(inn, [2, 4, 10, 3, 5, 9, 4, 6, 8])
    if len(inn) == 12:
        c1 = _ctrl(inn, [7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
        c2 = _ctrl(inn[:11], [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8])
        return int(inn[10]) == c1 and int(inn[11]) == c2
    return False


def ogrn_ok(ogrn):
    if len(ogrn) == 13:
        return int(ogrn[12]) == int(ogrn[:12]) % 11 % 10
    if len(ogrn) == 15:
        return int(ogrn[14]) == int(ogrn[:14]) % 13 % 10
    return False


def months_between(d1, d2):
    return (d2.year - d1.year) * 12 + (d2.month - d1.month) - (1 if d2.day < d1.day else 0)


# ---------- проверка формата ----------

def check_format(d, errs):
    for key in ("format_version", "meta", "egrul", "fns", "zsk", "bki", "bank"):
        if key not in d:
            errs.append(f"нет раздела {key}")
            return
    e, f, z, b, bank = d["egrul"], d["fns"], d["zsk"], d["bki"], d["bank"]

    def allowed(value, key):
        if value not in ALLOWED[key]:
            errs.append(f"{key}: недопустимое значение {value!r}")

    allowed(e["type"], "egrul.type")
    allowed(e["state"]["status"], "egrul.state.status")
    allowed(f["tax_regime"], "fns.tax_regime")
    allowed(z["risk_level"], "zsk.risk_level")
    if not inn_ok(e["inn"]):
        errs.append(f"ИНН {e['inn']}: неверные контрольные цифры")
    if (e["type"] == "LEGAL") != (len(e["inn"]) == 10):
        errs.append("длина ИНН не соответствует типу (юрлицо — 10, ИП — 12)")
    if not ogrn_ok(e["ogrn"]):
        errs.append(f"ОГРН {e['ogrn']}: неверная контрольная цифра")
    if e["type"] == "LEGAL":
        if e["kpp"][:4] != e["inn"][:4]:
            errs.append("КПП не согласован с ИНН")
        for person in [e["management"]] + e["founders"]:
            if not inn_ok(person["inn"]):
                errs.append(f"ИНН физлица {person['inn']}: неверные контрольные цифры")
    if b["subject"]["inn"] != e["inn"]:
        errs.append("ИНН в БКИ не совпадает с ЕГРЮЛ")
    for section in (e, f, z, b, bank):
        if "_mock" in section:
            allowed(section["_mock"]["mode"], "mock.mode")

    uids = {}
    for a in b["accounts"]:
        for key in ("account_type", "relationship", "creditor_kind", "status"):
            allowed(a[key], "bki." + key)
        if not set(a["payment_string"]) <= ALLOWED["payment_codes"]:
            errs.append(f"договор {a['contract_uid'][:8]}: неизвестный код в строке платежей")
        counts = {"d30_59": a["payment_string"].count("2"), "d60_89": a["payment_string"].count("3"),
                  "d90_plus": a["payment_string"].count("4") + a["payment_string"].count("5")}
        if counts != a["overdue_counts_24m"]:
            errs.append(f"договор {a['contract_uid'][:8]}: счётчики просрочек не совпадают со строкой платежей")
        if (a["current_overdue_days"] > 0) != (a["overdue_amount"] > 0):
            errs.append(f"договор {a['contract_uid'][:8]}: дни и сумма текущей просрочки не согласованы")
        if a["status"] != "ACTIVE" and (a["outstanding"] or a["monthly_payment"]):
            errs.append(f"договор {a['contract_uid'][:8]}: у закрытого договора есть долг или платёж")
        uids[a["contract_uid"]] = a

    months = [r["month"] for r in bank["turnover_months"]]
    if months != sorted(months) or months[-1] != "2026-09" or not 1 <= len(months) <= 12:
        errs.append("обороты: месяцы должны идти подряд и заканчиваться 2026-09")
    for r in bank["turnover_months"]:
        if r["credit_total"] != r["credit_net"] + sum(r["excluded"].values()):
            errs.append(f"обороты {r['month']}: credit_total ≠ credit_net + исключённые поступления")
    for loan in bank["own_loans"]:
        a = uids.get(loan["contract_uid"])
        if not a or a["creditor_kind"] != "OWN_BANK":
            errs.append(f"кредит банка {loan['contract_uid'][:8]} не найден в БКИ как OWN_BANK")
        elif a["monthly_payment"] != loan["monthly_payment"] or a["outstanding"] != loan["outstanding"]:
            errs.append(f"кредит банка {loan['contract_uid'][:8]}: данные расходятся с БКИ")


# ---------- признаки ----------

def features(d, turnover_override=None):
    reg = date.fromisoformat(d["egrul"]["state"]["registration_date"])
    rows = d["bank"]["turnover_months"]
    avg = sum(r["credit_net"] for r in rows) / len(rows)
    cv = (sum((r["credit_net"] - avg) ** 2 for r in rows) / len(rows)) ** 0.5 / avg
    accs = d["bki"]["accounts"]
    existing = sum(a["monthly_payment"] for a in accs if a["status"] == "ACTIVE" and a["relationship"] == "BORROWER")
    codes = "".join(a["payment_string"] for a in accs)
    amount = d["meta"]["scenario"]["amount"]
    return {
        "F1_business_age_months": months_between(reg, REPORT_DATE),
        "F2_avg_monthly_turnover": round(avg),
        "F3_turnover_cv": round(cv, 3),
        "F4_debt_load": round(existing / avg, 3),
        "F5_overdue_30plus_count_24m": sum(sum(a["overdue_counts_24m"].values()) for a in accs),
        "F5_max_overdue_days_24m": max([CODE_DAYS.get(c, 0) for c in codes] or [0]),
        "F6_amount_to_turnover": round(amount / avg, 2),
    }, avg, existing


# ---------- политика решения (упрощённый повтор docs/decision-policy.md) ----------

L = POLICY["limits"]


def grade_of(pd):
    for g in POLICY["risk_grades"]:
        if pd < g["pd_max"] or g["grade"] == "D":
            return g


def rate_of(pd, prod):
    r = POLICY["market"]["key_rate"] + POLICY["pricing"]["bank_margin"] + pd * prod["lgd"]
    return round(min(max(r, prod["rate_floor"]), prod["rate_cap"]), 3)


def max_amount(prod, rate, term, turnover, existing, collateral):
    caps = {"product_max": prod["amount_max"]}
    if prod["limit_rule"] == "turnover_share":
        caps["turnover_share"] = prod["turnover_share"] * turnover
    else:
        i = rate / 12
        free = L["max_debt_service_to_turnover"] * turnover - existing
        caps["payment_capacity"] = max(0.0, free) * (1 - (1 + i) ** -term) / i
        if "max_amount_to_monthly_turnover" in prod:
            caps["turnover_cap"] = prod["max_amount_to_monthly_turnover"] * turnover
        if prod.get("max_ltv") and collateral:
            caps["ltv"] = prod["max_ltv"] * collateral["value"]
    binding = min(caps, key=caps.get)
    return int(caps[binding] // L["amount_rounding"] * L["amount_rounding"]), binding


def payment(prod, amount, rate, term):
    if prod["limit_rule"] == "turnover_share":
        return round(amount * rate / 12)
    i = rate / 12
    return round(amount * i / (1 - (1 + i) ** -term))


def simulate(d):
    """Возвращает (путь переходов, исход, причина, детали) для автоматической части процесса."""
    sc, e, f = d["meta"]["scenario"], d["egrul"], d["fns"]
    prod = POLICY["products"][sc["product"]]
    path, details = ["T01", "T02"], {}

    # VALIDATION
    if sc["amount"] > POLICY["validation"]["financial_statements_required_above"] \
            and "financial_statements" not in sc["documents_at_submit"]:
        return path + ["T04"], "INFO_REQUESTED", "V03_FINANCIAL_STATEMENTS", details
    if prod["secured"] and not sc.get("collateral"):
        return path + ["T04"], "INFO_REQUESTED", "V02_COLLATERAL", details
    path.append("T03")

    # CHECKS: стоп-факторы по всем источникам, которые ответили
    feats, avg, existing = features(d)
    sf = []
    if e["state"]["status"] != "ACTIVE":
        sf.append("SF01_COMPANY_INACTIVE")
    bki_up = d["bki"].get("_mock", {}).get("mode", "ok") == "ok"
    if bki_up and any(a["status"] == "ACTIVE" and a["current_overdue_days"] > 0 for a in d["bki"]["accounts"]):
        sf.append("SF02_CURRENT_OVERDUE")
    if any(l["current_overdue_days"] > 0 for l in d["bank"]["own_loans"]) and "SF02_CURRENT_OVERDUE" not in sf:
        sf.append("SF02_CURRENT_OVERDUE")
    threshold = next(s["tax_debt_threshold"] for s in POLICY["stop_factors"] if s["code"] == "SF03_TAX_DEBT")
    if f["tax_debt"]["amount"] > threshold or any(s["active"] for s in f["account_suspensions"]):
        sf.append("SF03_TAX_DEBT")
    if feats["F1_business_age_months"] < prod["min_business_age_months"]:
        sf.append("SF04_BUSINESS_TOO_YOUNG")
    if d["zsk"]["risk_level"] == "RED":
        sf.append("SF05_ZSK_RED")
    if e.get("invalid"):
        sf.append("SF06_EGRUL_UNRELIABLE")
    details["stop_factors"] = sf
    if sf:
        return path + ["T08"], "REJECTED", sf[0], details
    if not bki_up:
        return path + ["T09"], "MANUAL_REVIEW", "M5_CHECKS_INCOMPLETE", details

    # CHECKS: сверка заявленной выручки с оборотами по счёту
    tol = POLICY["data_mismatch"]["tolerance"]
    bank_annual = avg * 12
    turnover = avg
    mismatch_unresolved = False
    ratio = sc["declared_revenue_12m"] / bank_annual - 1
    details["mismatch"] = round(ratio, 3)
    if ratio > tol:
        doc = sc.get("document_on_request")
        if not doc:
            return path + ["T22"], "INFO_REQUESTED", "DATA_MISMATCH", details
        path += ["T22", "T05", "T03"]
        verified = bank_annual + doc["turnover_12m"]
        ratio_after = sc["declared_revenue_12m"] / verified - 1
        details["mismatch_after_document"] = round(ratio_after, 3)
        if ratio_after <= tol:
            turnover = verified / 12
        else:
            mismatch_unresolved = True
    path.append("T07")

    # SCORING
    pd = d["meta"]["expected"]["assumed_pd"]
    g = grade_of(pd)
    details["grade"] = g["grade"]
    if g["route"] == "reject":
        return path + ["T13"], "REJECTED", "HIGH_RISK", details
    rate = rate_of(pd, prod)
    req, term = sc["amount"], sc["term_months"]
    mx, binding = max_amount(prod, rate, term, turnover, existing, sc.get("collateral"))
    details.update(rate=rate, limit=mx, limit_binding=binding)
    offer = None
    if req <= mx:
        offer = ("AS_REQUESTED", req, term)
    else:
        step = L["term_step_months"]
        grid = sorted({t for t in range(step, prod["term_months_max"] + 1, step) if t > term}
                      | ({prod["term_months_max"]} - {term}))
        for t in grid:
            if max_amount(prod, rate, t, turnover, existing, sc.get("collateral"))[0] >= req:
                offer = ("TERM_EXTENDED", req, t)
                break
        if offer is None:
            if mx < prod["amount_min"] or mx < L["min_counter_offer_share"] * req:
                return path + ["T13"], "REJECTED", "NO_VIABLE_OFFER", details
            offer = ("AMOUNT_REDUCED", mx, term)
    kind, amt, t = offer
    details["offer"] = {"type": kind, "amount": amt, "term": t, "rate": rate,
                        "payment": payment(prod, amt, rate, t)}

    manual = []
    if g["route"] == "manual":
        manual.append("M1_GREY_ZONE")
    if req > POLICY["manual_review"]["auto_approval_max_amount"]:
        manual.append("M2_LARGE_AMOUNT")
    if prod["secured"]:
        manual.append("M3_COLLATERAL")
    if mismatch_unresolved:
        manual.append("M4_DATA_MISMATCH")
    details["manual_triggers"] = manual
    if manual:
        return path + ["T12"], "MANUAL_REVIEW", manual, details
    if kind == "AS_REQUESTED":
        return path + ["T10"], "AUTO_APPROVED", None, details
    return path + ["T11"], "COUNTER_OFFER", kind, details


def main():
    files = sorted((ROOT / "mocks" / "companies").glob("*.json"))
    if not files:
        print("Нет файлов в mocks/companies")
        return 1
    total_errors, inns = 0, set()
    for file in files:
        d = json.loads(file.read_text(encoding="utf-8"))
        errs = []
        check_format(d, errs)
        if errs:
            print(f"✗ {file.name}"), [print("   -", x) for x in errs]
            total_errors += len(errs)
            continue
        inn = d["egrul"]["inn"]
        if inn in inns:
            errs.append(f"ИНН {inn} повторяется")
        inns.add(inn)
        if not file.name.endswith(f"_{inn}.json"):
            errs.append("имя файла не содержит ИНН компании")
        feats, _, _ = features(d)
        if feats != d["meta"]["expected"]["features"]:
            diff = {k: (v, d["meta"]["expected"]["features"].get(k)) for k, v in feats.items()
                    if d["meta"]["expected"]["features"].get(k) != v}
            errs.append(f"признаки в meta не совпадают с данными: {diff}")

        path, outcome, reason, det = simulate(d)
        exp = d["meta"]["expected"]
        if exp["path"][:len(path)] != path:
            errs.append(f"путь {path} не совпадает с ожидаемым {exp['path']}")
        if outcome != exp["outcome"]:
            errs.append(f"исход {outcome}, ожидался {exp['outcome']}")
        reasons = reason if isinstance(reason, list) else [reason]
        if exp["reason"] not in reasons:
            errs.append(f"причина {reason}, ожидалась {exp['reason']}")

        mark = "✓" if not errs else "✗"
        offer = det.get("offer")
        offer_txt = (f"{offer['amount']:,} ₽ / {offer['term']} мес / {offer['rate']:.1%} / платёж {offer['payment']:,} ₽"
                     .replace(",", " ") if offer and outcome != "REJECTED" else "")
        print(f"{mark} {d['meta']['id']}  {outcome:<14} {str(reason):<38} {offer_txt}")
        for x in errs:
            print("   -", x)
        total_errors += len(errs)
    print(f"\nКомпаний: {len(files)}, ошибок: {total_errors}")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
