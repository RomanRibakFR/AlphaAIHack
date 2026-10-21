from fastapi import APIRouter, Depends, HTTPException, Query

from app.inn import is_valid_inn
from app.registry import RegistryUnavailable, get_registry
from app.schemas import RegistryCompany

router = APIRouter(prefix="/companies", tags=["Компании"])


def lookup_or_fail(inn: str, registry) -> dict:
    if not is_valid_inn(inn):
        raise HTTPException(422, "Некорректный ИНН")
    try:
        data = registry(inn)
    except RegistryUnavailable:
        raise HTTPException(503, "Реестр временно недоступен, попробуйте позже")
    if data is None:
        raise HTTPException(404, "Компания с таким ИНН не найдена")
    return data


@router.get("/lookup", response_model=RegistryCompany)
def lookup(inn: str = Query(..., description="ИНН компании или ИП"), registry=Depends(get_registry)):
    """Данные компании из реестра — для автозаполнения анкеты."""
    return lookup_or_fail(inn, registry)
