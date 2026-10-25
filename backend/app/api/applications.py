import secrets
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import texts
from app.api.companies import lookup_or_fail
from app.applications import open_requests, problems_for_info, problems_for_submit, to_list_item, to_out
from app.db import get_session
from app.models import Application, Company, Document, Product
from app.pipeline import get_pipeline
from app.registry import get_registry
from app.schemas import AcceptBody, ApplicationCreate, ApplicationListItem, ApplicationOut, ApplicationUpdate, SignBody
from app.statuses import Actor, Status, TransitionError
from app.workflow import fire, now

router = APIRouter(prefix="/applications", tags=["Заявки"])

MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_SIGN_ATTEMPTS = 5
COLLATERAL_FIELDS = {"collateral_type", "collateral_description", "collateral_value"}


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


def event(session: Session, app: Application, name: str, actor: Actor = Actor.CLIENT, reason_code: str | None = None,
          comment: str | None = None) -> None:
    try:
        fire(session, app, name, actor, reason_code, comment)
    except TransitionError as e:
        raise HTTPException(409, {"message": str(e), "status": app.status})


def new_sign_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


@router.post("", response_model=ApplicationOut, status_code=201)
def create(body: ApplicationCreate, session: Session = Depends(get_session), registry=Depends(get_registry)):
    """Создать черновик. Компанию подтягиваем из реестра по ИНН."""
    card = lookup_or_fail(body.inn, registry)
    product = get_product(session, body.product_code)

    company = session.scalar(select(Company).where(Company.inn == body.inn))
    if company is None:
        company = Company(inn=body.inn)
        session.add(company)
    company.ogrn, company.kind, company.name, company.okved = card["ogrn"], card["kind"], card["name"], card["okved"]
    company.registered_at = date.fromisoformat(card["registered_at"])

    fields = body.model_dump(exclude={"inn", "product_code"}, exclude_none=True)
    app = Application(company=company, product=product, purpose=fields.pop("purpose", ""), **fields)
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
    """Заявка целиком: статус, подшаги, запросы банка, предложение или причина отказа, кнопки, история."""
    return to_out(get_app(session, app_id))


@router.patch("/{app_id}", response_model=ApplicationOut)
def update(app_id: int, body: ApplicationUpdate, session: Session = Depends(get_session)):
    """Автосохранение черновика: только изменённые поля. После отправки можно дописать только залог по запросу банка."""
    app = get_app(session, app_id)
    changes = body.model_dump(exclude_unset=True)
    if app.status == Status.INFO_REQUESTED:
        if set(changes) - COLLATERAL_FIELDS:
            raise HTTPException(409, "После отправки анкету менять нельзя — только то, что запросил банк")
    elif app.status != Status.DRAFT:
        raise HTTPException(409, "Заявку уже нельзя редактировать")

    if "product_code" in changes:
        app.product = get_product(session, changes.pop("product_code"))
    for field, value in changes.items():
        setattr(app, field, "" if field == "purpose" and value is None else value)
    session.commit()
    return to_out(app)


@router.post("/{app_id}/documents", response_model=ApplicationOut)
def upload_document(
    app_id: int,
    doc_type: str = Form(..., description="financial_statements, other_bank_statement, other"),
    file: UploadFile = File(...),
    declared_turnover: int | None = Form(None, description="Для выписки: сумма поступлений по ней, ₽"),
    declared_months: int = Form(6, description="Для выписки: за сколько месяцев"),
    session: Session = Depends(get_session),
):
    """Загрузить документ — при отправке или по запросу банка."""
    app = get_app(session, app_id)
    if app.status not in {Status.DRAFT, Status.INFO_REQUESTED}:
        raise HTTPException(409, "Сейчас документы загрузить нельзя")
    if doc_type not in texts.DOCUMENT_TYPES:
        raise HTTPException(422, "Неизвестный тип документа")
    declared = {}
    if doc_type == "other_bank_statement":
        if not declared_turnover or not 1 <= declared_months <= 12:
            raise HTTPException(422, "Для выписки укажите сумму поступлений и за сколько месяцев (1–12)")
        declared = {"turnover": declared_turnover, "months": declared_months}
    content = file.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Файл больше 10 МБ")

    request = next((r for r in open_requests(app) if any(i["code"] == doc_type for i in r.items)), None)
    app.documents.append(Document(
        doc_type=doc_type, filename=file.filename or "file", content_type=file.content_type or "application/octet-stream",
        size=len(content), content=content, declared_values=declared, info_request_id=request.id if request else None,
    ))
    session.commit()
    return to_out(app)


