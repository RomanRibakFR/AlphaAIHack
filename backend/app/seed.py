from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Product

# ставки и лимиты выдуманные, для демо
PRODUCTS = [
    dict(
        code="overdraft",
        name="Овердрафт",
        description="Закрыть кассовый разрыв: уходите в минус по счёту в пределах лимита",
        min_amount=Decimal("100000"), max_amount=Decimal("5000000"),
        min_term_months=1, max_term_months=12,
        base_rate=Decimal("18.50"), requires_collateral=False, min_business_age_months=6,
    ),
    dict(
        code="working_capital",
        name="Оборотный кредит",
        description="Пополнить оборотные средства: закупка товара, сырья, зарплаты",
        min_amount=Decimal("500000"), max_amount=Decimal("20000000"),
        min_term_months=3, max_term_months=36,
        base_rate=Decimal("17.00"), requires_collateral=False, min_business_age_months=12,
    ),
    dict(
        code="investment",
        name="Инвестиционный кредит",
        description="Купить оборудование, транспорт или недвижимость для бизнеса",
        min_amount=Decimal("1000000"), max_amount=Decimal("100000000"),
        min_term_months=12, max_term_months=84,
        base_rate=Decimal("15.50"), requires_collateral=True, min_business_age_months=24,
    ),
]


def seed_products(session) -> None:
    for data in PRODUCTS:
        product = session.scalar(select(Product).where(Product.code == data["code"]))
        if product is None:
            session.add(Product(**data))
        else:
            for k, v in data.items():
                setattr(product, k, v)
    session.commit()


if __name__ == "__main__":
    with SessionLocal() as s:
        seed_products(s)
    print("seed: ok")
