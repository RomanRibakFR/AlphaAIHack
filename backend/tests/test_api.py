import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app
from app.registry import RegistryUnavailable, get_registry
from app.seed import seed_products

VETER = {
    "inn": "7701123451", "ogrn": "1157746123456", "kind": "ul", "name": "ООО «Северный ветер»",
    "okved": "46.90", "registered_at": "2015-03-12", "status": "active",
}


def fake_registry(inn):
    if inn == "7802543212":
        raise RegistryUnavailable("лежит")
    return VETER if inn == VETER["inn"] else None


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

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_registry] = lambda: fake_registry
    yield TestClient(app)
    app.dependency_overrides.clear()


def new_draft(client, **fields):
    body = {"inn": "7701123451", "product_code": "working_capital", **fields}
    r = client.post("/api/applications", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_products_catalog(client):
    codes = [p["code"] for p in client.get("/api/products").json()]
    assert codes == ["overdraft", "working_capital", "investment"]


def test_lookup(client):
    assert client.get("/api/companies/lookup", params={"inn": "7701123451"}).json()["name"] == "ООО «Северный ветер»"
    assert client.get("/api/companies/lookup", params={"inn": "7701123450"}).status_code == 422  # плохая контрольная цифра
    assert client.get("/api/companies/lookup", params={"inn": "5403987653"}).status_code == 404
    assert client.get("/api/companies/lookup", params={"inn": "7802543212"}).status_code == 503


def test_draft_autosave_and_submit(client):
    draft = new_draft(client)
    assert draft["status"]["code"] == "draft"
    assert draft["company"]["name"] == "ООО «Северный ветер»"
    assert set(draft["available_actions"]) == {"edit", "submit", "withdraw"}

    # пустой черновик не отправить, и видно, какие поля подсветить
    r = client.post(f"/api/applications/{draft['id']}/submit")
    assert r.status_code == 422
    assert {p["field"] for p in r.json()["detail"]["problems"]} == {"amount", "term_months", "purpose"}

    client.patch(f"/api/applications/{draft['id']}", json={"amount": "2000000"})
    r = client.patch(f"/api/applications/{draft['id']}", json={"term_months": 12, "purpose": "закупка товара"})
    assert r.json()["amount"] == "2000000.00"
    assert r.json()["estimated_payment"] is not None

    r = client.post(f"/api/applications/{draft['id']}/submit")
    assert r.status_code == 200
    body = r.json()
    assert body["status"]["code"] == "submitted"
    assert body["status"]["title"] == "Рассматриваем заявку"
    assert "edit" not in body["available_actions"]
    assert [h["to_status"] for h in body["history"]] == ["submitted"]


def test_amount_outside_product_limits(client):
    draft = new_draft(client, amount="100", term_months=12, purpose="ремонт")
    r = client.post(f"/api/applications/{draft['id']}/submit")
    assert [p["field"] for p in r.json()["detail"]["problems"]] == ["amount"]


def test_cannot_edit_or_resubmit_after_submit(client):
    draft = new_draft(client, amount="1000000", term_months=6, purpose="закупка")
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
    assert client.get("/api/applications", params={"inn": "5403987653"}).json() == []


def test_unknown_company_and_product(client):
    assert client.post("/api/applications", json={"inn": "5403987653", "product_code": "overdraft"}).status_code == 404
    assert client.post("/api/applications", json={"inn": "7701123451", "product_code": "ipoteka"}).status_code == 422
