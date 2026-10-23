"""Скоринг и кредитное решение. Чистые функции: на вход данные, на выход решение — легко тестировать."""
import math
import statistics
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from app import scoring_config as cfg
from app import texts
from app.statuses import Status

D = Decimal


@dataclass
class ProductTerms:
    code: str
    min_amount: Decimal
    max_amount: Decimal
    base_rate: Decimal
    max_rate: Decimal
    min_business_age_months: int


@dataclass
class Inputs:
    product: ProductTerms
    amount: Decimal
    term_months: int
    registry: dict
    bki: dict
    fns: dict
    bank: dict
    declared_revenue: Decimal | None = None
    revenue_confirmed: bool = False  # клиент приложил документ
    today: date = field(default_factory=date.today)


@dataclass
class Result:
    outcome: Status
    score: int | None = None
    pd: Decimal | None = None
    factors: list = field(default_factory=list)
    stop_factors: list = field(default_factory=list)
    manual_reasons: list = field(default_factory=list)
    amount: Decimal | None = None
    term_months: int | None = None
    rate: Decimal | None = None
    monthly_payment: Decimal | None = None
    reason: str = ""
    advice: str = ""


def rub(x) -> str:
    return f"{D(x):,.0f}".replace(",", " ") + " ₽"


def annuity(amount: Decimal, rate: Decimal, months: int) -> Decimal:
    r = rate / D(1200)
    return (amount * r / (1 - (1 + r) ** -months)).quantize(D("0.01"), ROUND_HALF_UP)


def amount_for_payment(payment: Decimal, rate: Decimal, months: int) -> Decimal:
    r = rate / D(1200)
    return payment * (1 - (1 + r) ** -months) / r


def bin_points(value: float, bins: list) -> int:
    for upper, points in bins:
        if upper is None or value < upper:
            return points
    raise ValueError("последний интервал должен быть открытым")


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + end.month - start.month - (end.day < start.day)


def credit_history_kind(bki: dict) -> str:
    if bki["history_months"] == 0:
        return "none"
    if bki["max_overdue_days_12m"] == 0:
        return "clean"
    return "minor" if bki["max_overdue_days_12m"] <= 30 else "serious"


def revenue_figures(inp: Inputs) -> dict:
    turnover = [D(x) for x in inp.bank["monthly_turnover"]]
    avg = sum(turnover) / len(turnover)
    bank_annual = avg * 12
    # выручку со слов клиента берём, только если она подтверждена документом
    annual = bank_annual
    if inp.revenue_confirmed and inp.declared_revenue and inp.declared_revenue > bank_annual:
        annual = inp.declared_revenue
    cv = statistics.pstdev([float(x) for x in turnover]) / float(avg)
    return {"bank_annual": bank_annual, "annual": annual, "monthly": annual / 12, "cv": cv}


def revenue_mismatch(inp: Inputs) -> bool:
    """Выручка в анкете сильно больше того, что видно по счёту, и документа нет."""
    if inp.revenue_confirmed or not inp.declared_revenue:
        return False
    return inp.declared_revenue > revenue_figures(inp)["bank_annual"] * cfg.REVENUE_MISMATCH


def stop_factors(inp: Inputs) -> list[dict]:
    stops = []
    if inp.registry["status"] != "active":
        stops.append({"code": "liquidating"})
    if inp.bki["current_overdue_days"] > 0:
        stops.append({"code": "current_overdue", "days": inp.bki["current_overdue_days"]})
    if inp.fns["tax_debt"] > 0:
        stops.append({"code": "tax_debt", "amount": inp.fns["tax_debt"]})
    age = months_between(date.fromisoformat(inp.registry["registered_at"]), inp.today)
    if age < inp.product.min_business_age_months:
        stops.append({"code": "too_young", "age": age, "min_age": inp.product.min_business_age_months})
    return stops