@router.post("/{app_id}/submit", response_model=ApplicationOut)
def submit(app_id: int, background: BackgroundTasks, session: Session = Depends(get_session), pipeline=Depends(get_pipeline)):
    """Отправить в банк (T01). Если анкета неполная — 422 со списком полей. Дальше заявку ведёт конвейер."""
    app = get_app(session, app_id)
    if app.status != Status.DRAFT:
        # повторное нажатие не создаёт дубль и не меняет статус
        raise HTTPException(409, {"message": "Заявка уже отправлена", "status": app.status})
    problems = problems_for_submit(app)
    if problems:
        raise HTTPException(422, {"message": "Заявка заполнена не полностью", "problems": [p.model_dump() for p in problems]})
    event(session, app, "submit")
    session.commit()
    background.add_task(pipeline, app.id)
    return to_out(app)


@router.post("/{app_id}/provide-info", response_model=ApplicationOut)
def provide_info(app_id: int, background: BackgroundTasks, session: Session = Depends(get_session), pipeline=Depends(get_pipeline)):
    """Клиент дополнил то, что запросил банк (T05) — заявка проходит проверки заново."""
    app = get_app(session, app_id)
    problems = problems_for_info(app)
    if problems:
        raise HTTPException(422, {"message": "Ещё не всё из запрошенного", "problems": [p.model_dump() for p in problems]})
    event(session, app, "info_provided")
    for r in open_requests(app):
        r.resolved_at = now()
    session.commit()
    background.add_task(pipeline, app.id)
    return to_out(app)


@router.post("/{app_id}/cancel", response_model=ApplicationOut)
def cancel(app_id: int, session: Session = Depends(get_session)):
    """Отозвать заявку (T21, client_withdrew) — из любого незавершённого статуса."""
    app = get_app(session, app_id)
    event(session, app, "cancelled", reason_code="client_withdrew")
    session.commit()
    return to_out(app)


@router.post("/{app_id}/decline", response_model=ApplicationOut)
def decline(app_id: int, session: Session = Depends(get_session)):
    """Отказаться от предложения банка (T21, offer_declined)."""
    app = get_app(session, app_id)
    if app.status != Status.OFFER_PROPOSED:
        raise HTTPException(409, {"message": "Нет предложения, от которого можно отказаться", "status": app.status})
    event(session, app, "cancelled", reason_code="offer_declined")
    session.commit()
    return to_out(app)


@router.post("/{app_id}/accept", response_model=ApplicationOut)
def accept(app_id: int, body: AcceptBody | None = None, session: Session = Depends(get_session)):
    """Принять предложение (T17), можно выбрать один из вариантов. Дальше — подписание кодом."""
    app = get_app(session, app_id)
    offer = app.offer
    if app.status == Status.OFFER_PROPOSED and offer.valid_until < now():
        raise HTTPException(409, {"message": "Срок действия предложения истёк", "status": app.status})
    choice = body.alternative if body else None
    if choice is not None and not 0 <= choice < len(offer.alternatives):
        raise HTTPException(422, "Нет такого варианта")
    event(session, app, "offer_accepted")
    offer.chosen_alternative = choice
    app.sign_code, app.sign_attempts = new_sign_code(), 0
    session.commit()
    return to_out(app)


@router.post("/{app_id}/sign", response_model=ApplicationOut)
def sign(app_id: int, body: SignBody, session: Session = Depends(get_session)):
    """Подписать договор кодом (T19). Подпись условная, выдача моделируется в той же операции."""
    app = get_app(session, app_id)
    if app.status != Status.SIGNING:
        raise HTTPException(409, {"message": "Заявка не на подписании", "status": app.status})
    if body.code != app.sign_code:
        app.sign_attempts += 1
        message = "Неверный код подтверждения"
        if app.sign_attempts >= MAX_SIGN_ATTEMPTS:
            app.sign_code, app.sign_attempts = new_sign_code(), 0
            message += ". Попыток больше не осталось — выдали новый код"
        session.commit()
        raise HTTPException(400, message)
    event(session, app, "signed")
    app.issued_at, app.sign_code = now(), None
    session.commit()
    return to_out(app)
