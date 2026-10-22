from datetime import date, datetime
from decimal import Decimal

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


class ApplicationUpdate(BaseModel):
    product_code: str | None = None
    amount: Decimal | None = Field(None, gt=0)
    term_months: int | None = Field(None, gt=0)
    purpose: str | None = None


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


class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_status: Status | None
    to_status: Status
    actor: Actor
    comment: str | None
    created_at: datetime


class ApplicationOut(BaseModel):
    id: int
    status: StatusView
    company: CompanyShort
    product: ProductShort
    amount: Decimal | None
    term_months: int | None
    purpose: str
    estimated_payment: Decimal | None
    available_actions: list[str]
    history: list[HistoryItem]
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None


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
