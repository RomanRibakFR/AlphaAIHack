from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Product
from app.schemas import ProductOut

router = APIRouter(prefix="/products", tags=["Продукты"])


@router.get("", response_model=list[ProductOut])
def list_products(session: Session = Depends(get_session)):
    """Каталог кредитных продуктов."""
    return session.scalars(select(Product).order_by(Product.min_amount)).all()
