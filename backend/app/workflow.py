from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Application, StatusHistory
from app.policy import policy
from app.statuses import Actor, Status, find_transition


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def timeout(status: Status) -> timedelta | None:
    """Сколько ждём клиента в статусе. Для демо можно сократить переменными окружения."""
    override = {
        Status.INFO_REQUESTED: settings.timeout_info_requested_minutes,
        Status.OFFER_PROPOSED: settings.timeout_offer_minutes,
        Status.SIGNING: settings.timeout_signing_minutes,
    }.get(status)
    if override:
        return timedelta(minutes=override)
    days = policy()["timeouts_days"]
    key = {Status.INFO_REQUESTED: "info_requested", Status.OFFER_PROPOSED: "offer_proposed", Status.SIGNING: "signing"}.get(status)
    return timedelta(days=days[key]) if key else None


def fire(
    session: Session, app: Application, event: str, actor: Actor,
    reason_code: str | None = None, comment: str | None = None,
) -> str:
    """Единственное место, где меняется статус: проверка по таблице переходов, история, срок ожидания."""
    t = find_transition(app.status, event, actor)
    session.add(StatusHistory(
        application=app, transition_id=t.id, event=event, from_status=app.status, to_status=t.dst,
        actor=actor, reason_code=reason_code, comment=comment,
    ))
    app.status = t.dst
    app.status_changed_at = now()
    wait = timeout(t.dst)
    app.deadline_at = now() + wait if wait else None
    if t.id == "T01":
        app.submitted_at = now()
    return t.id
