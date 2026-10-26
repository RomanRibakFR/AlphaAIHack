"""Как заявка выглядит снаружи: что видит клиент, какие кнопки, что мешает отправить."""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.external import COMPANY_SOURCES
from app.models import Application, Offer
from app.policy import product as product_policy
from app.schemas import (
    ApplicationListItem,
    ApplicationOut,
    CompanyShort,
    DocumentOut,
    HistoryItem,
    InfoRequestOut,
    OfferOut,
    OfferVariant,
    Payment,
    Problem,
    ProductShort,
    Rejection,
    ReviewStep,
    StatusView,
)
from app.statuses import CLIENT_STAGES, CLIENT_VIEW, FINAL, REVIEWING, Actor, Status

CENT = Decimal("0.01")


def rub(x) -> str:
    return f"{Decimal(x):,.0f}".replace(",", " ") + " ₽"


def pct(x) -> str:
    # 16.40 -> «16,4%»
    return f"{Decimal(x).normalize():f}".replace(".", ",") + "%"


def sentence(text: str) -> str:
    return text if text.endswith(".") else text + "."


def available_actions(app: Application) -> list[str]:
    s = app.status
    if s == Status.DRAFT:
        return ["edit", "upload_document", "submit", "cancel"]
    if s == Status.INFO_REQUESTED:
        return ["edit", "upload_document", "provide_info", "cancel"]
    if s == Status.OFFER_PROPOSED:
        return ["accept", "decline"]
    if s == Status.SIGNING:
        return ["sign", "cancel"]
    return [] if s in FINAL else ["cancel"]


def open_requests(app: Application):
    return [r for r in app.info_requests if r.resolved_at is None]


def problems_for_submit(app: Application) -> list[Problem]:
    """Правило V01 и обязательные поля анкеты. Пустой список — можно отправлять."""
    p = app.product
    problems = []
    if app.amount is None:
        problems.append(Problem(field="amount", message="Укажите сумму"))
    elif not p.min_amount <= app.amount <= p.max_amount:
        problems.append(Problem(field="amount", message=f"Для продукта «{p.name}» сумма от {rub(p.min_amount)} до {rub(p.max_amount)}"))
    if app.term_months is None:
        problems.append(Problem(field="term_months", message="Укажите срок"))
    elif not p.min_term_months <= app.term_months <= p.max_term_months:
        problems.append(Problem(field="term_months", message=f"Для продукта «{p.name}» срок от {p.min_term_months} до {p.max_term_months} мес."))
    if not app.purpose.strip():
        problems.append(Problem(field="purpose", message="Расскажите, на что нужны деньги"))
    if not app.annual_revenue:
        problems.append(Problem(field="annual_revenue", message="Укажите выручку за последние 12 месяцев"))
    return problems


def problems_for_info(app: Application) -> list[Problem]:
    """Всё ли из запрошенного банком на месте."""
    uploaded = {d.doc_type for d in app.documents}
    problems = []
    for r in open_requests(app):
        for item in r.items:
            if item["kind"] == "document" and item["code"] not in uploaded:
                problems.append(Problem(field="documents", message=f"Загрузите: {item['title']}"))
            if item["kind"] == "field" and item["code"] == "collateral" and not (app.collateral_type and app.collateral_value):
                problems.append(Problem(field="collateral", message="Укажите вид и стоимость залога"))
    return problems


def monthly_payment(product_code: str, amount, rate_percent, term: int) -> Decimal:
    # аннуитет для всех продуктов: овердрафт — как 12 равных платежей (docs/decision-policy.md, раздел 5.3)
    r = Decimal(rate_percent) / 1200
    return (Decimal(amount) * r / (1 - (1 + r) ** -term)).quantize(CENT, ROUND_HALF_UP)


def estimated_payment(app: Application) -> Decimal | None:
    """Примерный платёж по ставке «от» — для калькулятора в черновике."""
    if not app.amount or not app.term_months:
        return None
    return monthly_payment(app.product.code, app.amount, app.product.base_rate, app.term_months)


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    days = [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(d.day, days[month - 1]))


def chosen_terms(offer: Offer) -> tuple[Decimal, int, Decimal]:
    if offer.chosen_alternative is not None:
        alt = offer.alternatives[offer.chosen_alternative]
        return Decimal(alt["amount"]), alt["term_months"], Decimal(alt["monthly_payment"])
    return offer.amount, offer.term_months, offer.monthly_payment


def payment_schedule(offer: Offer, start: date) -> list[Payment]:
    amount, term, payment = chosen_terms(offer)
    r = offer.rate / Decimal(1200)
    balance, rows = amount, []
    for n in range(1, term + 1):
        interest = (balance * r).quantize(CENT, ROUND_HALF_UP)
        principal = balance if n == term else payment - interest
        balance -= principal
        rows.append(Payment(n=n, date=add_months(start, n), payment=principal + interest,
                            principal=principal, interest=interest, balance=balance))
    return rows


def status_view(app: Application) -> StatusView:
    title, hint = CLIENT_VIEW[app.status]
    if app.status == Status.OFFER_PROPOSED and app.offer and app.offer.type == "AS_REQUESTED":
        title = "Кредит одобрен"
    return StatusView(code=app.status, title=title, hint=hint)


