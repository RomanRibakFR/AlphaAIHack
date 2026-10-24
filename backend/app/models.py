"""Модель данных — по разделам «Что нужно в модели данных» / «Что сохраняется» в docs/."""
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
    code: Mapped[str] = mapped_column(String(32), unique=True)  # OVERDRAFT, WORKING_CAPITAL, INVESTMENT
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    min_amount: Mapped[Decimal] = mapped_column(Money)
    max_amount: Mapped[Decimal] = mapped_column(Money)
    min_term_months: Mapped[int]
    max_term_months: Mapped[int]
    base_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # «ставка от», % годовых
    max_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # потолок, % годовых
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
    annual_revenue: Mapped[Decimal | None] = mapped_column(Money)  # выручка за 12 мес. со слов клиента
    collateral_type: Mapped[str | None] = mapped_column(String(40))
    collateral_description: Mapped[str | None] = mapped_column(String(255))
    collateral_value: Mapped[Decimal | None] = mapped_column(Money)

    status: Mapped[Status] = mapped_column(str_enum(Status), default=Status.DRAFT, index=True)
    status_changed_at: Mapped[datetime | None]
    deadline_at: Mapped[datetime | None] = mapped_column(index=True)  # до когда ждём клиента
    check_run: Mapped[int] = mapped_column(default=0)  # номер прохода проверок
    sign_code: Mapped[str | None] = mapped_column(String(6))
    sign_attempts: Mapped[int] = mapped_column(default=0)
    version: Mapped[int] = mapped_column(default=1)  # оптимистическая блокировка

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    submitted_at: Mapped[datetime | None]
    issued_at: Mapped[datetime | None]

    __mapper_args__ = {"version_id_col": version}

    company: Mapped[Company] = relationship(back_populates="applications")
    product: Mapped[Product] = relationship()
    history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="application", order_by="StatusHistory.id", cascade="all, delete-orphan"
    )
    checks: Mapped[list["CheckResult"]] = relationship(order_by="CheckResult.id", cascade="all, delete-orphan")
    decisions: Mapped[list["Decision"]] = relationship(order_by="Decision.id", cascade="all, delete-orphan")
    offers: Mapped[list["Offer"]] = relationship(order_by="Offer.id", cascade="all, delete-orphan")
    info_requests: Mapped[list["InfoRequest"]] = relationship(order_by="InfoRequest.id", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship(order_by="Document.id", cascade="all, delete-orphan")

    @property
    def last_decision(self) -> "Decision | None":
        return self.decisions[-1] if self.decisions else None

    @property
    def offer(self) -> "Offer | None":
        return self.offers[-1] if self.offers else None

    def current_checks(self) -> dict[str, "CheckResult"]:
        """Результаты проверок последнего прохода, по источникам."""
        return {c.source: c for c in self.checks if c.run == self.check_run}

    def data(self, source: str) -> dict | None:
        c = self.current_checks().get(source)
        return c.response if c and c.status == "ok" else None


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    transition_id: Mapped[str] = mapped_column(String(4))  # T01…T22
    event: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[Status | None] = mapped_column(str_enum(Status))
    to_status: Mapped[Status] = mapped_column(str_enum(Status))
    actor: Mapped[Actor] = mapped_column(str_enum(Actor))
    reason_code: Mapped[str | None] = mapped_column(String(40))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    application: Mapped[Application] = relationship(back_populates="history")


class CheckResult(Base):
    """Журнал обращений к источникам. Ответ сохраняем как есть — для аудита и пересчёта."""

    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    run: Mapped[int]
    source: Mapped[str] = mapped_column(String(20))  # egrul, fns, zsk, bank, bki
    status: Mapped[str] = mapped_column(String(20))  # ok, not_found, unavailable
    attempts: Mapped[int]
    response: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime]


class Decision(Base):
    """Решение: одно на каждый проход скоринга, стоп-фактор или действие специалиста."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    outcome: Mapped[str] = mapped_column(String(20))  # AUTO_APPROVED, COUNTER_OFFER, MANUAL_REVIEW, REJECTED
    policy_version: Mapped[str] = mapped_column(String(20))
    model_version: Mapped[str | None] = mapped_column(String(40))
    pd: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    grade: Mapped[str | None] = mapped_column(String(1))
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    contributions: Mapped[dict] = mapped_column(JSON, default=dict)
    stop_factors: Mapped[list] = mapped_column(JSON, default=list)
    manual_triggers: Mapped[list] = mapped_column(JSON, default=list)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    max_amount: Mapped[Decimal | None] = mapped_column(Money)
    limit_binding: Mapped[str | None] = mapped_column(String(30))
    recommendation: Mapped[dict | None] = mapped_column(JSON)  # черновик предложения для специалиста
    reason: Mapped[str] = mapped_column(Text, default="")  # для клиента
    advice: Mapped[str] = mapped_column(Text, default="")  # что можно сделать
    decided_by: Mapped[Actor] = mapped_column(str_enum(Actor))
    comment: Mapped[str | None] = mapped_column(Text)  # внутренний, клиенту не показываем
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    type: Mapped[str] = mapped_column(String(20))  # AS_REQUESTED / COUNTER
    counter_kind: Mapped[str | None] = mapped_column(String(20))  # TERM_EXTENDED / AMOUNT_REDUCED
    product_code: Mapped[str] = mapped_column(String(32))
    amount: Mapped[Decimal] = mapped_column(Money)
    term_months: Mapped[int]
    rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))  # % годовых
    monthly_payment: Mapped[Decimal] = mapped_column(Money)
    alternatives: Mapped[list] = mapped_column(JSON, default=list)  # другие варианты суммы и срока
    conditions: Mapped[list] = mapped_column(JSON, default=list)  # например, поручительство собственника
    reason: Mapped[str] = mapped_column(Text, default="")
    advice: Mapped[str] = mapped_column(Text, default="")
    valid_until: Mapped[datetime]
    created_by: Mapped[Actor] = mapped_column(str_enum(Actor))
    chosen_alternative: Mapped[int | None]  # какой вариант выбрал клиент; None — основной
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class InfoRequest(Base):
    """Запрос банка: что клиенту нужно догрузить или дописать."""

    __tablename__ = "info_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    reason_code: Mapped[str] = mapped_column(String(40))  # V02_COLLATERAL, V03_FINANCIAL_STATEMENTS, DATA_MISMATCH, UNDERWRITER
    items: Mapped[list] = mapped_column(JSON)  # [{kind: document|field, code, title, message}]
    requested_by: Mapped[Actor] = mapped_column(str_enum(Actor))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None]


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    info_request_id: Mapped[int | None] = mapped_column(ForeignKey("info_requests.id"))
    doc_type: Mapped[str] = mapped_column(String(40))  # financial_statements, other_bank_statement, other
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int]
    content: Mapped[bytes] = mapped_column(LargeBinary)  # для прототипа храним прямо в БД
    declared_values: Mapped[dict] = mapped_column(JSON, default=dict)  # например, обороты по выписке
    uploaded_at: Mapped[datetime] = mapped_column(server_default=func.now())
