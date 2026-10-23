import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app
from app.pipeline import get_pipeline, process
from app.registry import get_registry
from app.seed import seed_products
from tests import fakes


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        seed_products(s)

    def session_override():
        with Session() as s:
            yield s

    # конвейер в тестах — синхронно, без пауз и на фейковых данных
    def run_pipeline(app_id):
        process(app_id, session_factory=Session, fetch_all=fakes.fetch_all, delay=0)

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_registry] = lambda: fakes.registry
    app.dependency_overrides[get_pipeline] = lambda: run_pipeline
    yield TestClient(app)
    app.dependency_overrides.clear()


def new_draft(client, inn="7701123451", **fields):
    body = {"inn": inn, "product_code": "working_capital", **fields}
    r = client.post("/api/applications", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def full_draft(client, inn="7701123451", **fields):
    defaults = dict(amount="5000000", term_months=24, purpose="закупка товара", annual_revenue="48000000")
    return new_draft(client, inn, **{**defaults, **fields})


def test_products_catalog(client):
    codes = [p["code"] for p in client.get("/api/products").json()]
    assert codes == ["overdraft", "working_capital", "investment"]


def test_lookup(client):
    assert client.get("/api/companies/lookup", params={"inn": "7701123451"}).json()["name"] == "ООО «Северный ветер»"
    assert client.get("/api/companies/lookup", params={"inn": "7701123450"}).status_code == 422  # плохая контрольная цифра
    assert client.get("/api/companies/lookup", params={"inn": "772045678925"}).status_code == 404
    assert client.get("/api/companies/lookup", params={"inn": fakes.REGISTRY_DOWN_INN}).status_code == 503


def test_draft_autosave_and_submit(client):
    draft = new_draft(client)
    assert draft["status"]["code"] == "draft"
    assert draft["company"]["name"] == "ООО «Северный ветер»"
    assert set(draft["available_actions"]) == {"edit", "submit", "withdraw"}

    # пустой черновик не отправить, и видно, какие поля подсветить
    r = client.post(f"/api/applications/{draft['id']}/submit")
    assert r.status_code == 422
    assert {p["field"] for p in r.json()["detail"]["problems"]} == {"amount", "term_months", "purpose", "annual_revenue"}

    client.patch(f"/api/applications/{draft['id']}", json={"amount": "2000000", "annual_revenue": "48000000"})
    r = client.patch(f"/api/applications/{draft['id']}", json={"term_months": 12, "purpose": "закупка товара"})
    assert r.json()["amount"] == "2000000.00"
    assert r.json()["estimated_payment"] is not None

    r = client.post(f"/api/applications/{draft['id']}/submit")
    assert r.status_code == 200
    body = r.json()
    assert body["status"]["code"] == "submitted"
    assert body["status"]["title"] == "Рассматриваем заявку"
    assert [s["state"] for s in body["review_steps"]] == ["pending", "pending", "pending"]
    assert "edit" not in body["available_actions"]


def test_amount_outside_product_limits(client):
    draft = new_draft(client, amount="100", term_months=12, purpose="ремонт", annual_revenue="1000000")
    r = client.post(f"/api/applications/{draft['id']}/submit")
    assert [p["field"] for p in r.json()["detail"]["problems"]] == ["amount"]


def test_cannot_edit_after_submit(client):
    draft = full_draft(client)
    client.post(f"/api/applications/{draft['id']}/submit")

    assert client.patch(f"/api/applications/{draft['id']}", json={"amount": "5"}).status_code == 409
    assert client.post(f"/api/applications/{draft['id']}/submit").status_code == 409


def test_withdraw(client):
    draft = new_draft(client)
    r = client.post(f"/api/applications/{draft['id']}/withdraw")
    assert r.json()["status"]["code"] == "withdrawn"
    assert r.json()["available_actions"] == []


def test_list_by_inn(client):
    new_draft(client)
    new_draft(client)
    assert len(client.get("/api/applications", params={"inn": "7701123451"}).json()) == 2
    assert client.get("/api/applications", params={"inn": "7802543212"}).json() == []


def test_unknown_company_and_product(client):
    assert client.post("/api/applications", json={"inn": "772045678925", "product_code": "overdraft"}).status_code == 404
    assert client.post("/api/applications", json={"inn": "7701123451", "product_code": "ipoteka"}).status_code == 422