def client_stage(app: Application) -> str:
    """Подшаг «Рассматриваем заявку» — по статусу и журналу проверок."""
    if app.status == Status.SCORING:
        return "decision"
    if app.status == Status.CHECKS and set(COMPANY_SOURCES) <= set(app.current_checks()):
        return "credit_history"
    return "company_check"


def review_steps(app: Application) -> list[ReviewStep]:
    codes = [c for c, _ in CLIENT_STAGES]
    current = codes.index(client_stage(app))
    return [
        ReviewStep(code=code, title=title, state="done" if i < current else "current" if i == current else "pending")
        for i, (code, title) in enumerate(CLIENT_STAGES)
    ]


def offer_out(app: Application) -> OfferOut | None:
    o = app.offer
    if o is None or app.status not in {Status.OFFER_PROPOSED, Status.SIGNING, Status.ISSUED}:
        return None
    amount, term, payment = chosen_terms(o)
    if o.type == "AS_REQUESTED":
        text = (f"Кредит одобрен: {rub(o.amount)} на {o.term_months} мес. под {pct(o.rate)} годовых, "
                f"платёж {rub(o.monthly_payment)} в месяц. Проверьте условия и подпишите в кабинете.")
    elif o.counter_kind == "TERM_EXTENDED":
        text = (f"Мы готовы выдать {rub(o.amount)} на {o.term_months} мес. вместо {app.term_months} под {pct(o.rate)} годовых. "
                f"Причина: {sentence(o.reason)} Можно принять предложение или отказаться.")
    else:
        text = f"Мы готовы выдать {rub(o.amount)} вместо {rub(app.amount)} под {pct(o.rate)} годовых."
        if o.reason:
            text += f" Причина: {sentence(o.reason)}"
        if o.advice:
            text += f" Что можно сделать: {sentence(o.advice)}"
        for alt in o.alternatives:
            text += f" Есть и другой вариант: {rub(alt['amount'])} на {alt['term_months']} мес."
        text += " Можно принять предложение или отказаться."
    return OfferOut(
        type=o.type, counter_kind=o.counter_kind, amount=o.amount, term_months=o.term_months,
        requested_amount=app.amount, requested_term_months=app.term_months, rate=o.rate,
        monthly_payment=o.monthly_payment, total_payment=payment * term,
        alternatives=[OfferVariant(**a) for a in o.alternatives], conditions=o.conditions,
        chosen_alternative=o.chosen_alternative, valid_until=o.valid_until,
        reason=o.reason, advice=o.advice, text=text,
    )


def history_items(app: Application, internal: bool) -> list[HistoryItem]:
    items = [HistoryItem.model_validate(h) for h in app.history]
    if not internal:
        # комментарии и коды системы и специалиста — служебные (PD, стоп-факторы), клиенту не нужны
        for item in items:
            if item.actor != Actor.CLIENT:
                item.comment = None
                item.reason_code = None
    return items


def to_out(app: Application, internal: bool = False) -> ApplicationOut:
    d = app.last_decision
    rejection = None
    if app.status == Status.REJECTED and d is not None:
        rejection = Rejection(
            reason=d.reason, advice=d.advice,
            text=f"Сейчас мы не можем выдать кредит. Причина: {sentence(d.reason)}"
                 + (f" Что можно сделать: {sentence(d.advice)}" if d.advice else ""),
        )
    schedule = None
    if app.status == Status.ISSUED and app.offer and app.issued_at:
        schedule = payment_schedule(app.offer, app.issued_at.date())

    return ApplicationOut(
        id=app.id,
        status=status_view(app),
        review_steps=review_steps(app) if app.status in REVIEWING else None,
        company=CompanyShort.model_validate(app.company),
        product=ProductShort.model_validate(app.product),
        amount=app.amount, term_months=app.term_months, purpose=app.purpose, annual_revenue=app.annual_revenue,
        collateral_type=app.collateral_type, collateral_description=app.collateral_description,
        collateral_value=app.collateral_value,
        estimated_payment=estimated_payment(app),
        available_actions=available_actions(app),
        info_requests=[InfoRequestOut(id=r.id, reason_code=r.reason_code, items=r.items, created_at=r.created_at)
                       for r in open_requests(app)],
        documents=[DocumentOut.model_validate(doc) for doc in app.documents],
        offer=offer_out(app),
        rejection=rejection,
        sign_code=app.sign_code if app.status == Status.SIGNING else None,
        contract_number=f"КД-{app.id:06d}" if app.status in {Status.SIGNING, Status.ISSUED} else None,
        schedule=schedule,
        deadline_at=app.deadline_at,
        history=history_items(app, internal),
        version=app.version,
        created_at=app.created_at, updated_at=app.updated_at,
        submitted_at=app.submitted_at, issued_at=app.issued_at,
    )


def to_list_item(app: Application) -> ApplicationListItem:
    return ApplicationListItem(
        id=app.id, status=status_view(app), product=ProductShort.model_validate(app.product),
        amount=app.amount, term_months=app.term_months, updated_at=app.updated_at,
    )
