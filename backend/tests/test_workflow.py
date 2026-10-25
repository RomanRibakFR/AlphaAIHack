import pytest

from app.statuses import Actor, Status, TransitionError
from app.workflow import fire


def test_fire_writes_history_with_transition_id(session, draft):
    fire(session, draft, "submit", Actor.CLIENT)
    fire(session, draft, "processing_started", Actor.SYSTEM)
    session.commit()

    assert draft.status == Status.VALIDATION
    assert draft.submitted_at is not None
    assert [(h.transition_id, h.from_status, h.to_status) for h in draft.history] == [
        ("T01", Status.DRAFT, Status.SUBMITTED),
        ("T02", Status.SUBMITTED, Status.VALIDATION),
    ]


def test_bad_event_changes_nothing(session, draft):
    with pytest.raises(TransitionError):
        fire(session, draft, "signed", Actor.CLIENT)
    assert draft.status == Status.DRAFT
    assert draft.history == []


def test_waiting_for_client_sets_deadline(session, draft):
    for event, actor in [("submit", Actor.CLIENT), ("processing_started", Actor.SYSTEM), ("info_required", Actor.SYSTEM)]:
        fire(session, draft, event, actor)
    assert draft.status == Status.INFO_REQUESTED
    assert (draft.deadline_at - draft.status_changed_at).days == 14  # из timeouts_days политики

    fire(session, draft, "cancelled", Actor.CLIENT, reason_code="client_withdrew")
    assert draft.deadline_at is None
    assert draft.history[-1].reason_code == "client_withdrew"
