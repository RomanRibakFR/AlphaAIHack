"""
Статусы и переходы заявки — ровно по docs/application-states.md (T01…T22).
Таблица переходов здесь — единственный источник правды для бэкенда.
"""
from dataclasses import dataclass
from enum import StrEnum


class Status(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VALIDATION = "validation"
    INFO_REQUESTED = "info_requested"
    CHECKS = "checks"
    SCORING = "scoring"
    MANUAL_REVIEW = "manual_review"
    OFFER_PROPOSED = "offer_proposed"
    SIGNING = "signing"
    ISSUED = "issued"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Actor(StrEnum):
    CLIENT = "client"
    SYSTEM = "system"
    UNDERWRITER = "underwriter"
    TIMER = "timer"


S, A = Status, Actor
FINAL = {S.ISSUED, S.REJECTED, S.CANCELLED, S.EXPIRED}


@dataclass(frozen=True)
class Transition:
    id: str
    src: Status | None  # None — из любого нефинального
    event: str
    dst: Status
    actor: Actor


TRANSITIONS = [
    Transition("T01", S.DRAFT, "submit", S.SUBMITTED, A.CLIENT),
    Transition("T02", S.SUBMITTED, "processing_started", S.VALIDATION, A.SYSTEM),
    Transition("T03", S.VALIDATION, "validation_passed", S.CHECKS, A.SYSTEM),
    Transition("T04", S.VALIDATION, "info_required", S.INFO_REQUESTED, A.SYSTEM),
    Transition("T05", S.INFO_REQUESTED, "info_provided", S.VALIDATION, A.CLIENT),
    Transition("T06", S.INFO_REQUESTED, "info_expired", S.EXPIRED, A.TIMER),
    Transition("T07", S.CHECKS, "checks_passed", S.SCORING, A.SYSTEM),
    Transition("T08", S.CHECKS, "stop_factor_found", S.REJECTED, A.SYSTEM),
    Transition("T09", S.CHECKS, "checks_incomplete", S.MANUAL_REVIEW, A.SYSTEM),
    Transition("T22", S.CHECKS, "data_mismatch", S.INFO_REQUESTED, A.SYSTEM),
    Transition("T10", S.SCORING, "auto_approved", S.OFFER_PROPOSED, A.SYSTEM),
    Transition("T11", S.SCORING, "counter_offer_made", S.OFFER_PROPOSED, A.SYSTEM),
    Transition("T12", S.SCORING, "sent_to_review", S.MANUAL_REVIEW, A.SYSTEM),
    Transition("T13", S.SCORING, "auto_rejected", S.REJECTED, A.SYSTEM),
    Transition("T14", S.MANUAL_REVIEW, "underwriter_approved", S.OFFER_PROPOSED, A.UNDERWRITER),
    Transition("T15", S.MANUAL_REVIEW, "underwriter_rejected", S.REJECTED, A.UNDERWRITER),
    Transition("T16", S.MANUAL_REVIEW, "underwriter_requested_info", S.INFO_REQUESTED, A.UNDERWRITER),
    Transition("T17", S.OFFER_PROPOSED, "offer_accepted", S.SIGNING, A.CLIENT),
    Transition("T18", S.OFFER_PROPOSED, "offer_expired", S.EXPIRED, A.TIMER),
    Transition("T19", S.SIGNING, "signed", S.ISSUED, A.CLIENT),
    Transition("T20", S.SIGNING, "signing_expired", S.EXPIRED, A.TIMER),
    Transition("T21", None, "cancelled", S.CANCELLED, A.CLIENT),
]


class TransitionError(Exception):
    pass


def find_transition(current: Status, event: str, actor: Actor) -> Transition:
    for t in TRANSITIONS:
        if t.event == event and (t.src == current or (t.src is None and current not in FINAL)):
            if t.actor != actor:
                raise TransitionError(f"{actor} не может выполнить «{event}» (только {t.actor})")
            return t
    raise TransitionError(f"Событие «{event}» недопустимо в статусе {current}")


def events_for(current: Status, actor: Actor) -> list[str]:
    return [
        t.event for t in TRANSITIONS
        if t.actor == actor and (t.src == current or (t.src is None and current not in FINAL))
    ]


# ---- что видит клиент (тексты — исследование Полины, раздел 6 статусной модели) ----

REVIEWING = {S.SUBMITTED, S.VALIDATION, S.CHECKS, S.SCORING}

_REVIEWING_TEXT = (
    "Рассматриваем заявку",
    "Проверяем данные компании → смотрим кредитную историю → готовим решение. "
    "Мы сообщим здесь, как только решение будет готово.",
)

CLIENT_VIEW: dict[Status, tuple[str, str]] = {
    S.DRAFT: ("Черновик", "Заполните заявку и отправьте её в банк."),
    S.SUBMITTED: _REVIEWING_TEXT,
    S.VALIDATION: _REVIEWING_TEXT,
    S.CHECKS: _REVIEWING_TEXT,
    S.SCORING: _REVIEWING_TEXT,
    S.MANUAL_REVIEW: (
        "Рассматриваем заявку",
        "Заявку смотрит специалист банка — так бывает с крупными суммами или нестандартными данными. "
        "Если что-то понадобится, напишем здесь.",
    ),
    S.INFO_REQUESTED: ("Требуется дополнение", "Чтобы продолжить, загрузите то, что мы запросили. Заявка продолжится с того же места."),
    S.OFFER_PROPOSED: ("Есть предложение", "Проверьте условия и примите предложение или откажитесь."),  # заголовок уточняется по типу
    S.SIGNING: ("Подпишите документы", "Введите код подтверждения, чтобы подписать договор."),
    S.ISSUED: ("Кредит выдан", "Деньги зачислены на расчётный счёт."),
    S.REJECTED: ("Отказ", "Сейчас мы не можем выдать кредит. Причина и что можно сделать — ниже."),
    S.CANCELLED: ("Заявка отменена", "Можно подать новую заявку в любой момент."),
    S.EXPIRED: ("Срок истёк", "Мы не получили ответ вовремя, поэтому заявка закрыта. Можно подать новую."),
}

CLIENT_STAGES = [
    ("company_check", "Проверяем данные компании"),
    ("credit_history", "Смотрим кредитную историю"),
    ("decision", "Готовим решение"),
]
