from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import models
from app.db import Base


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
        code="overdraft", name="Овердрафт",
        min_amount=Decimal("100000"), max_amount=Decimal("5000000"),
        min_term_months=1, max_term_months=12, base_rate=Decimal("13"), max_rate=Decimal("22"),
    )
    company = models.Company(inn="7700000001", kind="ul", name="ООО Ромашка")
    app = models.Application(company=company, product=product, amount=Decimal("1000000"), term_months=6)
    session.add(app)
    session.commit()
    return app
