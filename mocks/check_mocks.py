#!/usr/bin/env python3
"""Проверка тестовых данных моков.

Запуск:  python mocks/check_mocks.py
Нужно: Python 3.10+, PyYAML; модель задачи 2 в models/pd/<ip|ul>/ (model.json + score.py).

Для каждого файла в mocks/companies/ проверяет:
  1. Формат: разделы, допустимые значения, контрольные цифры ИНН/ОГРН, согласованность чисел
     (обороты и остатки по счёту, строка платёжной дисциплины, категория МСП, отчётность).
  2. Вход модели PD: собирает его из сырых данных мока (функция model_inputs — это и есть правило,
     по которому бэкенд готовит вход модели) и считает PD настоящим score.py задачи 2.
  3. Сценарий: компания проходит по пути заявки туда, куда задумано, по правилам
     config/decision_policy.yaml.

Это инструмент проверки данных, а не код продукта: политика здесь упрощённо повторяет
docs/decision-policy.md, чтобы поймать ошибку в данных до того, как её увидит жюри.
"""
import importlib.util
import json
import math
import statistics
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
POLICY = yaml.safe_load((ROOT / "config" / "decision_policy.yaml").read_text(encoding="utf-8"))
APP_DATE = date.fromisoformat(POLICY["model"]["application_date"])
L = POLICY["limits"]

# ---------- модель задачи 2 ----------

_spec = importlib.util.spec_from_file_location("pd_score", ROOT / "models" / "pd" / "ip" / "score.py")
SCORE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SCORE)
MODELS = {
    "INDIVIDUAL": json.loads((ROOT / POLICY["model"]["ip_path"]).read_text(encoding="utf-8")),
    "LEGAL": json.loads((ROOT / POLICY["model"]["ul_path"]).read_text(encoding="utf-8")),
}

ALLOWED = {
    "egrul.type": {"LEGAL", "INDIVIDUAL"},
    "egrul.state.status": {"ACTIVE", "LIQUIDATING", "LIQUIDATED", "BANKRUPT", "REORGANIZING"},
    "fns.tax_regime": {"OSNO", "USN", "PSN", "AUSN", "ESHN"},
    "fns.msp_category": {"MICRO", "SMALL", "MEDIUM", None},
    "zsk.risk_level": {"GREEN", "YELLOW", "RED"},
    "bki.account_type": {"BUSINESS_LOAN", "CREDIT_LINE", "OVERDRAFT", "LEASING", "CREDIT_CARD",
                         "CONSUMER_LOAN", "CAR_LOAN", "MORTGAGE"},
    "bki.relationship": {"BORROWER", "GUARANTOR"},
    "bki.creditor_kind": {"OWN_BANK", "OTHER_BANK", "MFO", "LEASING_COMPANY"},
    "bki.status": {"ACTIVE", "CLOSED", "SOLD", "WRITTEN_OFF"},
    "payer.kind": {"LEGAL", "INDIVIDUAL", "RETAIL_ACQUIRING"},
    "fin.report_form": {"FULL", "SIMPLIFIED"},
    "mock.mode": {"ok", "unavailable", "not_found", "timeout"},
    "payment_codes": set("01ABC2345789Z-"),
}
CODE_DAYS = {"A": 29, "B": 7, "C": 29, "2": 59, "3": 89, "4": 119, "5": 120}


# ---------- идентификаторы ----------

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


# ---------- деньги ----------

def annuity_payment(amount, rate, n):
    i = rate / 12
    return amount * i / (1 - (1 + i) ** -n)


def annuity_amount(payment, rate, n):
    i = rate / 12
    return payment * (1 - (1 + i) ** -n) / i


def stress_payment(product, amount, term):
    """Платёж по новому кредиту для модели и лимитов — по потолку ставки продукта."""
    prod = POLICY["products"][product]
    return annuity_payment(amount, prod["rate_cap"], term)


# ---------- вход модели из данных мока ----------

def existing_debt_service(d):
    """Действующие платежи по кредитам — только по БКИ (кредиты нашего банка там тоже есть)."""
    return sum(a["monthly_payment"] for a in d["bki"]["accounts"]
               if a["status"] == "ACTIVE" and a["relationship"] == "BORROWER")