def score_factors(inp: Inputs) -> list[dict]:
    rev = revenue_figures(inp)
    age_years = months_between(date.fromisoformat(inp.registry["registered_at"]), inp.today) / 12
    history = credit_history_kind(inp.bki)
    new_payment = annuity(inp.amount, inp.product.base_rate, inp.term_months)
    load = (D(inp.bki["monthly_payments"]) + new_payment) / rev["monthly"]
    share = inp.amount / rev["annual"]

    def best(bins):
        return max(p for _, p in bins)

    history_text = {"none": "нет", "clean": "без просрочек", "minor": "просрочки до 30 дней", "serious": "просрочки более 30 дней"}
    return [
        dict(code="business_age", label="Срок работы бизнеса", value=f"{age_years:.1f} лет",
             points=bin_points(age_years, cfg.BUSINESS_AGE_YEARS), max_points=best(cfg.BUSINESS_AGE_YEARS),
             weak_text="небольшой срок работы бизнеса"),
        dict(code="credit_history", label="Кредитная история", value=history_text[history],
             points=cfg.CREDIT_HISTORY[history], max_points=max(cfg.CREDIT_HISTORY.values()),
             weak_text="нет кредитной истории" if history == "none" else "просрочки в кредитной истории"),
        dict(code="debt_load", label="Долговая нагрузка с новым кредитом", value=f"{load:.0%}",
             points=bin_points(float(load), cfg.DEBT_LOAD), max_points=best(cfg.DEBT_LOAD),
             weak_text="высокая долговая нагрузка"),
        dict(code="turnover_stability", label="Стабильность оборотов", value=f"разброс {rev['cv']:.0%}",
             points=bin_points(rev["cv"], cfg.TURNOVER_CV), max_points=best(cfg.TURNOVER_CV),
             weak_text="нестабильные обороты по счёту"),
        dict(code="amount_to_revenue", label="Сумма кредита к годовой выручке", value=f"{share:.0%}",
             points=bin_points(float(share), cfg.AMOUNT_TO_REVENUE), max_points=best(cfg.AMOUNT_TO_REVENUE),
             weak_text="сумма велика относительно выручки"),
    ]


def probability_of_default(score: int) -> Decimal:
    pd = 1 / (1 + math.exp(cfg.ALPHA + cfg.BETA * score))
    return D(pd).quantize(D("0.0001"), ROUND_HALF_UP)


def risk_rate(product: ProductTerms, pd: Decimal) -> Decimal:
    # чем выше риск, тем ближе ставка к потолку продукта
    k = min(D(1), pd / cfg.PD_MANUAL)
    return (product.base_rate + (product.max_rate - product.base_rate) * k).quantize(D("0.01"), ROUND_HALF_UP)


def decide(inp: Inputs) -> Result:
    stops = stop_factors(inp)
    if stops:
        first = stops[0]
        reason, advice = texts.STOP_REASONS[first["code"]]
        if first["code"] == "too_young":
            params = dict(first, wait=first["min_age"] - first["age"])
            reason, advice = reason.format(**params), advice.format(**params)
        return Result(Status.REJECTED, stop_factors=stops, reason=reason, advice=advice)

    factors = score_factors(inp)
    score = sum(f["points"] for f in factors)
    pd = probability_of_default(score)
    rate = risk_rate(inp.product, pd)
    res = Result(Status.APPROVED, score=score, pd=pd, factors=factors, term_months=inp.term_months, rate=rate)

    if pd >= cfg.PD_MANUAL:
        weak = sorted((f for f in factors if f["points"] < f["max_points"]), key=lambda f: f["points"] - f["max_points"])
        res.outcome = Status.REJECTED
        res.reason = texts.HIGH_RISK[0].format(weak=", ".join(f["weak_text"] for f in weak[:2]))
        res.advice = texts.HIGH_RISK[1]
        return res

    if pd >= cfg.PD_COUNTER:
        res.manual_reasons.append("pd")
    if inp.amount > cfg.LARGE_AMOUNT.get(inp.product.code, inp.product.max_amount):
        res.manual_reasons.append("large_amount")
    if res.manual_reasons:
        res.outcome = Status.MANUAL_REVIEW
        res.reason = ", ".join(texts.MANUAL_REASONS[r] for r in res.manual_reasons)
        return res

    # сколько можно дать, чтобы платежи не превысили лимит нагрузки
    rev = revenue_figures(inp)
    free_payment = cfg.MAX_DEBT_LOAD * rev["monthly"] - D(inp.bki["monthly_payments"])
    by_load = amount_for_payment(free_payment, rate, inp.term_months) if free_payment > 0 else D(0)

    offer = min(inp.amount, by_load)
    reason = texts.COUNTER_BY_LOAD if offer < inp.amount else ""
    if pd >= cfg.PD_APPROVE and offer > inp.amount * cfg.COUNTER_SHARE:
        offer = inp.amount * cfg.COUNTER_SHARE
        reason = reason or texts.COUNTER_BY_RISK
    offer = (offer / 10000).to_integral_value(ROUND_DOWN) * 10000  # круглая сумма

    if offer < inp.product.min_amount:
        res.outcome = Status.REJECTED
        res.reason, res.advice = texts.LOAD_TOO_HIGH
        return res

    res.amount = offer
    res.monthly_payment = annuity(offer, rate, inp.term_months)
    if offer < inp.amount:
        res.outcome = Status.COUNTER_OFFER
        res.reason = reason
    return res
