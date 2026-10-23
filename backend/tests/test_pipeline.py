"""Сквозные сценарии: от отправки заявки до выдачи / отказа, по одной компании на исход."""
from decimal import Decimal

from tests.test_api import client, full_draft  # noqa: F401  — фикстура


def submit(client, draft):
    r = client.post(f"/api/applications/{draft['id']}/submit")
    assert r.status_code == 200, r.text
    # конвейер в тестах отрабатывает сразу, поэтому сразу смотрим итог
    return client.get(f"/api/applications/{draft['id']}").json()


def statuses(app):
    return [h["to_status"] for h in app["history"]]


def test_approve_accept_sign_issue(client):
    app = submit(client, full_draft(client))
    assert app["status"]["code"] == "approved"
    assert statuses(app) == ["submitted", "validation", "external_checks", "scoring", "approved"]
    offer = app["offer"]
    assert offer["is_counter"] is False
    assert Decimal(offer["amount"]) == Decimal("5000000")
    assert Decimal("14") <= Decimal(offer["rate"]) < Decimal("15")
    assert set(app["available_actions"]) == {"accept", "decline"}

    app = client.post(f"/api/applications/{app['id']}/accept").json()
    assert app["status"]["code"] == "signing"
    code = app["sign_code"]
    assert len(code) == 6

    assert client.post(f"/api/applications/{app['id']}/sign", json={"code": "nope"}).status_code == 422
    app = client.post(f"/api/applications/{app['id']}/sign", json={"code": code}).json()
    assert app["status"]["code"] == "issued"
    assert app["sign_code"] is None
    assert app["contract_number"].startswith("КД-")
    schedule = app["schedule"]
    assert len(schedule) == 24
    assert sum(Decimal(p["principal"]) for p in schedule) == Decimal("5000000")
    assert Decimal(schedule[-1]["balance"]) == 0


def test_counter_offer_and_decline(client):
    app = submit(client, full_draft(client, "7802543212", amount="3000000", annual_revenue="10000000"))
    assert app["status"]["code"] == "counter_offer"
    offer = app["offer"]
    assert offer["is_counter"] is True
    assert Decimal(offer["amount"]) < Decimal("3000000")
    assert "платежи по кредитам" in offer["text"]

    app = client.post(f"/api/applications/{app['id']}/decline").json()
    assert app["status"]["code"] == "declined_by_client"


def test_stop_factor_rejects_with_reason(client):
    app = submit(client, full_draft(client, "7711234560", amount="2000000", annual_revenue="13000000"))
    assert app["status"]["code"] == "rejected"
    assert "ликвидации" in app["rejection"]["reason"]
    assert app["rejection"]["advice"]
    assert app["offer"] is None


def test_revenue_mismatch_asks_for_document_then_approves(client):
    draft = full_draft(client, "6602345677", amount="5000000", annual_revenue="30000000")
    app = submit(client, draft)
    assert app["status"]["code"] == "needs_info"
    assert app["status"]["title"] == "Требуется дополнение"
    [req] = app["info_requests"]
    assert req["document_kind"] == "bank_statement"

    # без документа повторно не отправить
    r = client.post(f"/api/applications/{app['id']}/submit")
    assert r.status_code == 422
    assert r.json()["detail"]["problems"][0]["field"] == "documents"

    r = client.post(f"/api/applications/{app['id']}/documents", data={"kind": "bank_statement"},
                    files={"file": ("vypiska.pdf", b"%PDF-1.4 fake", "application/pdf")})
    assert r.status_code == 200
    assert r.json()["documents"][0]["filename"] == "vypiska.pdf"

    app = submit(client, draft)
    assert app["status"]["code"] == "approved"
    assert app["info_requests"] == []


def test_manual_review_then_underwriter_approves(client):
    app = submit(client, full_draft(client, "540612345667", amount="1000000", term_months=12, annual_revenue="4000000"))
    assert app["status"]["code"] == "manual_review"
    assert app["status"]["title"] == "Рассматривает специалист"

    queue = client.get("/api/backoffice/applications").json()
    assert [q["id"] for q in queue] == [app["id"]]
    assert queue[0]["reason"] == "пограничная оценка риска"

    details = client.get(f"/api/backoffice/applications/{app['id']}").json()
    assert set(details["checks"]) == {"registry", "bki", "fns", "bank"}
    assert len(details["decisions"][0]["factors"]) == 5

    r = client.post(f"/api/backoffice/applications/{app['id']}/decision", json={"action": "approve", "comment": "ок, клиент давний"})
    assert r.status_code == 200
    app = client.get(f"/api/applications/{app['id']}").json()
    assert app["status"]["code"] == "approved"
    assert app["offer"]["amount"] == "1000000.00"
    assert app["history"][-1]["actor"] == "underwriter"


def test_underwriter_request_info_and_validation(client):
    app = submit(client, full_draft(client, "540612345667", amount="1000000", term_months=12, annual_revenue="4000000"))
    url = f"/api/backoffice/applications/{app['id']}/decision"

    assert client.post(url, json={"action": "reject"}).status_code == 422  # нет причины
    assert client.post(url, json={"action": "counter_offer", "amount": "2000000", "reason": "x"}).status_code == 422  # больше запрошенного

    r = client.post(url, json={"action": "request_info", "document_kind": "tax_return", "message": "Загрузите декларацию за 2025 год"})
    assert r.status_code == 200
    app = client.get(f"/api/applications/{app['id']}").json()
    assert app["status"]["code"] == "needs_info"
    assert app["info_requests"][0]["document_title"] == "Налоговая декларация"


def test_external_service_down_goes_to_manual_review(client):
    app = submit(client, full_draft(client, "5403987653", amount="2000000", annual_revenue="6000000"))
    assert app["status"]["code"] == "manual_review"
    queue = client.get("/api/backoffice/applications").json()
    assert queue[0]["reason"] == "не удалось получить данные из внешних источников"
