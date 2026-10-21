from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Application, StatusHistory
from app.statuses import Actor, Status, check_transition


def change_status(
    session: Session, app: Application, target: Status, actor: Actor, comment: str | None = None
) -> None:
    """Единственное место, где меняется статус заявки. Пишет историю."""
    check_transition(app.status, target, actor)

    session.add(
        StatusHistory(application=app, from_status=app.status, to_status=target, actor=actor, comment=comment)
    )
    app.status = target
    if target == Status.SUBMITTED and app.submitted_at is None:
        app.submitted_at = datetime.now(timezone.utc)
