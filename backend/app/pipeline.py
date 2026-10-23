"""
Кредитный конвейер: двигает заявку по шагам банка, пока она не дойдёт до решения
или не остановится (нужны данные от клиента / нужен специалист).
"""
import logging
import threading
import time
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import external, texts
from app.applications import problems_for_submit
from app.config import settings
from app.db import SessionLocal
from app.models import Application, CheckResult, Decision, InfoRequest
from app.scoring import Inputs, ProductTerms, decide, revenue_mismatch
from app.statuses import Actor, Status
from app.workflow import change_status

log = logging.getLogger("pipeline")

AUTO = {Status.SUBMITTED, Status.VALIDATION, Status.EXTERNAL_CHECKS, Status.SCORING}


def scoring_inputs(app: Application) -> Inputs:
    p = app.product
    return Inputs(
        product=ProductTerms(p.code, p.min_amount, p.max_amount, p.base_rate, p.max_rate, p.min_business_age_months),
        amount=app.amount,
        term_months=app.term_months,
        registry=app.check("registry"),
        bki=app.check("bki"),
        fns=app.check("fns"),
        bank=app.check("bank"),
        declared_revenue=app.annual_revenue,
        revenue_confirmed=any(d.kind == "bank_statement" for d in app.documents),
        today=date.today(),
    )


def step(session: Session, app: Application, fetch_all) -> None:
    """Один шаг конвейера. Что делать — решает текущий статус."""
    if app.status == Status.SUBMITTED:
        change_status(session, app, Status.VALIDATION, Actor.SYSTEM)

    elif app.status == Status.VALIDATION:
        problems = problems_for_submit(app)
        if problems:
            change_status(session, app, Status.NEEDS_INFO, Actor.SYSTEM, "; ".join(p.message for p in problems))
        else:
            change_status(session, app, Status.EXTERNAL_CHECKS, Actor.SYSTEM)

    elif app.status == Status.EXTERNAL_CHECKS:
        try:
            data = fetch_all(app.company.inn)
        except external.ExternalUnavailable as e:
            log.warning("заявка %s: внешние источники недоступны: %s", app.id, e)
            reason = texts.MANUAL_REASONS["external_unavailable"]
            app.decisions.append(Decision(outcome=Status.MANUAL_REVIEW, reason=reason, decided_by=Actor.SYSTEM, comment=str(e)))
            change_status(session, app, Status.MANUAL_REVIEW, Actor.SYSTEM, reason)
            return

        for source, payload in data.items():
            app.checks.append(CheckResult(source=source, payload=payload))

        if revenue_mismatch(scoring_inputs(app)):
            kind, message = texts.REVENUE_REQUEST
            if not any(r.document_kind == kind and r.resolved_at is None for r in app.info_requests):
                app.info_requests.append(InfoRequest(document_kind=kind, message=message))
            change_status(session, app, Status.NEEDS_INFO, Actor.SYSTEM, "выручка в анкете не подтверждается оборотами по счёту")
        else:
            change_status(session, app, Status.SCORING, Actor.SYSTEM)

    elif app.status == Status.SCORING:
        r = decide(scoring_inputs(app))
        app.decisions.append(Decision(
            outcome=r.outcome, score=r.score, pd=r.pd, factors=r.factors, stop_factors=r.stop_factors,
            amount=r.amount, term_months=r.term_months, rate=r.rate, monthly_payment=r.monthly_payment,
            reason=r.reason, advice=r.advice, decided_by=Actor.SYSTEM,
            comment=", ".join(r.manual_reasons) or None,
        ))
        change_status(session, app, r.outcome, Actor.SYSTEM, f"PD {r.pd:.2%}" if r.pd is not None else "стоп-фактор")


def process(app_id: int, session_factory=SessionLocal, fetch_all=external.fetch_all, delay: float | None = None) -> None:
    delay = settings.pipeline_step_delay if delay is None else delay
    with session_factory() as session:
        while True:
            app = session.get(Application, app_id)
            if app is None or app.status not in AUTO:
                return
            try:
                step(session, app, fetch_all)
                session.commit()
            except Exception:
                session.rollback()
                log.exception("заявка %s: ошибка на шаге %s, останавливаемся", app_id, app.status)
                return
            if delay:
                time.sleep(delay)


def resume_unfinished() -> None:
    """После рестарта дожимаем заявки, которые застряли посередине конвейера."""
    with SessionLocal() as session:
        ids = session.scalars(select(Application.id).where(Application.status.in_(AUTO))).all()
    for app_id in ids:
        threading.Thread(target=process, args=(app_id,), daemon=True).start()


def get_pipeline():
    # через зависимость, чтобы в тестах гонять конвейер синхронно с фейковыми данными
    return process
