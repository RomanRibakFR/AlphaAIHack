from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.statuses import Actor, Status


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str
    min_amount: Decimal
    max_amount: Decimal
    min_term_months: int
    max_term_months: int
    base_rate: Decimal = Field(description="Ставка от, % годовых")
    max_rate: Decimal = Field(description="Ставка до, % годовых")
    requires_collateral: bool
    min_business_age_months: int


class CompanyCard(BaseModel):
    inn: str
    ogrn: str | None = None
    kind: Literal["ul", "ip"]
    name: str
    okved: str | None = None
    okved_name: str | None = None
    registered_at: date | None = None
    status: str
    address: str | None = None
    director: str | None = None


class _ApplicationFields(BaseModel):
    amount: Decimal | None = Field(None, gt=0)
    term_months: int | None = Field(None, gt=0)
    purpose: str | None = None
    annual_revenue: Decimal | None = Field(None, gt=0, description="Выручка за последние 12 месяцев")
    collateral_type: str | None = Field(None, description="Вид залога, для инвестиционного кредита (REAL_ESTATE, EQUIPMENT, VEHICLE)")
    collateral_description: str | None = None
    collateral_value: Decimal | None = Field(None, gt=0, description="Стоимость залога, ₽")


class ApplicationCreate(_ApplicationFields):
    inn: str
    product_code: str


class ApplicationUpdate(_ApplicationFields):
    product_code: str | None = None


class AcceptBody(BaseModel):
    alternative: int | None = Field(None, description="Номер варианта из offer.alternatives; пусто — основной")


class SignBody(BaseModel):
    code: str


class CompanyShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inn: str
    name: str
    kind: str


class ProductShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str


class StatusView(BaseModel):
    code: Status
    title: str
    hint: str


class ReviewStep(BaseModel):
    code: str
    title: str
    state: Literal["done", "current", "pending"]


class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transition_id: str
    from_status: Status | None
    to_status: Status
    actor: Actor
    reason_code: str | None
    comment: str | None
    created_at: datetime


class RequestItem(BaseModel):
    kind: Literal["document", "field"]
    code: str
    title: str
    message: str


class InfoRequestOut(BaseModel):
    id: int
    reason_code: str
    items: list[RequestItem]
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_type: str
    filename: str
    size: int
    declared_values: dict
    uploaded_at: datetime


class OfferVariant(BaseModel):
    amount: Decimal
    term_months: int
    monthly_payment: Decimal


class OfferOut(BaseModel):
    type: Literal["AS_REQUESTED", "COUNTER"]
    counter_kind: str | None
    amount: Decimal
    term_months: int
    requested_amount: Decimal
    requested_term_months: int
    rate: Decimal = Field(description="% годовых")
    monthly_payment: Decimal
    total_payment: Decimal
    alternatives: list[OfferVariant]
    conditions: list[str]
    chosen_alternative: int | None
    valid_until: datetime
    reason: str
    advice: str
    text: str


class Rejection(BaseModel):
    reason: str
    advice: str
    text: str


class Payment(BaseModel):
    n: int
    date: date
    payment: Decimal
    principal: Decimal
    interest: Decimal
    balance: Decimal


class ApplicationOut(BaseModel):
    id: int
    status: StatusView
    review_steps: list[ReviewStep] | None = None
    company: CompanyShort
    product: ProductShort
    amount: Decimal | None
    term_months: int | None
    purpose: str
    annual_revenue: Decimal | None
    collateral_type: str | None
    collateral_description: str | None
    collateral_value: Decimal | None
    estimated_payment: Decimal | None
    available_actions: list[str]
    info_requests: list[InfoRequestOut]
    documents: list[DocumentOut]
    offer: OfferOut | None = None
    rejection: Rejection | None = None
    sign_code: str | None = Field(None, description="В реальном банке пришёл бы в SMS — у нас показываем в кабинете")
    contract_number: str | None = None
    schedule: list[Payment] | None = None
    deadline_at: datetime | None
    history: list[HistoryItem]
    version: int
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    issued_at: datetime | None


class ApplicationListItem(BaseModel):
    id: int
    status: StatusView
    product: ProductShort
    amount: Decimal | None
    term_months: int | None
    updated_at: datetime


class Problem(BaseModel):
    field: str
    message: str


# ---- для сотрудника банка ----

class CheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    status: str
    attempts: int
    response: dict | None
    error: str | None
    started_at: datetime
    finished_at: datetime


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outcome: str
    policy_version: str
    model_version: str | None
    pd: Decimal | None
    pd_at_requested_terms: Decimal | None
    grade: str | None
    lgd: Decimal | None
    product_pd_max: Decimal | None
    model_inputs: dict
    features: dict
    contributions: dict
    clipping_warnings: list[dict]
    stop_factors: list[dict]
    manual_triggers: list[str]
    reason_codes: list[str]
    max_amount: Decimal | None
    limit_binding: str | None
    recommendation: dict | None
    reason: str
    advice: str
    decided_by: Actor
    comment: str | None
    created_at: datetime


class QueueItem(BaseModel):
    id: int
    company: CompanyShort
    product: ProductShort
    amount: Decimal | None
    term_months: int | None
    status: Status
    pd: Decimal | None
    grade: str | None
    triggers: list[str] = Field(description="Почему заявка у специалиста")
    submitted_at: datetime | None


class BackofficeApplication(BaseModel):
    application: ApplicationOut
    checks: list[CheckOut]
    decisions: list[DecisionOut]


class UnderwriterDecision(BaseModel):
    action: Literal["approve", "reject", "request_info"]
    comment: str = Field(..., min_length=1, description="Комментарий специалиста — обязателен (внутренний)")
    amount: Decimal | None = Field(None, gt=0, description="approve: сумма; по умолчанию — рекомендация системы")
    term_months: int | None = Field(None, gt=0)
    rate: Decimal | None = Field(None, gt=0, description="approve: % годовых; по умолчанию — рекомендация системы")
    reason_code: str | None = Field(None, description="reject: код причины")
    reason: str | None = Field(None, description="reject: причина для клиента")
    advice: str | None = Field(None, description="reject: что можно сделать")
    items: list[str] | None = Field(None, description="request_info: other_bank_statement, financial_statements, other, collateral")
    message: str | None = Field(None, description="request_info: что и зачем нужно — увидит клиент")


# ---- чат с поддержкой ----

class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author: Literal["client", "support"]
    text: str
    created_at: datetime


class ChatThread(BaseModel):
    inn: str
    company_name: str
    messages: list[ChatMessageOut]
    unread: int = Field(description="Сколько сообщений другой стороны ещё не прочитано")


class ChatSummary(BaseModel):
    inn: str
    company_name: str
    last_text: str
    last_author: Literal["client", "support"]
    last_at: datetime
    unread: int


class ChatIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
