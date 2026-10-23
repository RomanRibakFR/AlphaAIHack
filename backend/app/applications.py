from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app import texts
from app.models import Application, Product
from app.schemas import (
    ApplicationListItem,
    ApplicationOut,
    CompanyShort,
    DocumentOut,
    HistoryItem,
    InfoRequestOut,
    Offer,
    Payment,
    Problem,
    ProductShort,
    Rejection,
    ReviewStep,
    StatusView,
)
from app.scoring import annuity, rub
from app.statuses import CLIENT_VIEW, REVIEW_STEPS, Actor, Status, next_statuses

EDITABLE = {Status.DRAFT, Status.NEEDS_INFO}
REVIEWING = {Status.SUBMITTED, Status.VALIDATION, Status.EXTERNAL_CHECKS, Status.SCORING}
WITH_OFFER = {Status.APPROVED, Status.COUNTER_OFFER, Status.SIGNING, Status.ISSUED}

# в какой статус ведёт кнопка клиента
CLIENT_ACTIONS = {
    Status.SUBMITTED: "submit",
    Status.WITHDRAWN: "withdraw",
    Status.SIGNING: "accept",
    Status.DECLINED_BY_CLIENT: "decline",
    Status.ISSUED: "sign",
}


def available_actions(app: Application) -> list[str]:
    actions = ["edit"] if app.status in EDITABLE else []
    actions += [CLIENT_ACTIONS[s] for s in next_statuses(app.status, Actor.CLIENT) if s in CLIENT_ACTIONS]
    return actions


def open_requests(app: Application):
    return [r for r in app.info_requests if r.resolved_at is None]


def problems_for_submit(app: Application) -> list[Problem]:
    """Что мешает отправить заявку. Пустой список — можно отправлять."""
    p: Product = app.product
    problems = []

    if app.amount is None:
        problems.append(Problem(field="amount", message="Укажите сумму"))
    elif not p.min_amount <= app.amount <= p.max_amount:
        problems.append(Problem(
            field="amount", message=f"Для продукта «{p.name}» сумма от {rub(p.min_amount)} до {rub(p.max_amount)}",
        ))

    if app.term_months is None:
        problems.append(Problem(field="term_months", message="Укажите срок"))
    elif not p.min_term_months <= app.term_months <= p.max_term_months:
        problems.append(Problem(
            field="term_months",
            message=f"Для продукта «{p.name}» срок от {p.min_term_months} до {p.max_term_months} мес.",
        ))

    if not app.purpose.strip():
        problems.append(Problem(field="purpose", message="Расскажите, на что нужны деньги"))

    if not app.annual_revenue:
        problems.append(Problem(field="annual_revenue", message="Укажите выручку за последние 12 месяцев"))

    uploaded = {d.kind for d in app.documents}
    for r in open_requests(app):
        if r.document_kind not in uploaded:
            problems.append(Problem(field="documents", message=f"Загрузите документ: {texts.DOCUMENT_KINDS[r.document_kind]}"))

    return problems


