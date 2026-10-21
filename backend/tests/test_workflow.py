import pytest

from app.statuses import Actor, Status, TransitionError
from app.workflow import change_status


def test_change_status_writes_history(session, draft):
    change_status(session, draft, Status.SUBMITTED, Actor.CLIENT)
    change_status(session, draft, Status.VALIDATION, Actor.SYSTEM, "автопроверка")
    session.commit()

    assert draft.status == Status.VALIDATION
    assert draft.submitted_at is not None
    assert [(h.from_status, h.to_status, h.actor) for h in draft.history] == [
        (Status.DRAFT, Status.SUBMITTED, Actor.CLIENT),
        (Status.SUBMITTED, Status.VALIDATION, Actor.SYSTEM),
    ]
    assert draft.history[1].comment == "автопроверка"


def test_bad_transition_changes_nothing(session, draft):
    with pytest.raises(TransitionError):
        change_status(session, draft, Status.ISSUED, Actor.CLIENT)

    assert draft.status == Status.DRAFT
    assert draft.history == []


def test_resubmit_keeps_first_submitted_at(session, draft):
    change_status(session, draft, Status.SUBMITTED, Actor.CLIENT)
    first = draft.submitted_at
    change_status(session, draft, Status.VALIDATION, Actor.SYSTEM)
    change_status(session, draft, Status.NEEDS_INFO, Actor.SYSTEM)
    change_status(session, draft, Status.SUBMITTED, Actor.CLIENT)

    assert draft.submitted_at == first
