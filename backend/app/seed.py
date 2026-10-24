"""Каталог продуктов — из config/decision_policy.yaml, чтобы цифры в кабинете и в решении не разъезжались."""
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Product
from app.policy import policy

DESCRIPTIONS = {
    "OVERDRAFT": "Закрыть кассовый разрыв: уходите в минус по счёту в пределах лимита",
    "WORKING_CAPITAL": "Пополнить оборотные средства без залога: закупка товара, сырья, зарплаты",
    "INVESTMENT": "Купить оборудование, транспорт или недвижимость для бизнеса, под залог",
}


def products_from_policy() -> list[dict]:
    p = policy()
    cheapest = p["market"]["key_rate"] + p["pricing"]["bank_margin"]  # ставка при нулевом риске
    rows = []
    for code, prod in p["products"].items():
        rows.append(dict(
            code=code, name=prod["name"], description=DESCRIPTIONS.get(code, ""),
            min_amount=Decimal(prod["amount_min"]), max_amount=Decimal(prod["amount_max"]),
            min_term_months=prod["term_months_min"], max_term_months=prod["term_months_max"],
            base_rate=Decimal(str(round(max(cheapest, prod["rate_floor"]) * 100, 2))),
            max_rate=Decimal(str(round(prod["rate_cap"] * 100, 2))),
            requires_collateral=prod["secured"], min_business_age_months=prod["min_business_age_months"],
        ))
    return rows


def seed_products(session) -> None:
    for data in products_from_policy():
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
