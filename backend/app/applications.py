from decimal import ROUND_HALF_UP, Decimal

from app.models import Application, Product
from app.schemas import (
    ApplicationListItem,
    ApplicationOut,
    CompanyShort,
    HistoryItem,
    Problem,
    ProductShort,
    StatusView,
)
from app.statuses import CLIENT_VIEW, Actor, Status, next_statuses

EDITABLE = {Status.DRAFT, Status.NEEDS_INFO}

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


def problems_for_submit(app: Application) -> list[Problem]:
    """Что мешает отправить заявку. Пустой список — можно отправлять."""
    p: Product = app.product
    problems = []

    if app.amount is None:
        problems.append(Problem(field="amount", message="Укажите сумму"))
    elif not p.min_amount <= app.amount <= p.max_amount:
        problems.append(Problem(
            field="amount",
            message=f"Для продукта «{p.name}» сумма от {p.min_amount:,.0f} до {p.max_amount:,.0f} ₽".replace(",", " "),
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

    return problems


def estimated_payment(app: Application) -> Decimal | None:
    """Примерный ежемесячный платёж по аннуитету и базовой ставке продукта."""
    if not app.amount or not app.term_months:
        return None
    r = app.product.base_rate / Decimal(1200)
    n = app.term_months
    payment = app.amount * r / (1 - (1 + r) ** -n)
    return payment.quantize(Decimal("0.01"), ROUND_HALF_UP)


def status_view(status: Status) -> StatusView:
    title, hint = CLIENT_VIEW[status]
    return StatusView(code=status, title=title, hint=hint)


def to_out(app: Application) -> ApplicationOut:
    return ApplicationOut(
        id=app.id,
        status=status_view(app.status),
        company=CompanyShort.model_validate(app.company),
        product=ProductShort.model_validate(app.product),
        amount=app.amount,
        term_months=app.term_months,
        purpose=app.purpose,
        estimated_payment=estimated_payment(app),
        available_actions=available_actions(app),
        history=[HistoryItem.model_validate(h) for h in app.history],
        created_at=app.created_at,
        updated_at=app.updated_at,
        submitted_at=app.submitted_at,
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
