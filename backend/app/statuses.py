from enum import StrEnum


class Status(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VALIDATION = "validation"
    NEEDS_INFO = "needs_info"
    EXTERNAL_CHECKS = "external_checks"
    SCORING = "scoring"
    MANUAL_REVIEW = "manual_review"
    APPROVED = "approved"
    COUNTER_OFFER = "counter_offer"
    SIGNING = "signing"
    ISSUED = "issued"
    REJECTED = "rejected"
    DECLINED_BY_CLIENT = "declined_by_client"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class Actor(StrEnum):
    CLIENT = "client"
    SYSTEM = "system"
    UNDERWRITER = "underwriter"


S, A = Status, Actor

# кто может перевести заявку из одного статуса в другой
TRANSITIONS: dict[tuple[Status, Status], set[Actor]] = {
    (S.DRAFT, S.SUBMITTED): {A.CLIENT},
    (S.SUBMITTED, S.VALIDATION): {A.SYSTEM},
    (S.VALIDATION, S.EXTERNAL_CHECKS): {A.SYSTEM},
    (S.VALIDATION, S.NEEDS_INFO): {A.SYSTEM},
    (S.NEEDS_INFO, S.SUBMITTED): {A.CLIENT},
    (S.EXTERNAL_CHECKS, S.SCORING): {A.SYSTEM},
    (S.EXTERNAL_CHECKS, S.NEEDS_INFO): {A.SYSTEM},  # данные анкеты не сошлись с внешними
    (S.EXTERNAL_CHECKS, S.MANUAL_REVIEW): {A.SYSTEM},  # внешний сервис не ответил
    (S.SCORING, S.APPROVED): {A.SYSTEM},
    (S.SCORING, S.COUNTER_OFFER): {A.SYSTEM},
    (S.SCORING, S.REJECTED): {A.SYSTEM},
    (S.SCORING, S.MANUAL_REVIEW): {A.SYSTEM},
    (S.MANUAL_REVIEW, S.APPROVED): {A.UNDERWRITER},
    (S.MANUAL_REVIEW, S.COUNTER_OFFER): {A.UNDERWRITER},
    (S.MANUAL_REVIEW, S.REJECTED): {A.UNDERWRITER},
    (S.MANUAL_REVIEW, S.NEEDS_INFO): {A.UNDERWRITER},
    (S.APPROVED, S.SIGNING): {A.CLIENT},
    (S.COUNTER_OFFER, S.SIGNING): {A.CLIENT},
    (S.APPROVED, S.DECLINED_BY_CLIENT): {A.CLIENT},
    (S.COUNTER_OFFER, S.DECLINED_BY_CLIENT): {A.CLIENT},
    (S.SIGNING, S.ISSUED): {A.CLIENT},
    # клиент не ответил вовремя
    (S.NEEDS_INFO, S.EXPIRED): {A.SYSTEM},
    (S.APPROVED, S.EXPIRED): {A.SYSTEM},
    (S.COUNTER_OFFER, S.EXPIRED): {A.SYSTEM},
}

# отозвать можно в любой момент до решения
for _s in (S.DRAFT, S.SUBMITTED, S.VALIDATION, S.NEEDS_INFO, S.EXTERNAL_CHECKS, S.SCORING, S.MANUAL_REVIEW):
    TRANSITIONS[(_s, S.WITHDRAWN)] = {A.CLIENT}

FINAL = {S.ISSUED, S.REJECTED, S.DECLINED_BY_CLIENT, S.WITHDRAWN, S.EXPIRED}


class TransitionError(Exception):
    pass


def check_transition(current: Status, target: Status, actor: Actor) -> None:
    allowed = TRANSITIONS.get((current, target))
    if allowed is None:
        raise TransitionError(f"Нельзя перейти из {current} в {target}")
    if actor not in allowed:
        raise TransitionError(f"{actor} не может перевести заявку из {current} в {target}")


def next_statuses(current: Status, actor: Actor) -> list[Status]:
    return [to for (frm, to), actors in TRANSITIONS.items() if frm == current and actor in actors]


# что видит клиент: внутренние шаги банка склеены в один «рассматриваем» (тексты — от Полины)
_REVIEWING = (
    "Рассматриваем заявку",
    "Проверяем данные компании → смотрим кредитную историю → готовим решение. "
    "Мы сообщим здесь, как только решение будет готово.",
)

CLIENT_VIEW: dict[Status, tuple[str, str]] = {
    S.DRAFT: ("Черновик", "Заполните заявку и отправьте её в банк"),
    S.SUBMITTED: _REVIEWING,
    S.VALIDATION: _REVIEWING,
    S.EXTERNAL_CHECKS: _REVIEWING,
    S.SCORING: _REVIEWING,
    S.MANUAL_REVIEW: (
        "Рассматривает специалист",
        "Заявку смотрит специалист банка — так бывает с крупными суммами или нестандартными данными. "
        "Если что-то понадобится, напишем здесь.",
    ),
    S.NEEDS_INFO: ("Требуется дополнение", "Чтобы продолжить, загрузите документ из запроса. Заявка продолжится с того же места."),
    S.APPROVED: ("Одобрено", "Проверьте условия и подпишите в кабинете."),
    S.COUNTER_OFFER: ("Есть предложение", "Мы готовы выдать кредит на других условиях. Можно принять предложение или отказаться."),
    S.SIGNING: ("Подписание", "Проверьте договор и подтвердите подпись кодом."),
    S.ISSUED: ("Кредит выдан", "Деньги зачислены на счёт, график платежей — в карточке заявки."),
    S.REJECTED: ("Отказ", "Сейчас мы не можем выдать кредит. Причина и что можно сделать — ниже."),
    S.DECLINED_BY_CLIENT: ("Вы отказались", "Предложение отклонено. Можно подать новую заявку в любой момент."),
    S.WITHDRAWN: ("Отозвана", "Вы отозвали заявку."),
    S.EXPIRED: ("Истекла", "Срок ответа истёк, можно подать новую заявку."),
}

# подшаги «Рассматриваем заявку», чтобы клиент видел прогресс
REVIEW_STEPS = [
    (S.VALIDATION, "Проверяем данные компании"),
    (S.EXTERNAL_CHECKS, "Смотрим кредитную историю"),
    (S.SCORING, "Готовим решение"),
]
