from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import texts
from app.api.applications import get_app, move
from app.applications import to_out
from app.db import get_session
from app.models import Application, Decision, InfoRequest
from app.schemas import BackofficeApplication, DecisionOut, QueueItem, UnderwriterDecision
from app.scoring import annuity
from app.statuses import Actor, Status

router = APIRouter(prefix="/backoffice/applications", tags=["Сотрудник банка"])


@router.get("", response_model=list[QueueItem])
def queue(status: Status = Query(Status.MANUAL_REVIEW), session: Session = Depends(get_session)):
    """Очередь заявок. По умолчанию — те, что ждут специалиста."""
    apps = session.scalars(
        select(Application).where(Application.status == status).order_by(Application.submitted_at)
    ).all()
    return [
        QueueItem(
            id=a.id, company=a.company, product=a.product, amount=a.amount, term_months=a.term_months,
            status=a.status, submitted_at=a.submitted_at,
            pd=a.last_decision.pd if a.last_decision else None,
            reason=a.last_decision.reason if a.last_decision else None,
        )
        for a in apps
    ]


@router.get("/{app_id}", response_model=BackofficeApplication)
def details(app_id: int, session: Session = Depends(get_session)):
    """Всё по заявке в одном месте: анкета, ответы внешних источников, баллы и решения."""
    app = get_app(session, app_id)
    checks = {}
    for c in app.checks:
        checks[c.source] = c.payload  # последние ответы перезаписывают старые
    return BackofficeApplication(
        application=to_out(app, internal=True), checks=checks,
        decisions=[DecisionOut.model_validate(d) for d in app.decisions],
    )


@router.post("/{app_id}/decision", response_model=BackofficeApplication)
def decide(app_id: int, body: UnderwriterDecision, session: Session = Depends(get_session)):
    """Решение специалиста по заявке на ручной проверке."""
    app = get_app(session, app_id)
    if app.status != Status.MANUAL_REVIEW:
        raise HTTPException(409, "Заявка не на ручной проверке")

    last = app.last_decision
    if body.action == "request_info":
        if body.document_kind not in texts.DOCUMENT_KINDS or not body.message:
            raise HTTPException(422, "Для дозапроса нужны document_kind и message")
        app.info_requests.append(InfoRequest(document_kind=body.document_kind, message=body.message))
        move(session, app, Status.NEEDS_INFO, Actor.UNDERWRITER)

    elif body.action == "reject":
        if not body.reason:
            raise HTTPException(422, "Укажите причину отказа для клиента")
        app.decisions.append(Decision(
            outcome=Status.REJECTED, reason=body.reason, advice=body.advice or "",
            decided_by=Actor.UNDERWRITER, comment=body.comment,
        ))
        move(session, app, Status.REJECTED, Actor.UNDERWRITER)

    else:
        amount = app.amount if body.action == "approve" else body.amount
        if amount is None:
            raise HTTPException(422, "Для контрпредложения укажите сумму")
        if body.action == "counter_offer" and (amount >= app.amount or not body.reason):
            raise HTTPException(422, "Контрпредложение — это сумма меньше запрошенной и причина для клиента")
        term = body.term_months or app.term_months
        rate = body.rate or (last.rate if last and last.rate else app.product.base_rate)
        outcome = Status.APPROVED if body.action == "approve" else Status.COUNTER_OFFER
        app.decisions.append(Decision(
            outcome=outcome, score=last.score if last else None, pd=last.pd if last else None,
            factors=last.factors if last else [], amount=amount, term_months=term, rate=rate,
            monthly_payment=annuity(amount, rate, term), reason=body.reason or "",
            decided_by=Actor.UNDERWRITER, comment=body.comment,
        ))
        move(session, app, outcome, Actor.UNDERWRITER)

    session.commit()
    return details(app_id, session)
