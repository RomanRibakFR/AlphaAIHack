"""
Кредитный конвейер: ведёт заявку по системным шагам (SUBMITTED → VALIDATION → CHECKS → SCORING),
пока она не дойдёт до решения или не остановится (ждём клиента / нужен специалист).
"""
import logging
import threading
import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import external, texts
from app.config import settings, today
from app.db import SessionLocal
from app.decision import Request, decide
from app.features import revenue_check, stop_factors
from app.models import Application, CheckResult, Decision, InfoRequest, Offer
from app.policy import policy, product as product_policy
from app.statuses import Actor, Status
from app.workflow import fire, now, timeout

log = logging.getLogger("pipeline")

AUTO = {Status.SUBMITTED, Status.VALIDATION, Status.CHECKS, Status.SCORING}
EXPIRING = {Status.INFO_REQUESTED: "info_expired", Status.OFFER_PROPOSED: "offer_expired", Status.SIGNING: "signing_expired"}


def statement_of(app: Application) -> dict | None:
    docs = [d for d in app.documents if d.doc_type == "other_bank_statement" and d.declared_values.get("turnover")]
    return docs[-1].declared_values if docs else None


def validation_requests(app: Application) -> list[str]:
    """Правила V02/V03: чего не хватает для этого продукта и суммы."""
    missing = []
    has = {d.doc_type for d in app.documents}
    if app.amount > policy()["validation"]["financial_statements_required_above"] and "financial_statements" not in has:
        missing.append("V03_FINANCIAL_STATEMENTS")
    if product_policy(app.product.code)["secured"] and not (app.collateral_type and app.collateral_value):
        missing.append("V02_COLLATERAL")
    return missing


def add_decision(app: Application, outcome: str, decided_by: Actor = Actor.SYSTEM, **kw) -> Decision:
    d = Decision(outcome=outcome, policy_version=str(policy()["version"]), decided_by=decided_by, **kw)
    app.decisions.append(d)
    return d


def add_offer(app: Application, created_by: Actor, kind: str, amount, term: int, rate: float, monthly_payment,
              alternatives=(), conditions=(), reason="", advice="") -> Offer:
    offer = Offer(
        type="AS_REQUESTED" if kind == "AS_REQUESTED" else "COUNTER",
        counter_kind=None if kind == "AS_REQUESTED" else kind,
        product_code=app.product.code, amount=Decimal(amount), term_months=term,
        rate=Decimal(str(round(rate * 100, 2))), monthly_payment=Decimal(monthly_payment),
        alternatives=list(alternatives), conditions=list(conditions), reason=reason, advice=advice,
        valid_until=now() + timeout(Status.OFFER_PROPOSED), created_by=created_by,
    )
    app.offers.append(offer)
    return offer


def offer_dict(o) -> dict | None:
    if o is None:
        return None
    return {"kind": o.kind, "amount": o.amount, "term_months": o.term_months, "rate": round(o.rate * 100, 2),
            "monthly_payment": o.monthly_payment, "alternatives": o.alternatives, "conditions": o.conditions,
            "reason": o.reason, "advice": o.advice}


def run_checks(session: Session, app: Application, fetch) -> None:
    """CHECKS: опрашиваем источники по одному и сразу пишем в журнал — по нему кабинет показывает подшаги."""
    done = app.current_checks()
    for source in external.SOURCES:
        if source in done:
            continue  # после рестарта не опрашиваем повторно то, что уже есть
        f = fetch(source, app.company.inn)
        app.checks.append(CheckResult(
            run=app.check_run, source=source, status=f.status, attempts=f.attempts, response=f.response,
            error=f.error, started_at=f.started_at, finished_at=f.finished_at,
        ))
        session.commit()

    data = {s: app.data(s) for s in external.SOURCES}
    failed = [s for s, c in app.current_checks().items() if c.status != "ok"]
    prod = product_policy(app.product.code)

    stops = stop_factors(data, prod, today())
    if stops:
        first = stops[0]
        reason, advice = texts.STOP_FACTORS[first["code"]]
        if first["code"] == "SF04_BUSINESS_TOO_YOUNG":
            reason, advice = sf04_texts(first, app)
        add_decision(app, "REJECTED", stop_factors=stops, reason_codes=[s["code"] for s in stops],
                     reason=reason, advice=advice)
        fire(session, app, "stop_factor_found", Actor.SYSTEM, first["code"])
        return

    if failed:
        add_decision(app, "MANUAL_REVIEW", manual_triggers=["M5_CHECKS_INCOMPLETE"],
                     comment="не ответили: " + ", ".join(failed))
        fire(session, app, "checks_incomplete", Actor.SYSTEM, "M5_CHECKS_INCOMPLETE")
        return

    revenue = revenue_check(data["bank"], float(app.annual_revenue), statement_of(app))
    if revenue.needs_document:
        app.info_requests.append(InfoRequest(reason_code="DATA_MISMATCH", items=[texts.REQUESTS["DATA_MISMATCH"]],
                                             requested_by=Actor.SYSTEM))
        fire(session, app, "data_mismatch", Actor.SYSTEM, "DATA_MISMATCH", f"расхождение {revenue.mismatch:.0%}")
        return
    fire(session, app, "checks_passed", Actor.SYSTEM)