def estimated_payment(app: Application) -> Decimal | None:
    """Примерный ежемесячный платёж по аннуитету и базовой ставке продукта."""
    if not app.amount or not app.term_months:
        return None
    return annuity(app.amount, app.product.base_rate, app.term_months)


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    days = [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(year, month, min(d.day, days[month - 1]))


def payment_schedule(amount: Decimal, rate: Decimal, months: int, start: date) -> list[Payment]:
    payment = annuity(amount, rate, months)
    r = rate / Decimal(1200)
    balance = amount
    rows = []
    for n in range(1, months + 1):
        interest = (balance * r).quantize(Decimal("0.01"), ROUND_HALF_UP)
        principal = balance if n == months else payment - interest
        balance -= principal
        rows.append(Payment(n=n, date=add_months(start, n), payment=principal + interest,
                            principal=principal, interest=interest, balance=balance))
    return rows


def status_view(status: Status) -> StatusView:
    title, hint = CLIENT_VIEW[status]
    return StatusView(code=status, title=title, hint=hint)


def review_steps(status: Status) -> list[ReviewStep]:
    order = [s for s, _ in REVIEW_STEPS]
    current = order.index(status) if status in order else -1
    return [
        ReviewStep(title=title, state="done" if i < current else "current" if i == current else "pending")
        for i, (_, title) in enumerate(REVIEW_STEPS)
    ]


def offer_for(app: Application) -> Offer | None:
    d = app.last_decision
    if app.status not in WITH_OFFER or d is None or d.amount is None:
        return None
    is_counter = d.amount < app.amount
    if is_counter:
        text = f"Мы готовы выдать {rub(d.amount)} вместо {rub(app.amount)}. Причина: {d.reason}."
        if d.advice:
            text += f" Что можно сделать: {d.advice}."
        text += " Можно принять предложение или отказаться."
    else:
        text = (f"Кредит одобрен: {rub(d.amount)} на {d.term_months} мес. под {d.rate}% годовых, "
                f"платёж {rub(d.monthly_payment)} в месяц. Проверьте условия и подпишите в кабинете.")
    return Offer(amount=d.amount, requested_amount=app.amount, term_months=d.term_months, rate=d.rate,
                 monthly_payment=d.monthly_payment, total_payment=d.monthly_payment * d.term_months,
                 is_counter=is_counter, advice=d.advice if is_counter else "", text=text)


def history_items(app: Application, internal: bool) -> list[HistoryItem]:
    items = [HistoryItem.model_validate(h) for h in app.history]
    if not internal:
        # комментарии системы и специалиста — служебные (PD, причины ручной проверки), клиенту не нужны
        for item in items:
            if item.actor != Actor.CLIENT:
                item.comment = None
    return items


def to_out(app: Application, internal: bool = False) -> ApplicationOut:
    d = app.last_decision
    offer = offer_for(app)
    rejection = None
    if app.status == Status.REJECTED and d is not None:
        rejection = Rejection(
            reason=d.reason, advice=d.advice,
            text=f"Сейчас мы не можем выдать кредит. Причина: {d.reason}. Что можно сделать: {d.advice}.",
        )
    schedule = None
    if app.status == Status.ISSUED and offer and app.issued_at:
        schedule = payment_schedule(offer.amount, offer.rate, offer.term_months, app.issued_at.date())

    return ApplicationOut(
        id=app.id,
        status=status_view(app.status),
        review_steps=review_steps(app.status) if app.status in REVIEWING else None,
        company=CompanyShort.model_validate(app.company),
        product=ProductShort.model_validate(app.product),
        amount=app.amount,
        term_months=app.term_months,
        purpose=app.purpose,
        annual_revenue=app.annual_revenue,
        estimated_payment=estimated_payment(app),
        available_actions=available_actions(app),
        info_requests=[
            InfoRequestOut(document_kind=r.document_kind, document_title=texts.DOCUMENT_KINDS[r.document_kind],
                           message=r.message, created_at=r.created_at)
            for r in open_requests(app)
        ],
        documents=[DocumentOut.model_validate(doc) for doc in app.documents],
        offer=offer,
        rejection=rejection,
        sign_code=app.sign_code if app.status == Status.SIGNING else None,
        contract_number=f"КД-{app.id:06d}" if app.status in {Status.SIGNING, Status.ISSUED} else None,
        schedule=schedule,
        history=history_items(app, internal),
        created_at=app.created_at,
        updated_at=app.updated_at,
        submitted_at=app.submitted_at,
        issued_at=app.issued_at,
    )


def to_list_item(app: Application) -> ApplicationListItem:
    return ApplicationListItem(
        id=app.id,
        status=status_view(app.status),
        product=ProductShort.model_validate(app.product),
        amount=app.amount,
        term_months=app.term_months,
        updated_at=app.updated_at,
    )
