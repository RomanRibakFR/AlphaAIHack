from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import config, models
from app.db import Base, get_session
from app.main import app as fastapi_app
from app.pipeline import get_pipeline, process
from app.registry import get_registry
from app.seed import seed_products
from tests import fakes


@pytest.fixture(autouse=True)
def as_of(monkeypatch):
    # данные моков выгружены на 24.10.2026 — от этой даты и считаем, чтобы тесты не плыли со временем
    monkeypatch.setattr(config.settings, "data_as_of", date(2026, 10, 24))


# для юнит-тестов хватает sqlite в памяти, postgres не нужен
@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def draft(session):
    product = models.Product(
        code="WORKING_CAPITAL", name="Оборотный кредит",
        min_amount=Decimal("300000"), max_amount=Decimal("30000000"),
        min_term_months=6, max_term_months=36, base_rate=Decimal("15"), max_rate=Decimal("25"),
    )
    company = models.Company(inn="0001000010", kind="ul", name="ООО «Утренний кофе»")
    app = models.Application(company=company, product=product, amount=Decimal("3000000"), term_months=24)
    session.add(app)
    session.commit()
    return app


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session_ = sessionmaker(bind=engine)
    with Session_() as s:
        seed_products(s)

    def session_override():
        with Session_() as s:
            yield s

    # конвейер в тестах — синхронно и на данных из файлов моков
    def run_pipeline(app_id):
        process(app_id, session_factory=Session_, fetch=fakes.fetch)

    fastapi_app.dependency_overrides[get_session] = session_override
    fastapi_app.dependency_overrides[get_registry] = lambda: fakes.registry
    fastapi_app.dependency_overrides[get_pipeline] = lambda: run_pipeline
    c = TestClient(fastapi_app)
    c.session_factory = Session_
    yield c
    fastapi_app.dependency_overrides.clear()
