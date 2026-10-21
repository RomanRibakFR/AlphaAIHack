import pytest

from app.statuses import CLIENT_VIEW, FINAL, TRANSITIONS, Actor, Status, TransitionError, check_transition, next_statuses


def test_happy_path_to_issued():
    path = [
        (Status.DRAFT, Status.SUBMITTED, Actor.CLIENT),
        (Status.SUBMITTED, Status.VALIDATION, Actor.SYSTEM),
        (Status.VALIDATION, Status.EXTERNAL_CHECKS, Actor.SYSTEM),
        (Status.EXTERNAL_CHECKS, Status.SCORING, Actor.SYSTEM),
        (Status.SCORING, Status.APPROVED, Actor.SYSTEM),
        (Status.APPROVED, Status.SIGNING, Actor.CLIENT),
        (Status.SIGNING, Status.ISSUED, Actor.CLIENT),
    ]
    for current, target, actor in path:
        check_transition(current, target, actor)


def test_cannot_skip_steps():
    with pytest.raises(TransitionError):
        check_transition(Status.DRAFT, Status.APPROVED, Actor.SYSTEM)


def test_client_cannot_approve_himself():
    with pytest.raises(TransitionError):
        check_transition(Status.MANUAL_REVIEW, Status.APPROVED, Actor.CLIENT)


def test_only_underwriter_decides_manual_review():
    check_transition(Status.MANUAL_REVIEW, Status.APPROVED, Actor.UNDERWRITER)
    with pytest.raises(TransitionError):
        check_transition(Status.MANUAL_REVIEW, Status.APPROVED, Actor.SYSTEM)


def test_needs_info_loops_back_to_submitted():
    check_transition(Status.VALIDATION, Status.NEEDS_INFO, Actor.SYSTEM)
    check_transition(Status.NEEDS_INFO, Status.SUBMITTED, Actor.CLIENT)


def test_withdraw_only_before_decision():
    check_transition(Status.SCORING, Status.WITHDRAWN, Actor.CLIENT)
    with pytest.raises(TransitionError):
        check_transition(Status.APPROVED, Status.WITHDRAWN, Actor.CLIENT)


def test_final_statuses_are_dead_ends():
    for status in FINAL:
        assert next_statuses(status, Actor.CLIENT) == []
        assert next_statuses(status, Actor.SYSTEM) == []
        assert next_statuses(status, Actor.UNDERWRITER) == []


def test_every_status_reachable_and_has_client_text():
    reachable = {Status.DRAFT} | {to for (_, to) in TRANSITIONS}
    assert reachable == set(Status)
    assert set(CLIENT_VIEW) == set(Status)
