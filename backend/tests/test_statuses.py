import pytest

from app.statuses import CLIENT_VIEW, FINAL, TRANSITIONS, Actor, Status, TransitionError, events_for, find_transition


def test_transition_ids_unique_and_match_docs():
    ids = [t.id for t in TRANSITIONS]
    assert len(ids) == len(set(ids)) == 22
    assert set(ids) == {f"T{i:02d}" for i in range(1, 23)}


def test_happy_path():
    path = [
        (Status.DRAFT, "submit", Actor.CLIENT),
        (Status.SUBMITTED, "processing_started", Actor.SYSTEM),
        (Status.VALIDATION, "validation_passed", Actor.SYSTEM),
        (Status.CHECKS, "checks_passed", Actor.SYSTEM),
        (Status.SCORING, "auto_approved", Actor.SYSTEM),
        (Status.OFFER_PROPOSED, "offer_accepted", Actor.CLIENT),
        (Status.SIGNING, "signed", Actor.CLIENT),
    ]
    ids = [find_transition(s, e, a).id for s, e, a in path]
    assert ids == ["T01", "T02", "T03", "T07", "T10", "T17", "T19"]


def test_client_cannot_do_system_steps():
    with pytest.raises(TransitionError):
        find_transition(Status.SCORING, "auto_approved", Actor.CLIENT)


def test_underwriter_only_from_manual_review():
    assert find_transition(Status.MANUAL_REVIEW, "underwriter_approved", Actor.UNDERWRITER).id == "T14"
    with pytest.raises(TransitionError):
        find_transition(Status.REJECTED, "underwriter_approved", Actor.UNDERWRITER)  # сценарий S13


def test_cancel_from_any_non_final():
    for s in Status:
        if s in FINAL:
            with pytest.raises(TransitionError):
                find_transition(s, "cancelled", Actor.CLIENT)
        else:
            assert find_transition(s, "cancelled", Actor.CLIENT).id == "T21"


def test_final_statuses_are_dead_ends():
    for s in FINAL:
        for actor in Actor:
            assert events_for(s, actor) == []


def test_every_status_reachable_and_has_client_text():
    reachable = {Status.DRAFT} | {t.dst for t in TRANSITIONS}
    assert reachable == set(Status)
    assert set(CLIENT_VIEW) == set(Status)