def sf04_texts(sf: dict, app: Application) -> tuple[str, str]:
    """Когда вернуться и какой продукт подойдёт уже сейчас."""
    reason, advice = texts.STOP_FACTORS["SF04_BUSINESS_TOO_YOUNG"]
    reg = app.company.registered_at
    y, m = divmod(reg.month - 1 + sf["min_age"], 12)
    ready = reg.replace(year=reg.year + y, month=m + 1, day=min(reg.day, 28))
    alt = ""
    for code, p in policy()["products"].items():
        if code != app.product.code and p["min_business_age_months"] <= sf["age"]:
            alt = texts.SF04_ALT.format(product=p["name"], months=p["min_business_age_months"])
            break
    return reason.format(age=sf["age"], min_age=sf["min_age"]), advice.format(date=ready.strftime("%d.%m.%Y"), alt=alt)


def run_scoring(session: Session, app: Application) -> None:
    data = {s: app.data(s) for s in external.SOURCES}
    req = Request(
        product_code=app.product.code, amount=int(app.amount), term_months=app.term_months,
        is_legal=app.company.kind == "ul",
        collateral_value=int(app.collateral_value) if app.collateral_value else None,
        reviewed_before=any(h.to_status == Status.MANUAL_REVIEW for h in app.history),
    )
    revenue = revenue_check(data["bank"], float(app.annual_revenue), statement_of(app))
    r = decide(req, data, revenue, today())

    add_decision(
        app, r.outcome, model_version=r.model_version,
        pd=Decimal(str(round(r.pd, 4))) if r.pd is not None else None, grade=r.grade,
        features=r.features, contributions=r.contributions, manual_triggers=r.manual_triggers,
        reason_codes=r.reason_codes, max_amount=r.max_amount, limit_binding=r.limit_binding,
        recommendation=offer_dict(r.offer) if r.outcome == "MANUAL_REVIEW" else None,
        reason=r.reason, advice=r.advice,
        comment=f"PD {r.pd:.2%}, класс {r.grade}" if r.pd is not None else None,
    )
    if r.outcome == "REJECTED":
        fire(session, app, "auto_rejected", Actor.SYSTEM, r.reason_codes[0])
    elif r.outcome == "MANUAL_REVIEW":
        fire(session, app, "sent_to_review", Actor.SYSTEM, r.manual_triggers[0])
    else:
        o = r.offer
        add_offer(app, Actor.SYSTEM, o.kind, o.amount, o.term_months, o.rate, o.monthly_payment,
                  o.alternatives, o.conditions, o.reason, o.advice)
        event = "auto_approved" if r.outcome == "AUTO_APPROVED" else "counter_offer_made"
        fire(session, app, event, Actor.SYSTEM, None if o.kind == "AS_REQUESTED" else o.kind)


def step(session: Session, app: Application, fetch) -> None:
    if app.status == Status.SUBMITTED:
        fire(session, app, "processing_started", Actor.SYSTEM)

    elif app.status == Status.VALIDATION:
        missing = validation_requests(app)
        if missing:
            for code in missing:
                app.info_requests.append(InfoRequest(reason_code=code, items=[texts.REQUESTS[code]], requested_by=Actor.SYSTEM))
            fire(session, app, "info_required", Actor.SYSTEM, missing[0])
        else:
            app.check_run += 1
            fire(session, app, "validation_passed", Actor.SYSTEM)

    elif app.status == Status.CHECKS:
        run_checks(session, app, fetch)

    elif app.status == Status.SCORING:
        run_scoring(session, app)


def process(app_id: int, session_factory=SessionLocal, fetch=external.fetch) -> None:
    with session_factory() as session:
        while True:
            app = session.get(Application, app_id)
            if app is None or app.status not in AUTO:
                return
            try:
                step(session, app, fetch)
                session.commit()
            except Exception:
                session.rollback()
                log.exception("заявка %s: ошибка на шаге конвейера, останавливаемся", app_id)
                return


def expire_overdue(session: Session) -> int:
    """Таймер: заявки, где клиент не ответил вовремя, переводим в «Срок истёк» (T06, T18, T20)."""
    apps = session.scalars(
        select(Application).where(Application.status.in_(EXPIRING), Application.deadline_at < now())
    ).all()
    for app in apps:
        fire(session, app, EXPIRING[app.status], Actor.TIMER)
    session.commit()
    return len(apps)


def timer_loop() -> None:
    while True:
        try:
            with SessionLocal() as session:
                n = expire_overdue(session)
                if n:
                    log.info("истекло заявок: %s", n)
        except Exception:
            log.exception("таймер сроков упал, попробуем в следующий раз")
        time.sleep(settings.timer_interval_seconds)


def resume_unfinished() -> None:
    """После рестарта дожимаем заявки, которые застряли посередине конвейера, и запускаем таймер сроков."""
    with SessionLocal() as session:
        ids = session.scalars(select(Application.id).where(Application.status.in_(AUTO))).all()
    for app_id in ids:
        threading.Thread(target=process, args=(app_id,), daemon=True).start()
    threading.Thread(target=timer_loop, daemon=True).start()


def get_pipeline():
    # через зависимость, чтобы в тестах гонять конвейер синхронно с фейковыми данными
    return process
