from datetime import timedelta

from app.models import Application
from app.pipeline import expire_overdue
from app.workflow import now
from tests import fakes

KOFE = "0001000010"  # C01, автоодобрение


def new_draft(client, inn=KOFE, **fields):
    r = client.post("/api/applications", json={"inn": inn, "product_code": "WORKING_CAPITAL", **fields})
    assert r.status_code == 201, r.text
    return r.json()


def full_draft(client, inn=KOFE, **fields):
    defaults = dict(amount=3_000_000, term_months=24, purpose="закупка", annual_revenue=31_500_000)
    return new_draft(client, inn, **{**defaults, **fields})


def test_products_from_policy(client):
    products = {p["code"]: p for p in client.get("/api/products").json()}
    assert list(products) == ["OVERDRAFT", "WORKING_CAPITAL", "INVESTMENT"]
    assert products["WORKING_CAPITAL"]["base_rate"] == "15.00"  # ключевая 14% + маржа 1%
    assert products["INVESTMENT"]["requires_collateral"] is True


def test_lookup(client):
    card = client.get("/api/companies/lookup", params={"inn": KOFE}).json()
    assert card["name"] == "ООО «Утренний кофе»" and card["kind"] == "ul"
    assert client.get("/api/companies/lookup", params={"inn": "000100000244"}).json()["kind"] == "ip"
    assert client.get("/api/companies/lookup", params={"inn": "0001000011"}).status_code == 422
    assert client.get("/api/companies/lookup", params={"inn": "7701123451"}).status_code == 404
    assert client.get("/api/companies/lookup", params={"inn": fakes.REGISTRY_DOWN_INN}).status_code == 503


def test_submit_needs_full_form(client):
    draft = new_draft(client)
    assert set(draft["available_actions"]) == {"edit", "upload_document", "submit", "cancel"}
    r = client.post(f"/api/applications/{draft['id']}/submit")
    assert r.status_code == 422
    assert {p["field"] for p in r.json()["detail"]["problems"]} == {"amount", "term_months", "purpose", "annual_revenue"}

    r = client.patch(f"/api/applications/{draft['id']}", json={"amount": 100})
    r = client.patch(f"/api/applications/{draft['id']}", json={"term_months": 24, "purpose": "закупка", "annual_revenue": 31_500_000})
    assert r.json()["estimated_payment"] is not None
    r = client.post(f"/api/applications/{draft['id']}/submit")
    assert [p["field"] for p in r.json()["detail"]["problems"]] == ["amount"]  # V01: сумма вне продукта


def test_resubmit_is_idempotent_and_form_frozen(client):
    draft = full_draft(client)
    assert client.post(f"/api/applications/{draft['id']}/submit").status_code == 200
    assert client.post(f"/api/applications/{draft['id']}/submit").status_code == 409
    assert client.patch(f"/api/applications/{draft['id']}", json={"amount": 5}).status_code == 409
    assert len(client.get("/api/applications", params={"inn": KOFE}).json()) == 1


def test_wrong_sign_code(client):
    app = full_draft(client)
    client.post(f"/api/applications/{app['id']}/submit")
    app = client.post(f"/api/applications/{app['id']}/accept", json={}).json()
    r = client.post(f"/api/applications/{app['id']}/sign", json={"code": "nope"})
    assert r.status_code == 400  # сценарий S14
    assert client.get(f"/api/applications/{app['id']}").json()["status"]["code"] == "signing"


def test_issue_gives_schedule(client):
    app = full_draft(client)
    client.post(f"/api/applications/{app['id']}/submit")
    app = client.post(f"/api/applications/{app['id']}/accept", json={}).json()
    app = client.post(f"/api/applications/{app['id']}/sign", json={"code": app["sign_code"]}).json()
    assert app["status"]["code"] == "issued"
    assert len(app["schedule"]) == 24
    assert app["schedule"][-1]["balance"] == "0.00"


def test_cancel_while_processing_and_decline_offer(client):
    a = full_draft(client)
    assert client.post(f"/api/applications/{a['id']}/cancel").json()["status"]["code"] == "cancelled"

    b = full_draft(client)
    client.post(f"/api/applications/{b['id']}/submit")
    r = client.post(f"/api/applications/{b['id']}/decline").json()
    assert r["status"]["code"] == "cancelled"
    assert r["history"][-1]["transition_id"] == "T21"


def test_counter_offer_choose_alternative(client):
    d = fakes.by_id("C04")
    app = full_draft(client, d["egrul"]["inn"], amount=6_000_000, annual_revenue=19_800_000)
    client.post(f"/api/applications/{app['id']}/submit")
    app = client.get(f"/api/applications/{app['id']}").json()
    offer = app["offer"]
    assert app["status"]["title"] == "Есть предложение"
    assert offer["counter_kind"] == "AMOUNT_REDUCED" and offer["alternatives"]
    assert "Есть и другой вариант" in offer["text"]

    app = client.post(f"/api/applications/{app['id']}/accept", json={"alternative": 0}).json()
    app = client.post(f"/api/applications/{app['id']}/sign", json={"code": app["sign_code"]}).json()
    assert len(app["schedule"]) == offer["alternatives"][0]["term_months"]


def test_timer_expires_forgotten_offer(client):
    app = full_draft(client)
    client.post(f"/api/applications/{app['id']}/submit")
    with client.session_factory() as s:
        a = s.get(Application, app["id"])
        a.deadline_at = now() - timedelta(minutes=1)
        s.commit()
        assert expire_overdue(s) == 1
    app = client.get(f"/api/applications/{app['id']}").json()
    assert app["status"]["code"] == "expired"
    assert app["history"][-1]["transition_id"] == "T18"


def test_underwriter_needs_comment_and_cannot_touch_other_statuses(client):
    app = full_draft(client)  # черновик, не у специалиста
    url = f"/api/backoffice/applications/{app['id']}/decision"
    assert client.post(url, json={"action": "approve"}).status_code == 422  # нет комментария
    assert client.post(url, json={"action": "approve", "comment": "ок"}).status_code == 409


def test_underwriter_request_info_returns_to_underwriter(client):
    # сценарий S07: специалист запросил документ, клиент дополнил — заявка снова у специалиста (M7)
    d = fakes.by_id("C05")
    app = full_draft(client, d["egrul"]["inn"], amount=2_000_000, annual_revenue=26_900_000)
    client.post(f"/api/applications/{app['id']}/submit")
    r = client.post(f"/api/backoffice/applications/{app['id']}/decision",
                    json={"action": "request_info", "items": ["other"], "message": "Пришлите договор с крупным покупателем",
                          "comment": "хочу понять сезонность"})
    assert r.status_code == 200
    app = client.get(f"/api/applications/{app['id']}").json()
    assert app["info_requests"][0]["items"][0]["message"] == "Пришлите договор с крупным покупателем"

    client.post(f"/api/applications/{app['id']}/documents", data={"doc_type": "other"}, files={"file": ("d.pdf", b"x", "application/pdf")})
    client.post(f"/api/applications/{app['id']}/provide-info")
    details = client.get(f"/api/backoffice/applications/{app['id']}").json()
    assert details["application"]["status"]["code"] == "manual_review"
    assert "M7_REVIEWED_BEFORE" in details["decisions"][-1]["manual_triggers"]
    assert details["decisions"][-1]["recommendation"]["amount"] > 0
