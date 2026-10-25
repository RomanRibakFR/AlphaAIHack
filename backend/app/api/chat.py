"""
Чат с поддержкой.

Переписка привязана к компании, а не к заявке: вопрос часто возникает
до подачи («подойду ли я вообще?») или вовсе не про конкретную заявку.
Сотрудник видит список диалогов и отвечает из своего рабочего места.

Ролей на бэкенде нет, как и везде в прототипе: сторону определяет ручка,
по которой пришло сообщение, а не авторизация.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.inn import is_valid_inn
from app.models import ChatMessage, Company
from app.schemas import ChatIn, ChatSummary, ChatThread

router = APIRouter(prefix="/chat", tags=["Чат с поддержкой"])
backoffice_router = APIRouter(prefix="/backoffice/chats", tags=["Сотрудник банка"])

CLIENT = "client"
SUPPORT = "support"


def check_inn(inn: str) -> str:
    if not is_valid_inn(inn):
        raise HTTPException(422, "Некорректный ИНН")
    return inn


def company_name(session: Session, inn: str) -> str:
    """Имя из базы, если компания уже заводила заявку. Иначе показываем ИНН."""
    name = session.scalar(select(Company.name).where(Company.inn == inn))
    return name or f"ИНН {inn}"


def messages_of(session: Session, inn: str) -> list[ChatMessage]:
    return list(
        session.scalars(
            select(ChatMessage).where(ChatMessage.inn == inn).order_by(ChatMessage.id)
        ).all()
    )


def thread(session: Session, inn: str, unread_for: str) -> ChatThread:
    """Переписка целиком. unread_for — чьи непрочитанные считаем."""
    items = messages_of(session, inn)
    field = "read_by_support" if unread_for == SUPPORT else "read_by_client"
    other = CLIENT if unread_for == SUPPORT else SUPPORT
    unread = sum(1 for m in items if m.author == other and not getattr(m, field))
    return ChatThread(inn=inn, company_name=company_name(session, inn), messages=items, unread=unread)


def mark_read(items: list[ChatMessage], reader: str) -> None:
    """Прочитанными помечаем чужие сообщения — свои и так свои."""
    field = "read_by_support" if reader == SUPPORT else "read_by_client"
    other = CLIENT if reader == SUPPORT else SUPPORT
    for m in items:
        if m.author == other:
            setattr(m, field, True)


def add(session: Session, inn: str, author: str, body: ChatIn) -> None:
    text = body.text.strip()
    if not text:
        raise HTTPException(422, "Сообщение пустое")
    session.add(ChatMessage(inn=inn, author=author, text=text))


# ——— сторона клиента ———


@router.get("", response_model=ChatThread)
def client_thread(inn: str = Query(...), session: Session = Depends(get_session)):
    """Переписка компании с поддержкой. Открыли — значит прочитали."""
    check_inn(inn)
    items = messages_of(session, inn)
    mark_read(items, CLIENT)
    session.commit()
    return thread(session, inn, unread_for=CLIENT)


@router.post("", response_model=ChatThread)
def client_send(body: ChatIn, inn: str = Query(...), session: Session = Depends(get_session)):
    """Клиент пишет в поддержку."""
    check_inn(inn)
    # отвечая, человек уже прочитал то, на что отвечает
    mark_read(messages_of(session, inn), CLIENT)
    add(session, inn, CLIENT, body)
    session.commit()
    return thread(session, inn, unread_for=CLIENT)


# ——— сторона сотрудника банка ———


@backoffice_router.get("", response_model=list[ChatSummary])
def chats(session: Session = Depends(get_session)):
    """Диалоги, новые сверху: сначала те, где клиент ждёт ответа."""
    inns = session.scalars(select(ChatMessage.inn).group_by(ChatMessage.inn)).all()
    out = []
    for inn in inns:
        items = messages_of(session, inn)
        if not items:
            continue
        last = items[-1]
        out.append(
            ChatSummary(
                inn=inn,
                company_name=company_name(session, inn),
                last_text=last.text,
                last_author=last.author,
                last_at=last.created_at,
                unread=sum(1 for m in items if m.author == CLIENT and not m.read_by_support),
            )
        )
    out.sort(key=lambda c: (c.unread > 0, c.last_at), reverse=True)
    return out


@backoffice_router.get("/{inn}", response_model=ChatThread)
def staff_thread(inn: str, session: Session = Depends(get_session)):
    """Переписка с конкретной компанией. Открыли — вопросы считаются прочитанными."""
    check_inn(inn)
    items = messages_of(session, inn)
    mark_read(items, SUPPORT)
    session.commit()
    return thread(session, inn, unread_for=SUPPORT)


@backoffice_router.post("/{inn}", response_model=ChatThread)
def staff_send(inn: str, body: ChatIn, session: Session = Depends(get_session)):
    """Ответ поддержки."""
    check_inn(inn)
    mark_read(messages_of(session, inn), SUPPORT)
    add(session, inn, SUPPORT, body)
    session.commit()
    return thread(session, inn, unread_for=SUPPORT)
