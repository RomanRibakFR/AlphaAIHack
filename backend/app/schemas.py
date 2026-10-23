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
    base_rate: Decimal
    max_rate: Decimal
    requires_collateral: bool
    min_business_age_months: int


class RegistryCompany(BaseModel):
    inn: str
    ogrn: str | None = None
    kind: str
    name: str
    okved: str | None = None
    okved_name: str | None = None
    registered_at: date | None = None
    status: str
    address: str | None = None
    director: str | None = None


class ApplicationCreate(BaseModel):
    inn: str
    product_code: str
    amount: Decimal | None = Field(None, gt=0)
    term_months: int | None = Field(None, gt=0)
    purpose: str = ""
    annual_revenue: Decimal | None = Field(None, gt=0)


class ApplicationUpdate(BaseModel):
    product_code: str | None = None
    amount: Decimal | None = Field(None, gt=0)
    term_months: int | None = Field(None, gt=0)
    purpose: str | None = None
    annual_revenue: Decimal | None = Field(None, gt=0)


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
    title: str
    state: Literal["done", "current", "pending"]


class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_status: Status | None
    to_status: Status
    actor: Actor
    comment: str | None
    created_at: datetime


class InfoRequestOut(BaseModel):
    document_kind: str
    document_title: str
    message: str
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    filename: str
    size: int
    uploaded_at: datetime


class Offer(BaseModel):
    amount: Decimal
    requested_amount: Decimal
    term_months: int
    rate: Decimal
    monthly_payment: Decimal
    total_payment: Decimal
    is_counter: bool
    advice: str = ""
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
    estimated_payment: Decimal | None
    available_actions: list[str]
    info_requests: list[InfoRequestOut]
    documents: list[DocumentOut]
    offer: Offer | None = None
    rejection: Rejection | None = None
    sign_code: str | None = Field(None, description="В реальном банке пришёл бы в SMS — у нас показываем в кабинете")
    contract_number: str | None = None
    schedule: list[Payment] | None = None
    history: list[HistoryItem]
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

class Factor(BaseModel):
    code: str
    label: str
    value: str
    points: int
    max_points: int


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    outcome: Status
    score: int | None
    pd: Decimal | None
    factors: list[Factor]
    stop_factors: list[dict]
    amount: Decimal | None
    term_months: int | None
    rate: Decimal | None
    monthly_payment: Decimal | None
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
    reason: str | None
    submitted_at: datetime | None


class BackofficeApplication(BaseModel):
    application: ApplicationOut
    checks: dict[str, dict]
    decisions: list[DecisionOut]


class UnderwriterDecision(BaseModel):
    action: Literal["approve", "counter_offer", "reject", "request_info"]
    amount: Decimal | None = Field(None, gt=0, description="Для контрпредложения")
    term_months: int | None = Field(None, gt=0)
    rate: Decimal | None = Field(None, gt=0, description="% годовых; по умолчанию — расчётная ставка скоринга")
    reason: str | None = Field(None, description="Причина для клиента (контрпредложение, отказ)")
    advice: str | None = Field(None, description="Что можно сделать (для отказа)")
    document_kind: str | None = Field(None, description="Для дозапроса: bank_statement, financial_report, tax_return, other")
    message: str | None = Field(None, description="Для дозапроса: что и зачем нужно")
    comment: str | None = Field(None, description="Внутренний комментарий, клиент не видит")
