from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import texts
from app.api.applications import event, get_app
from app.applications import monthly_payment, to_out
from app.db import get_session
from app.models import Application, InfoRequest
from app.pipeline import add_decision, add_offer
from app.schemas import BackofficeApplication, CheckOut, DecisionOut, QueueItem, UnderwriterDecision
from app.statuses import Actor, Status

router = APIRouter(prefix="/backoffice/applications", tags=["Сотрудник банка"])

UNDERWRITER_REJECT = "по результатам рассмотрения заявки специалистом банк не готов выдать кредит"


def triggers_of(app: Application) -> list[str]:
    d = app.last_decision
    return [texts.MANUAL_TRIGGERS.get(t, t) for t in (d.manual_triggers if d else [])]


@router.get("", response_model=list[QueueItem])
def queue(status: Status = Query(Status.MANUAL_REVIEW), session: Session = Depends(get_session)):
    """Очередь заявок. По умолчанию — те, что ждут специалиста."""
    apps = session.scalars(select(Application).where(Application.status == status).order_by(Application.submitted_at)).all()
    return [
        QueueItem(
            id=a.id, company=a.company, product=a.product, amount=a.amount, term_months=a.term_months,
            status=a.status, submitted_at=a.submitted_at, triggers=triggers_of(a),
            pd=a.last_decision.pd if a.last_decision else None,
            grade=a.last_decision.grade if a.last_decision else None,
        )
        for a in apps
    ]


@router.get("/{app_id}", response_model=BackofficeApplication)
def details(app_id: int, session: Session = Depends(get_session)):
    """Всё по заявке: анкета, ответы источников, признаки, вклад в оценку, рекомендация системы."""
    app = get_app(session, app_id)
    return BackofficeApplication(
        application=to_out(app, internal=True),
        checks=[CheckOut.model_validate(c) for c in app.current_checks().values()],
        decisions=[DecisionOut.model_validate(d) for d in app.decisions],
    )


@router.post("/{app_id}/decision", response_model=BackofficeApplication)
def decide(app_id: int, body: UnderwriterDecision, session: Session = Depends(get_session)):
    """Решение специалиста (T14 одобрить / T15 отказать / T16 запросить данные). Комментарий обязателен."""
    app = get_app(session, app_id)
    if app.status != Status.MANUAL_REVIEW:
        raise HTTPException(409, {"message": "Заявка не у специалиста", "status": app.status})
    last = app.last_decision

    if body.action == "request_info":
        allowed = set(texts.DOCUMENT_TYPES) | {"collateral"}
        if not body.items or set(body.items) - allowed or not body.message:
            raise HTTPException(422, f"Для запроса нужны items (из {sorted(allowed)}) и message для клиента")
        items = [
            dict(kind="field", code="collateral", title="Залог", message=body.message) if code == "collateral"
            else dict(kind="document", code=code, title=texts.DOCUMENT_TYPES[code], message=body.message)
            for code in body.items
        ]
        app.info_requests.append(InfoRequest(reason_code="UNDERWRITER", items=items, requested_by=Actor.UNDERWRITER))
        add_decision(app, "INFO_REQUESTED", Actor.UNDERWRITER, comment=body.comment)
        event(session, app, "underwriter_requested_info", Actor.UNDERWRITER, "UNDERWRITER", body.comment)

    elif body.action == "reject":
        if not body.reason_code:
            raise HTTPException(422, "Укажите код причины отказа")
        add_decision(app, "REJECTED", Actor.UNDERWRITER, reason_codes=[body.reason_code], comment=body.comment,
                     reason=body.reason or UNDERWRITER_REJECT, advice=body.advice or "")
        event(session, app, "underwriter_rejected", Actor.UNDERWRITER, body.reason_code, body.comment)

    else:
        rec = (last.recommendation if last else None) or {}
        amount = body.amount or Decimal(rec.get("amount") or app.amount)
        term = body.term_months or rec.get("term_months") or app.term_months
        rate = body.rate or Decimal(str(rec.get("rate") or app.product.base_rate))
        payment = monthly_payment(app.product.code, amount, rate, term)
        kind = "AS_REQUESTED" if amount == app.amount and term == app.term_months else (
            "TERM_EXTENDED" if amount == app.amount else "AMOUNT_REDUCED")
        reason, advice = (rec.get("reason", ""), rec.get("advice", "")) if kind != "AS_REQUESTED" else ("", "")
        add_offer(app, Actor.UNDERWRITER, kind, amount, term, float(rate) / 100, payment,
                  conditions=rec.get("conditions", []), reason=reason, advice=advice)
        add_decision(app, "APPROVED" if kind == "AS_REQUESTED" else "COUNTER_OFFER", Actor.UNDERWRITER,
                     pd=last.pd if last else None, grade=last.grade if last else None, comment=body.comment)
        event(session, app, "underwriter_approved", Actor.UNDERWRITER, None, body.comment)

    session.commit()
    return details(app_id, session)
