"""
Слой 3 — кредитная политика: лимит, подбор условий, PD на этих условиях, ставка, кто решает.
Порядок шагов — docs/decision-policy.md, раздел 6.1. Все числа — config/decision_policy.yaml.
Эталон расчёта на тех же данных — simulate в mocks/check_mocks.py.
"""
from dataclasses import dataclass, field
from datetime import date

from app import texts
from app.features import Revenue, avg_turnover, current_payments, model_inputs
from app.pd_model import ModelUnavailable, predict
from app.policy import policy, product as product_policy


@dataclass
class Request:
    product_code: str
    amount: int
    term_months: int
    is_legal: bool
    collateral_value: int | None
    reviewed_before: bool  # заявка уже была у специалиста (M7)


@dataclass
class Offer:
    kind: str  # AS_REQUESTED / TERM_EXTENDED / AMOUNT_REDUCED
    amount: int
    term_months: int
    rate: float  # доля, 0.174
    monthly_payment: int
    alternatives: list = field(default_factory=list)
    conditions: list = field(default_factory=list)
    reason: str = ""
    advice: str = ""


@dataclass
class Result:
    outcome: str  # AUTO_APPROVED, COUNTER_OFFER, MANUAL_REVIEW, REJECTED
    features: dict = field(default_factory=dict)  # признаки модели
    model_inputs: dict = field(default_factory=dict)  # сырой вход score.py — по нему решение можно пересчитать
    pd: float | None = None
    pd_at_requested_terms: float | None = None
    grade: str | None = None
    lgd: float | None = None
    product_pd_max: float | None = None
    contributions: dict = field(default_factory=dict)
    clipping_warnings: list = field(default_factory=list)
    model_version: str | None = None
    rate: float | None = None
    max_amount: int | None = None
    limit_binding: str | None = None
    offer: Offer | None = None  # для MANUAL_REVIEW — рекомендация специалисту
    manual_triggers: list = field(default_factory=list)
    reason_codes: list = field(default_factory=list)
    reason: str = ""
    advice: str = ""
    comment: str | None = None  # для специалиста


# ---------- деньги ----------

def annuity_factor(rate: float, term: int) -> float:
    i = rate / 12
    return (1 - (1 + i) ** -term) / i


def payment(amount: float, rate: float, term: int) -> int:
    # овердрафт тоже как 12 равных платежей — так устроен сценарий, на котором обучена модель
    return round(amount / annuity_factor(rate, term))


def stress_payment(prod: dict, amount: float, term: int) -> float:
    """Платёж по новому кредиту для модели и лимитов — по потолку ставки продукта (раздел 5.3)."""
    return amount / annuity_factor(prod["rate_cap"], term)


# ---------- риск и цена ----------

def lgd_of(prod: dict, amount: int, collateral: int | None) -> float:
    """LGD по Базель III: 40% без обеспечения, 20% на часть, покрытую залогом после дисконта."""
    g = policy()["lgd"]
    if not prod["secured"] or not collateral:
        return g["unsecured"]
    secured = min(collateral * (1 - g["real_estate_haircut"]), amount)
    return (g["unsecured"] * (amount - secured) + g["secured_real_estate"] * secured) / amount


def pd_max_of(prod: dict, lgd: float) -> float:
    """PD, при которой ставка упирается в потолок продукта: выше риск не покрыть рыночной ставкой."""
    p = policy()
    return (prod["rate_cap"] - p["market"]["key_rate"] - p["pricing"]["bank_margin"]) / lgd


def grade_of(pd: float, pd_max: float) -> str:
    g = policy()["risk_grades"]
    if pd < g["A"]["pd_below"]:
        return "A"
    if pd < g["B"]["pd_below"]:
        return "B"
    return "C" if pd < pd_max else "D"


def rate_of(pd: float, prod: dict, lgd: float) -> float:
    """Ставка = ключевая + маржа + PD × LGD, в коридоре продукта, с шагом 0,1 п.п."""
    p = policy()
    r = p["market"]["key_rate"] + p["pricing"]["bank_margin"] + pd * lgd
    step = p["pricing"]["rate_rounding"]
    return round(round(min(max(r, prod["rate_floor"]), prod["rate_cap"]) / step) * step, 4)


# ---------- лимит и подбор условий ----------

