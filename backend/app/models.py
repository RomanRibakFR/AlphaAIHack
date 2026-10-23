from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Enum, ForeignKey, LargeBinary, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.statuses import Actor, Status

Money = Numeric(14, 2)


def str_enum(enum_cls):
    # храним как строку, а не нативный enum postgres — проще мигрировать
    return Enum(enum_cls, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e])


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    min_amount: Mapped[Decimal] = mapped_column(Money)
    max_amount: Mapped[Decimal] = mapped_column(Money)
    min_term_months: Mapped[int]
    max_term_months: Mapped[int]
    base_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # % годовых, для самых надёжных
    max_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # потолок для рисковых
    requires_collateral: Mapped[bool] = mapped_column(default=False)
    min_business_age_months: Mapped[int] = mapped_column(default=0)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    inn: Mapped[str] = mapped_column(String(12), unique=True)
    ogrn: Mapped[str | None] = mapped_column(String(15))
    kind: Mapped[str] = mapped_column(String(2))  # "ul" или "ip"
    name: Mapped[str] = mapped_column(String(255))
    okved: Mapped[str | None] = mapped_column(String(10))
    registered_at: Mapped[date | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    applications: Mapped[list["Application"]] = relationship(back_populates="company")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    # в черновике могут быть пустыми, проверяем при отправке
    amount: Mapped[Decimal | None] = mapped_column(Money)
    term_months: Mapped[int | None]
    purpose: Mapped[str] = mapped_column(String(255), default="")
    annual_revenue: Mapped[Decimal | None] = mapped_column(Money)  # со слов клиента
    status: Mapped[Status] = mapped_column(str_enum(Status), default=Status.DRAFT, index=True)
    sign_code: Mapped[str | None] = mapped_column(String(6))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    submitted_at: Mapped[datetime | None]
    issued_at: Mapped[datetime | None]

    company: Mapped[Company] = relationship(back_populates="applications")
    product: Mapped[Product] = relationship()
    history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="application", order_by="StatusHistory.id", cascade="all, delete-orphan"
    )
    checks: Mapped[list["CheckResult"]] = relationship(order_by="CheckResult.id", cascade="all, delete-orphan")
    decisions: Mapped[list["Decision"]] = relationship(order_by="Decision.id", cascade="all, delete-orphan")
    info_requests: Mapped[list["InfoRequest"]] = relationship(order_by="InfoRequest.id", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(order_by="Document.id", cascade="all, delete-orphan")

    @property
    def last_decision(self) -> "Decision | None":
        return self.decisions[-1] if self.decisions else None

    def check(self, source: str) -> dict | None:
        for c in reversed(self.checks):
            if c.source == source:
                return c.payload
        return None


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    from_status: Mapped[Status | None] = mapped_column(str_enum(Status))
    to_status: Mapped[Status] = mapped_column(str_enum(Status))
    actor: Mapped[Actor] = mapped_column(str_enum(Actor))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    application: Mapped[Application] = relationship(back_populates="history")


class CheckResult(Base):
    """Ответ внешнего источника (реестр, БКИ, ФНС, счёт) — сохраняем как есть для аудита."""

    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    source: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    outcome: Mapped[Status] = mapped_column(str_enum(Status))
    score: Mapped[int | None]
    pd: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    factors: Mapped[list] = mapped_column(JSON, default=list)
    stop_factors: Mapped[list] = mapped_column(JSON, default=list)
    amount: Mapped[Decimal | None] = mapped_column(Money)
    term_months: Mapped[int | None]
    rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    monthly_payment: Mapped[Decimal | None] = mapped_column(Money)
    reason: Mapped[str] = mapped_column(Text, default="")  # для клиента
    advice: Mapped[str] = mapped_column(Text, default="")  # что можно сделать
    decided_by: Mapped[Actor] = mapped_column(str_enum(Actor))
    comment: Mapped[str | None] = mapped_column(Text)  # внутренний, клиенту не показываем
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class InfoRequest(Base):
    """Дозапрос: что банк просит догрузить."""

    __tablename__ = "info_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    document_kind: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None]


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int]
    content: Mapped[bytes] = mapped_column(LargeBinary)  # для демо храним прямо в БД
    uploaded_at: Mapped[datetime] = mapped_column(server_default=func.now())