def model_inputs(d, product, amount, term):
    """Сырые входы модели PD задачи 2 (формат score.py) из разделов мока.

    Это правило, по которому бэкенд готовит вход модели; описано в docs/mocks-format.md, раздел 5.
    """
    e, f, bank = d["egrul"], d["fns"], d["bank"]
    rows = bank["turnover_months"]
    net = [r["credit_net"] for r in rows]
    receipts = statistics.fmean(net)
    customers = [p for p in bank["top_payers_12m"] if p["kind"] != "RETAIL_ACQUIRING"]
    largest = max((p["amount"] for p in customers), default=0)
    inputs = {
        "business_age_years": (APP_DATE - date.fromisoformat(e["state"]["registration_date"])).days / 365.25,
        "msp_category": (f["msp_register"]["category"] or "").lower(),
        "okved_main": e["okved"],
        "monthly_receipts_rub": receipts,
        "monthly_operating_outflows_rub": statistics.fmean(r["debit_operating"] for r in rows),
        "existing_monthly_debt_service_rub": float(existing_debt_service(d)),
        "new_monthly_debt_service_rub": stress_payment(product, amount, term),
        "receipts_growth_6m_pct": (statistics.fmean(net[-3:]) / statistics.fmean(net[-6:-3]) - 1) * 100,
        "receipts_cv_pct": statistics.pstdev(net) / receipts * 100,
        "cash_reserve_rub": float(bank["current_balance"]),
        "largest_customer_share_pct": largest / sum(net) * 100,
    }
    if e["type"] == "LEGAL":
        fin = d["financials"]
        if fin is None:
            return inputs  # модель ЮЛ без отчётности не считается → REQUEST_DATA → к специалисту
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


def run_model(d, product, amount, term):
    inputs = model_inputs(d, product, amount, term)
    result = SCORE.score(inputs, MODELS[d["egrul"]["type"]])
    return inputs, result


# ---------- политика решения (упрощённый повтор docs/decision-policy.md) ----------

def lgd_of(product, amount, collateral):
    prod, g = POLICY["products"][product], POLICY["lgd"]
    if not prod["secured"] or not collateral:
        return g["unsecured"]
    secured = min(collateral["value"] * (1 - g["real_estate_haircut"]), amount)
    return (g["unsecured"] * (amount - secured) + g["secured_real_estate"] * secured) / amount


def pd_max_of(product, lgd):
    prod = POLICY["products"][product]
    return (prod["rate_cap"] - POLICY["market"]["key_rate"] - POLICY["pricing"]["bank_margin"]) / lgd


def grade_of(pd, pd_max):
    g = POLICY["risk_grades"]
    if pd < g["A"]["pd_below"]:
        return "A"
    if pd < g["B"]["pd_below"]:
        return "B"
    if pd < pd_max:
        return "C"
    return "D"


def rate_of(pd, product, lgd):
    prod = POLICY["products"][product]
    r = POLICY["market"]["key_rate"] + POLICY["pricing"]["bank_margin"] + pd * lgd
    r = min(max(r, prod["rate_floor"]), prod["rate_cap"])
    step = POLICY["pricing"]["rate_rounding"]
    return round(round(r / step) * step, 6)