def max_amount(prod: dict, term: int, receipts: float, existing: float, collateral: int | None):
    """Лимит = минимум из ограничений (раздел 6.3); какое сработало — объясняет клиенту контрпредложение."""
    limits = policy()["limits"]
    caps = {"product_max": prod["amount_max"]}
    by_new = limits["max_new_payment_share"] * receipts
    by_total = limits["max_total_debt_service_share"] * receipts - existing
    free, kind = (by_new, "new_payment") if by_new <= by_total else (by_total, "total_debt_service")
    caps[kind] = free * annuity_factor(prod["rate_cap"], term) if free > 0 else 0.0
    if "turnover_share" in prod:
        caps["turnover_share"] = prod["turnover_share"] * receipts
    if prod.get("max_ltv") and collateral:
        caps["collateral"] = prod["max_ltv"] * collateral
    binding = min(caps, key=caps.get)
    rounding = limits["amount_rounding"]
    return int(caps[binding] // rounding * rounding), binding


def pick_terms(req: Request, prod: dict, receipts: float, existing: float):
    """Подбор условий (раздел 6.4): та же сумма → больше срок → меньше сумма. None — предложить нечего."""
    limits = policy()["limits"]
    limit, binding = max_amount(prod, req.term_months, receipts, existing, req.collateral_value)
    if req.amount <= limit:
        return ("AS_REQUESTED", req.amount, req.term_months), limit, binding, []

    step = limits["term_step_months"]
    longer = sorted({t for t in range(step, prod["term_months_max"] + 1, step) if t > req.term_months}
                    | ({prod["term_months_max"]} - {req.term_months}))
    for term in longer:
        if max_amount(prod, term, receipts, existing, req.collateral_value)[0] >= req.amount:
            return ("TERM_EXTENDED", req.amount, term), limit, binding, []

    if limit < prod["amount_min"] or limit < limits["min_counter_offer_share"] * req.amount:
        return None, limit, binding, []
    # вариант на максимальный срок, если он заметно больше
    alternatives = []
    if longer:
        alt, _ = max_amount(prod, longer[-1], receipts, existing, req.collateral_value)
        if alt >= limit * 1.1:
            alternatives.append((alt, longer[-1]))
    return ("AMOUNT_REDUCED", limit, req.term_months), limit, binding, alternatives


def weak_factors(contributions: dict) -> list[str]:
    """Один-два признака, которые сильнее всего подняли риск."""
    worst = [f for v, f in sorted(((v, f) for f, v in contributions.items() if v > 0), reverse=True)[:2]]
    return worst or ["debt_coverage"]


# ---------- решение ----------

def decide(req: Request, data: dict, revenue: Revenue, today: date) -> Result:
    p = policy()
    prod = product_policy(req.product_code)
    res = Result("MANUAL_REVIEW")
    receipts = avg_turnover(data["bank"])  # модель и лимиты — всегда по нашему счёту (раздел 4.3)
    existing = current_payments(data["bki"])

    # шаг 1: бизнес вне области модели
    if data["fns"]["msp_register"]["category"] not in p["msp"]["allowed_categories"]:
        res.manual_triggers = ["M8_OUT_OF_MODEL_SCOPE"]
        return res

    # шаг 2: лимит и условия
    terms, res.max_amount, res.limit_binding, alternatives = pick_terms(req, prod, receipts, existing)
    if terms is None:
        res.outcome, res.reason_codes = "REJECTED", ["NO_VIABLE_OFFER"]
        res.reason = texts.LIMIT_REASONS[res.limit_binding][0]
        res.advice = texts.NO_VIABLE_OFFER_ADVICE
        return review_instead(res) if req.reviewed_before else res
    kind, amount, term = terms

    # шаг 3: PD на подобранных условиях
    try:
        res.model_inputs = model_inputs(data, stress_payment(prod, amount, term), today)
        model = predict(res.model_inputs, req.is_legal)
        if kind != "AS_REQUESTED":  # для объяснения: какой была бы оценка на запрошенных условиях
            asked = model_inputs(data, stress_payment(prod, req.amount, req.term_months), today)
            res.pd_at_requested_terms = predict(asked, req.is_legal)["pd"]
    except ModelUnavailable as e:
        res.manual_triggers, res.comment = ["M6_MODEL_UNAVAILABLE"], f"модель: {e}"
        return res
    res.pd, res.features, res.contributions = model["pd"], model["features"], model["contributions"]
    res.clipping_warnings, res.model_version = model["clipping_warnings"], model["model_version"]
    res.lgd = lgd_of(prod, amount, req.collateral_value)
    res.product_pd_max = pd_max_of(prod, res.lgd)
    res.grade = grade_of(res.pd, res.product_pd_max)

    # шаг 4: риск нельзя покрыть рыночной ставкой — отказ
    if res.grade == "D":
        weak = weak_factors(res.contributions)
        res.outcome, res.reason_codes = "REJECTED", ["HIGH_RISK"]
        res.reason = texts.HIGH_RISK.format(weak=", ".join(dict.fromkeys(texts.weak_factor(f) for f in weak)))
        res.advice = texts.weak_factor_advice(weak[0])
        return review_instead(res) if req.reviewed_before else res

    res.rate = rate_of(res.pd, prod, res.lgd)
    conditions = [texts.OWNER_GUARANTEE] if req.is_legal and not prod["secured"] else []
    res.offer = Offer(kind, amount, term, res.rate, payment(amount, res.rate, term), conditions=conditions,
                      alternatives=[{"amount": a, "term_months": t, "monthly_payment": payment(a, res.rate, t)}
                                    for a, t in alternatives])
    if kind == "TERM_EXTENDED":
        reason, res.offer.advice = texts.TERM_EXTENDED
        res.offer.reason = reason.format(term=req.term_months)
    elif kind == "AMOUNT_REDUCED":
        res.offer.reason, res.offer.advice = texts.LIMIT_REASONS[res.limit_binding]

    # шаг 5: кому решать
    triggers = []
    if res.grade == "C":
        triggers.append("M1_GREY_ZONE")
    if req.amount > p["manual_review"]["auto_approval_max_amount"]:
        triggers.append("M2_LARGE_AMOUNT")
    if prod["secured"]:
        triggers.append("M3_COLLATERAL")
    if revenue.unresolved:
        triggers.append("M4_DATA_MISMATCH")
    if req.reviewed_before:
        triggers.append("M7_REVIEWED_BEFORE")
    if triggers:
        res.outcome, res.manual_triggers = "MANUAL_REVIEW", triggers
        return res

    # шаги 6–7
    if kind == "AS_REQUESTED":
        res.outcome = "AUTO_APPROVED"
    else:
        res.outcome, res.reason_codes = "COUNTER_OFFER", [kind]
        res.reason, res.advice = res.offer.reason, res.offer.advice
    return res


def review_instead(res: Result) -> Result:
    """Заявку уже смотрел специалист: автоматика не перезаписывает решение человека — отдаём ему с рекомендацией."""
    res.manual_triggers = ["M7_REVIEWED_BEFORE"]
    res.outcome = "MANUAL_REVIEW"
    return res
