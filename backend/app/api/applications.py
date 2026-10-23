import secrets
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import texts
from app.api.companies import lookup_or_fail
from app.applications import EDITABLE, open_requests, problems_for_submit, to_list_item, to_out
from app.db import get_session
from app.models import Application, Company, Document, Product
from app.pipeline import get_pipeline
from app.registry import get_registry
from app.schemas import ApplicationCreate, ApplicationListItem, ApplicationOut, ApplicationUpdate, SignBody
from app.statuses import Actor, Status, TransitionError
from app.workflow import change_status

router = APIRouter(prefix="/applications", tags=["Заявки"])

MAX_FILE_SIZE = 10 * 1024 * 1024


def get_app(session: Session, app_id: int) -> Application:
    app = session.get(Application, app_id)
    if app is None:
        raise HTTPException(404, "Заявка не найдена")
    return app


def get_product(session: Session, code: str) -> Product:
    product = session.scalar(select(Product).where(Product.code == code))
    if product is None:
        raise HTTPException(422, f"Нет такого продукта: {code}")
    return product


def move(session: Session, app: Application, target: Status, actor: Actor = Actor.CLIENT) -> None:
    try:
        change_status(session, app, target, actor)
    except TransitionError as e:
        raise HTTPException(409, str(e))


@router.post("", response_model=ApplicationOut, status_code=201)
def create(body: ApplicationCreate, session: Session = Depends(get_session), registry=Depends(get_registry)):
    """Создать черновик. Компанию подтягиваем из реестра по ИНН."""
    data = lookup_or_fail(body.inn, registry)
    product = get_product(session, body.product_code)

    company = session.scalar(select(Company).where(Company.inn == body.inn))
    if company is None:
        company = Company(inn=body.inn)
        session.add(company)
    company.ogrn = data.get("ogrn")
    company.kind = data["kind"]
    company.name = data["name"]
    company.okved = data.get("okved")
    if data.get("registered_at"):
        company.registered_at = date.fromisoformat(data["registered_at"])

    app = Application(
        company=company, product=product, amount=body.amount, term_months=body.term_months,
        purpose=body.purpose, annual_revenue=body.annual_revenue,
    )
    session.add(app)
    session.commit()
    return to_out(app)


@router.get("", response_model=list[ApplicationListItem])
def list_for_company(inn: str = Query(...), session: Session = Depends(get_session)):
    """Заявки компании, свежие сверху. Пока без авторизации — по ИНН."""
    apps = session.scalars(
        select(Application).join(Company).where(Company.inn == inn).order_by(Application.updated_at.desc())
    ).all()
    return [to_list_item(a) for a in apps]


@router.get("/{app_id}", response_model=ApplicationOut)
def get_one(app_id: int, session: Session = Depends(get_session)):
    """Заявка целиком: статус для клиента, предложение или причина отказа, кнопки, история."""
    return to_out(get_app(session, app_id))


@router.patch("/{app_id}", response_model=ApplicationOut)
def update(app_id: int, body: ApplicationUpdate, session: Session = Depends(get_session)):
    """Автосохранение черновика. Можно присылать только изменённые поля."""
    app = get_app(session, app_id)
    if app.status not in EDITABLE:
        raise HTTPException(409, "Заявку уже нельзя редактировать")

    changes = body.model_dump(exclude_unset=True)
    if "product_code" in changes:
        app.product = get_product(session, changes.pop("product_code"))
    for field, value in changes.items():
        if field == "purpose" and value is None:
            value = ""
        setattr(app, field, value)

    session.commit()
    return to_out(app)


@router.post("/{app_id}/documents", response_model=ApplicationOut)
def upload_document(
    app_id: int,
    kind: str = Form(..., description="bank_statement, financial_report, tax_return, other"),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Загрузить документ (например, по дозапросу банка)."""
    app = get_app(session, app_id)
    if app.status not in EDITABLE:
        raise HTTPException(409, "Сейчас документы загрузить нельзя")
    if kind not in texts.DOCUMENT_KINDS:
        raise HTTPException(422, "Неизвестный тип документа")
    content = file.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Файл больше 10 МБ")

    app.documents.append(Document(
        kind=kind, filename=file.filename or "file", content_type=file.content_type or "application/octet-stream",
        size=len(content), content=content,
    ))
    session.commit()
    return to_out(app)


@router.post("/{app_id}/submit", response_model=ApplicationOut)
def submit(
    app_id: int, background: BackgroundTasks,
    session: Session = Depends(get_session), pipeline=Depends(get_pipeline),
):
    """Отправить в банк. Если чего-то не хватает — 422 со списком полей. Дальше заявку ведёт конвейер."""
    app = get_app(session, app_id)
    problems = problems_for_submit(app)
    if problems:
        raise HTTPException(422, {"message": "Заявка заполнена не полностью", "problems": [p.model_dump() for p in problems]})

    move(session, app, Status.SUBMITTED)
    for r in open_requests(app):  # документы догружены — дозапрос закрыт
        r.resolved_at = datetime.now(timezone.utc)
    session.commit()

    background.add_task(pipeline, app.id)
    return to_out(app)


@router.post("/{app_id}/withdraw", response_model=ApplicationOut)
def withdraw(app_id: int, session: Session = Depends(get_session)):
    """Отозвать заявку (только до решения банка)."""
    app = get_app(session, app_id)
    move(session, app, Status.WITHDRAWN)
    session.commit()
    return to_out(app)


@router.post("/{app_id}/accept", response_model=ApplicationOut)
def accept(app_id: int, session: Session = Depends(get_session)):
    """Принять предложение банка — переходим к подписанию."""
    app = get_app(session, app_id)
    move(session, app, Status.SIGNING)
    app.sign_code = f"{secrets.randbelow(10**6):06d}"
    session.commit()
    return to_out(app)


@router.post("/{app_id}/decline", response_model=ApplicationOut)
def decline(app_id: int, session: Session = Depends(get_session)):
    """Отказаться от предложения банка."""
    app = get_app(session, app_id)
    move(session, app, Status.DECLINED_BY_CLIENT)
    session.commit()
    return to_out(app)


@router.post("/{app_id}/sign", response_model=ApplicationOut)
def sign(app_id: int, body: SignBody, session: Session = Depends(get_session)):
    """Подписать договор кодом. Подпись условная, деньги «зачисляются» сразу."""
    app = get_app(session, app_id)
    if app.status == Status.SIGNING and body.code != app.sign_code:
        raise HTTPException(422, "Неверный код подтверждения")
    move(session, app, Status.ISSUED)
    app.issued_at = datetime.now(timezone.utc)
    app.sign_code = None
    session.commit()
    return to_out(app)
