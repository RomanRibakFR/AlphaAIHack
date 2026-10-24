"""
Слой 3 — кредитная политика: ставка, лимит, предложение, кто решает.
Порядок шагов — docs/decision-policy.md, раздел 6.1. Все числа — config/decision_policy.yaml.
"""
from dataclasses import dataclass, field
from datetime import date

from app import texts
from app.features import Revenue, current_payments, features
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
    features: dict = field(default_factory=dict)
    pd: float | None = None
    grade: str | None = None
    contributions: dict = field(default_factory=dict)
    model_version: str | None = None
    rate: float | None = None
    max_amount: int | None = None
    limit_binding: str | None = None
    offer: Offer | None = None  # для MANUAL_REVIEW — рекомендация специалисту
    manual_triggers: list = field(default_factory=list)
    reason_codes: list = field(default_factory=list)
    reason: str = ""
    advice: str = ""


def grade_of(pd: float) -> dict:
    return next(g for g in policy()["risk_grades"] if pd < g["pd_max"] or g["grade"] == "D")


def rate_of(pd: float, prod: dict) -> float:
    """Ставка = ключевая + маржа + PD × LGD, в границах продукта, с шагом 0,1 п.п."""
    p = policy()
    r = p["market"]["key_rate"] + p["pricing"]["bank_margin"] + pd * prod["lgd"]
    step = p["pricing"]["rate_rounding"]
    return round(round(min(max(r, prod["rate_floor"]), prod["rate_cap"]) / step) * step, 4)


def annuity_factor(rate: float, term: int) -> float:
    i = rate / 12
    return (1 - (1 + i) ** -term) / i


def payment(prod: dict, amount: int, rate: float, term: int) -> int:
    if prod["limit_rule"] == "turnover_share":  # по овердрафту платим проценты, тело — в конце срока
        return round(amount * rate / 12)
    return round(amount / annuity_factor(rate, term))


def max_amount(prod: dict, rate: float, term: int, turnover: float, existing: float, collateral: int | None):
    """Лимит = минимум из ограничений; какое ограничение сработало — объясняет клиенту контрпредложение."""
    limits = policy()["limits"]
    caps = {"product_max": prod["amount_max"]}
    if prod["limit_rule"] == "turnover_share":
        caps["turnover_share"] = prod["turnover_share"] * turnover
    else:
        free = limits["max_debt_service_to_turnover"] * turnover - existing
        caps["payment_capacity"] = max(0.0, free) * annuity_factor(rate, term)
        if "max_amount_to_monthly_turnover" in prod:
            caps["turnover_cap"] = prod["max_amount_to_monthly_turnover"] * turnover
        if prod.get("max_ltv") and collateral:
            caps["ltv"] = prod["max_ltv"] * collateral
    binding = min(caps, key=caps.get)
    rounding = limits["amount_rounding"]
    return int(caps[binding] // rounding * rounding), binding


def make_offer(req: Request, prod: dict, rate: float, turnover: float, existing: float):
    """Предложение по разделу 6.4: та же сумма → больше срок → меньше сумма. None — предложить нечего."""
    limits = policy()["limits"]
    limit, binding = max_amount(prod, rate, req.term_months, turnover, existing, req.collateral_value)
    conditions = [texts.OWNER_GUARANTEE] if req.is_legal and not prod["secured"] else []

    def offer(kind, amount, term, **kw):
        return Offer(kind, amount, term, rate, payment(prod, amount, rate, term), conditions=conditions, **kw)

    if req.amount <= limit:
        return offer("AS_REQUESTED", req.amount, req.term_months), limit, binding

    step = limits["term_step_months"]
    longer = sorted({t for t in range(step, prod["term_months_max"] + 1, step) if t > req.term_months}
                    | ({prod["term_months_max"]} - {req.term_months}))
    for term in longer:
        if max_amount(prod, rate, term, turnover, existing, req.collateral_value)[0] >= req.amount:
            reason, advice = texts.TERM_EXTENDED
            return offer("TERM_EXTENDED", req.amount, term, reason=reason.format(term=req.term_months), advice=advice), limit, binding

    if limit < prod["amount_min"] or limit < limits["min_counter_offer_share"] * req.amount:
        return None, limit, binding

    reason, advice = texts.LIMIT_REASONS[binding]
    alternatives = []
    if longer:
        alt, _ = max_amount(prod, rate, longer[-1], turnover, existing, req.collateral_value)
        if alt >= limit * 1.1:  # вариант на максимальный срок, если он заметно больше
            alternatives.append({"amount": alt, "term_months": longer[-1], "monthly_payment": payment(prod, alt, rate, longer[-1])})
    return offer("AMOUNT_REDUCED", limit, req.term_months, alternatives=alternatives, reason=reason, advice=advice), limit, binding


def weak_factors(contributions: dict) -> list[str]:
    """Один-два признака, которые сильнее всего подняли риск."""
    worst = [f for v, f in sorted(((v, f) for f, v in contributions.items() if v > 0), reverse=True)[:2]]
    return worst or ["F4"]


def decide(req: Request, data: dict, revenue: Revenue, today: date) -> Result:
    prod = product_policy(req.product_code)
    feats = features(data["egrul"], data["bki"], data["bank"], req.amount, today)
    res = Result("MANUAL_REVIEW", features=feats)

    # шаг 1: модель
    try:
        model = predict(feats)
    except ModelUnavailable:
        res.manual_triggers = ["M6_MODEL_UNAVAILABLE"]
        return res
    res.pd, res.contributions, res.model_version = model["pd"], model["contributions"], model["model_version"]
    grade = grade_of(res.pd)
    res.grade = grade["grade"]

    # шаг 3: высокий риск — сразу отказ (если человек ещё не смотрел)
    if grade["route"] == "reject" and not req.reviewed_before:
        weak = weak_factors(res.contributions)
        res.outcome, res.reason_codes = "REJECTED", ["HIGH_RISK"]
        res.reason = texts.HIGH_RISK.format(weak=", ".join(texts.WEAK_FACTORS[f] for f in weak))
        res.advice = texts.WEAK_FACTOR_ADVICE[weak[0]]
        return res

    # шаг 4: ставка, лимит, предложение
    res.rate = rate_of(res.pd, prod)
    offer, res.max_amount, res.limit_binding = make_offer(
        req, prod, res.rate, revenue.monthly_for_limits, current_payments(data["bki"])
    )
    if offer is None and not req.reviewed_before:
        res.outcome, res.reason_codes = "REJECTED", ["NO_VIABLE_OFFER"]
        res.reason = texts.LIMIT_REASONS[res.limit_binding][0]
        res.advice = texts.NO_VIABLE_OFFER_ADVICE
        return res
    res.offer = offer

    # шаги 2 и 5: кому решать
    triggers = []
    if req.reviewed_before:
        triggers.append("M7_REVIEWED_BEFORE")
    if grade["route"] == "manual":
        triggers.append("M1_GREY_ZONE")
    if req.amount > policy()["manual_review"]["auto_approval_max_amount"]:
        triggers.append("M2_LARGE_AMOUNT")
    if prod["secured"]:
        triggers.append("M3_COLLATERAL")
    if revenue.unresolved:
        triggers.append("M4_DATA_MISMATCH")
    if triggers:
        res.outcome, res.manual_triggers = "MANUAL_REVIEW", triggers
        return res

    # шаги 6–7
    if offer.kind == "AS_REQUESTED":
        res.outcome = "AUTO_APPROVED"
    else:
        res.outcome, res.reason_codes = "COUNTER_OFFER", [offer.kind]
        res.reason, res.advice = offer.reason, offer.advice
    return res