def max_amount(d, product, term, collateral):
    """Наибольшая сумма на этот срок и что её ограничило."""
    prod = POLICY["products"][product]
    receipts = statistics.fmean(r["credit_net"] for r in d["bank"]["turnover_months"])
    existing = existing_debt_service(d)
    caps = {"product_max": prod["amount_max"]}
    by_new = L["max_new_payment_share"] * receipts
    by_total = L["max_total_debt_service_share"] * receipts - existing
    free, kind = (by_new, "new_payment") if by_new <= by_total else (by_total, "total_debt_service")
    caps[kind] = annuity_amount(free, prod["rate_cap"], term) if free > 0 else 0.0
    if "turnover_share" in prod:
        caps["turnover_share"] = prod["turnover_share"] * receipts
    if prod.get("max_ltv") and collateral:
        caps["collateral"] = prod["max_ltv"] * collateral["value"]
    binding = min(caps, key=caps.get)
    step = L["amount_rounding"]
    return int(caps[binding] // step * step), binding


def simulate(d):
    """Путь заявки (переходы), исход, причина и детали для автоматической части процесса."""
    sc, e, f = d["meta"]["scenario"], d["egrul"], d["fns"]
    product = sc["product"]
    prod = POLICY["products"][product]
    path, det = ["T01", "T02"], {}

    # VALIDATION
    if prod["secured"] and not sc.get("collateral"):
        return path + ["T04"], "INFO_REQUESTED", "V02_COLLATERAL", det
    path.append("T03")

    # CHECKS: стоп-факторы по всем источникам, которые ответили
    def up(section):
        return d[section].get("_mock", {}).get("mode", "ok") == "ok" if d[section] else True

    sf = []
    if e["state"]["status"] != "ACTIVE":
        sf.append("SF01_COMPANY_INACTIVE")
    if (up("bki") and any(a["status"] == "ACTIVE" and a["current_overdue_days"] > 0 for a in d["bki"]["accounts"])) \
            or any(x["current_overdue_days"] > 0 for x in d["bank"]["own_loans"]):
        sf.append("SF02_CURRENT_OVERDUE")
    threshold = next(s["tax_debt_threshold"] for s in POLICY["stop_factors"] if s["code"] == "SF03_TAX_DEBT")
    if f["tax_debt"]["amount"] > threshold or any(s["active"] for s in f["account_suspensions"]):
        sf.append("SF03_TAX_DEBT")
    reg = date.fromisoformat(e["state"]["registration_date"])
    if months_between(reg, APP_DATE) < prod["min_business_age_months"]:
        sf.append("SF04_BUSINESS_TOO_YOUNG")
    if d["zsk"]["risk_level"] == "RED":
        sf.append("SF05_ZSK_RED")
    if e.get("invalid"):
        sf.append("SF06_EGRUL_UNRELIABLE")
    det["stop_factors"] = sf
    if sf:
        return path + ["T08"], "REJECTED", sf[0], det
    if not all(up(s) for s in ("egrul", "fns", "zsk", "bki", "bank")):
        return path + ["T09"], "MANUAL_REVIEW", "M5_CHECKS_INCOMPLETE", det

    # CHECKS: сверка анкеты со счётом (лимиты и модель всегда по данным нашего счёта)
    tol = POLICY["data_mismatch"]["tolerance"]
    bank_annual = sum(r["credit_net"] for r in d["bank"]["turnover_months"]) * 12 / len(d["bank"]["turnover_months"])
    mismatch_unresolved = False
    det["mismatch"] = round(sc["declared_revenue_12m"] / bank_annual - 1, 3)
    if det["mismatch"] > tol:
        doc = sc.get("document_on_request")
        if not doc:
            return path + ["T22"], "INFO_REQUESTED", "DATA_MISMATCH", det
        path += ["T22", "T05", "T03"]
        det["mismatch_after_document"] = round(sc["declared_revenue_12m"] / (bank_annual + doc["turnover_12m"]) - 1, 3)
        mismatch_unresolved = det["mismatch_after_document"] > tol
    path.append("T07")

    # SCORING
    if f["msp_register"]["category"] not in POLICY["msp"]["allowed_categories"]:
        return path + ["T12"], "MANUAL_REVIEW", "M8_OUT_OF_MODEL_SCOPE", det
    req, term, coll = sc["amount"], sc["term_months"], sc.get("collateral")
    limit, binding = max_amount(d, product, term, coll)
    det.update(limit_at_requested_term=limit, limit_binding=binding)
    if req <= limit:
        offer = ("AS_REQUESTED", req, term)
    else:
        offer = None
        step = L["term_step_months"]
        grid = sorted({t for t in range(step, prod["term_months_max"] + 1, step) if t > term}
                      | ({prod["term_months_max"]} - {term}))
        for t in grid:
            if max_amount(d, product, t, coll)[0] >= req:
                offer = ("TERM_EXTENDED", req, t)
                break
        if offer is None:
            if limit < prod["amount_min"] or limit < L["min_counter_offer_share"] * req:
                return path + ["T13"], "REJECTED", "NO_VIABLE_OFFER", det
            offer = ("AMOUNT_REDUCED", limit, term)
    kind, amount, t = offer

    inputs, result = run_model(d, product, amount, t)
    if result["status"] != "SYNTHETIC_SIMULATOR":
        det["model_errors"] = result["errors"]
        return path + ["T12"], "MANUAL_REVIEW", "M6_MODEL_UNAVAILABLE", det
    pd = result["pd_probability"]
    lgd = lgd_of(product, amount, coll)
    pdm = pd_max_of(product, lgd)
    grade = grade_of(pd, pdm)
    risk_factors = sorted((x for x in result["contribution_details"] if x["logit_contribution"] > 0),
                          key=lambda x: -x["logit_contribution"])[:2]
    det["model"] = {
        "segment": result["segment"], "model_id": result["model_id"], "pd": pd, "grade": grade,
        "lgd": round(lgd, 4), "product_pd_max": round(pdm, 4), "inputs": inputs,
        "top_risk_factors": [x["feature"] for x in risk_factors],
        "clipped_features": [w["feature"] for w in result["clipping_warnings"]],
    }
    if grade == "D":
        return path + ["T13"], "REJECTED", "HIGH_RISK", det
    rate = rate_of(pd, product, lgd)
    pay = annuity_payment(amount, rate, t)
    det["offer"] = {"type": kind, "amount": amount, "term_months": t, "rate": rate,
                    "monthly_payment": round(pay), "limit_binding": binding}

    manual = []
    if grade == "C":
        manual.append("M1_GREY_ZONE")
    if req > POLICY["manual_review"]["auto_approval_max_amount"]:
        manual.append("M2_LARGE_AMOUNT")
    if prod["secured"]:
        manual.append("M3_COLLATERAL")
    if mismatch_unresolved:
        manual.append("M4_DATA_MISMATCH")
    det["manual_triggers"] = manual
    if manual:
        return path + ["T12"], "MANUAL_REVIEW", manual, det
    if kind == "AS_REQUESTED":
        return path + ["T10"], "AUTO_APPROVED", None, det
    return path + ["T11"], "COUNTER_OFFER", kind, det


# ---------- проверка формата ----------

def check_format(d, errs):
    for key in ("format_version", "meta", "egrul", "fns", "zsk", "bki", "bank", "financials"):
        if key not in d:
            errs.append(f"нет раздела {key}")
            return
    e, f, z, b, bank, fin = d["egrul"], d["fns"], d["zsk"], d["bki"], d["bank"], d["financials"]

    def allowed(value, key):
        if value not in ALLOWED[key]:
            errs.append(f"{key}: недопустимое значение {value!r}")

    allowed(e["type"], "egrul.type")
    allowed(e["state"]["status"], "egrul.state.status")
    allowed(f["tax_regime"], "fns.tax_regime")
    allowed(f["msp_register"]["category"], "fns.msp_category")
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

    # категория МСП по 209-ФЗ: микро — до 15 человек и 120 млн ₽ дохода, малое — до 100 и 800 млн
    cat, emp = f["msp_register"]["category"], f["employee_count"]
    income = fin["lines"]["2110"] if fin else sum(r["credit_net"] for r in bank["turnover_months"])
    expected_cat = "MICRO" if emp <= 15 and income <= 120e6 else "SMALL" if emp <= 100 and income <= 800e6 else "MEDIUM"
    if cat != expected_cat:
        errs.append(f"категория МСП {cat}, а по численности {emp} и доходу должна быть {expected_cat}")

    # бухгалтерская отчётность: есть у юрлица, нет у ИП
    if e["type"] == "INDIVIDUAL" and fin is not None:
        errs.append("у ИП нет бухгалтерской отчётности: financials должен быть null")
    if fin:
        allowed(fin["report_form"], "fin.report_form")
        ln = fin["lines"]
        for k, v in ln.items():
            if v is not None and (not isinstance(v, int) or v % 1000):
                errs.append(f"отчётность, строка {k}: ожидается целое число рублей, кратное 1000")
        if ln["1200"] > ln["1600"]:
            errs.append("оборотные активы (1200) больше активов (1600)")
        if ln["1600"] <= 0 or ln["1500"] <= 0 or ln["2110"] <= 0:
            errs.append("активы, краткосрочные обязательства и выручка должны быть больше нуля")

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

    rows = bank["turnover_months"]
    months = [r["month"] for r in rows]
    if months != sorted(months) or months[-1] != "2026-09" or not 6 <= len(months) <= 12:
        errs.append("обороты: месяцы должны идти подряд и заканчиваться 2026-09")
    prev_close = None
    for r in rows:
        if r["credit_total"] != r["credit_net"] + sum(r["excluded"].values()):
            errs.append(f"обороты {r['month']}: credit_total ≠ credit_net + исключённые поступления")
        if r["debit_total"] != r["debit_operating"] + r["debit_debt_service"] + r["debit_own_transfers"]:
            errs.append(f"обороты {r['month']}: debit_total ≠ сумма списаний по видам")
        if r["balance_close"] != r["balance_open"] + r["credit_total"] - r["debit_total"]:
            errs.append(f"обороты {r['month']}: остаток на конец ≠ начало + поступления − списания")
        if prev_close is not None and r["balance_open"] != prev_close:
            errs.append(f"обороты {r['month']}: остаток на начало ≠ остатку на конец прошлого месяца")
        if r["balance_close"] < 0:
            errs.append(f"обороты {r['month']}: отрицательный остаток")
        prev_close = r["balance_close"]
    total_net = sum(r["credit_net"] for r in rows)
    payers = bank["top_payers_12m"]
    for p in payers:
        allowed(p["kind"], "payer.kind")
        if abs(p["share"] - round(p["amount"] / total_net, 4)) > 1e-9:
            errs.append(f"плательщик {p['name']}: доля не совпадает с суммой")
    if [p["amount"] for p in payers] != sorted((p["amount"] for p in payers), reverse=True):
        errs.append("плательщики должны идти по убыванию суммы")
    if sum(p["amount"] for p in payers) > total_net:
        errs.append("сумма крупнейших плательщиков больше всех очищенных поступлений")
    for loan in bank["own_loans"]:
        a = uids.get(loan["contract_uid"])
        if not a or a["creditor_kind"] != "OWN_BANK":
            errs.append(f"кредит банка {loan['contract_uid'][:8]} не найден в БКИ как OWN_BANK")
        elif a["monthly_payment"] != loan["monthly_payment"] or a["outstanding"] != loan["outstanding"]:
            errs.append(f"кредит банка {loan['contract_uid'][:8]}: данные расходятся с БКИ")


def _same(a, b):
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9)
    return a == b


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
            print(f"✗ {file.name}")
            for x in errs:
                print("   -", x)
            total_errors += len(errs)
            continue
        inn = d["egrul"]["inn"]
        if inn in inns:
            errs.append(f"ИНН {inn} повторяется")
        inns.add(inn)
        if not file.name.endswith(f"_{inn}.json"):
            errs.append("имя файла не содержит ИНН компании")

        path, outcome, reason, det = simulate(d)
        exp = d["meta"]["expected"]
        if exp["path"][:len(path)] != path:
            errs.append(f"путь {path} не совпадает с ожидаемым {exp['path']}")
        if outcome != exp["outcome"]:
            errs.append(f"исход {outcome}, ожидался {exp['outcome']}")
        if exp["reason"] not in (reason if isinstance(reason, list) else [reason]):
            errs.append(f"причина {reason}, ожидалась {exp['reason']}")
        model = det.get("model")
        if exp["grade"] != (model["grade"] if model else None):
            errs.append(f"класс риска {model['grade'] if model else None}, задуман {exp['grade']}")
        stored = exp.get("model")
        if (stored is None) != (model is None):
            errs.append("meta.expected.model не соответствует пересчёту (есть/нет оценки)")
        elif model:
            if not _same(stored["pd"], model["pd"]):
                errs.append(f"PD в meta {stored['pd']}, пересчёт {model['pd']}")
            for k, v in model["inputs"].items():
                if not _same(stored["inputs"].get(k), v):
                    errs.append(f"вход модели {k}: в meta {stored['inputs'].get(k)}, пересчёт {v}")
        if exp.get("offer") != det.get("offer"):
            errs.append(f"предложение в meta {exp.get('offer')} ≠ пересчёт {det.get('offer')}")

        mark = "✓" if not errs else "✗"
        pd_txt = f"PD {model['pd']:6.2%} [{model['grade']}]" if model else " " * 15
        o = det.get("offer")
        offer_txt = (f"{o['amount']:,} ₽ / {o['term_months']} мес / {o['rate']:.1%} / {o['monthly_payment']:,} ₽"
                     .replace(",", " ") if o and outcome != "REJECTED" else "")
        print(f"{mark} {d['meta']['id']}  {outcome:<14} {str(reason):<36} {pd_txt}  {offer_txt}")
        for x in errs:
            print("   -", x)
        total_errors += len(errs)
    print(f"\nКомпаний: {len(files)}, ошибок: {total_errors}")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
