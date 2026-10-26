"""
Сквозной прогон всех 17 тестовых компаний Аскара (mocks/companies).
Делаем в API то, что написано в meta.scenario, и сверяем путь переходов T01…T22 с meta.expected.path.
"""
import copy
from datetime import date

import pytest

from app import external
from app.decision import Request, decide
from app.features import revenue_check
from tests import fakes

COMPANIES = sorted(d["meta"]["id"] for d in fakes.companies().values())


def drive(client, d):
    """Проходим заявку как клиент и специалист, пока она не закончится. Возвращает итоговую заявку."""
    sc = d["meta"]["scenario"]
    body = dict(inn=d["egrul"]["inn"], product_code=sc["product"], amount=sc["amount"], term_months=sc["term_months"],
                purpose=sc["purpose"], annual_revenue=sc["declared_revenue_12m"])
    if sc["collateral"]:
        body.update(collateral_type=sc["collateral"]["type"], collateral_description=sc["collateral"]["description"],
                    collateral_value=sc["collateral"]["value"])
    r = client.post("/api/applications", json=body)
    assert r.status_code == 201, r.text
    app_id = r.json()["id"]
    url = f"/api/applications/{app_id}"

    for doc in sc.get("documents_at_submit", []):  # в моках v2 отчётность банк берёт сам из ГИР БО
        r = client.post(f"{url}/documents", data={"doc_type": doc}, files={"file": ("otchet.pdf", b"%PDF", "application/pdf")})
        assert r.status_code == 200, r.text
    assert client.post(f"{url}/submit").status_code == 200

    for _ in range(10):
        app = client.get(url).json()
        status = app["status"]["code"]
        if status == "info_requested":
            doc = sc["document_on_request"]
            # Полина просит выписку за 6 месяцев — указываем половину годовых оборотов из сценария
            r = client.post(f"{url}/documents", data={"doc_type": doc["doc_type"], "declared_turnover": doc["turnover_12m"] // 2,
                                                      "declared_months": 6},
                            files={"file": ("vypiska.pdf", b"%PDF", "application/pdf")})
            assert r.status_code == 200, r.text
            assert client.post(f"{url}/provide-info").status_code == 200
        elif status == "manual_review":
            r = client.post(f"/api/backoffice/applications/{app_id}/decision",
                            json={"action": "approve", "comment": "согласен с рекомендацией системы"})
            assert r.status_code == 200, r.text
        elif status == "offer_proposed":
            app = client.post(f"{url}/accept", json={}).json()
            r = client.post(f"{url}/sign", json={"code": app["sign_code"]})
            assert r.status_code == 200, r.text
        else:
            return app
    raise AssertionError("заявка зациклилась")


def system_decision(client, app_id):
    """Последнее решение системы (до специалиста) — с ним сверяем ожидаемый исход и причину."""
    decisions = client.get(f"/api/backoffice/applications/{app_id}").json()["decisions"]
    return [x for x in decisions if x["decided_by"] == "system"][-1]


@pytest.mark.parametrize("company_id", COMPANIES)
def test_company_goes_its_way(client, company_id):
    d = fakes.by_id(company_id)
    exp = d["meta"]["expected"]
    app = drive(client, d)

    path = [h["transition_id"] for h in app["history"]]
    assert path == exp["path"]

    dec = system_decision(client, app["id"])
    outcome = dec["outcome"]
    reasons = dec["reason_codes"] + dec["manual_triggers"] + [s["code"] for s in dec["stop_factors"]]
    assert outcome == exp["outcome"]
    if exp["reason"]:
        assert exp["reason"] in reasons

    # PD, класс и предложение — те же, что в эталонном расчёте mocks/check_mocks.py
    model = exp.get("model")
    assert dec["grade"] == exp["grade"]
    if model:
        assert float(dec["pd"]) == pytest.approx(model["pd"], abs=1e-6)
        assert float(dec["lgd"]) == pytest.approx(model["lgd"], abs=1e-4)
        assert float(dec["product_pd_max"]) == pytest.approx(model["product_pd_max"], abs=1e-4)
        assert dec["model_version"] == model["model_id"]
    if exp.get("offer"):
        o, got = exp["offer"], dec["recommendation"] or app["offer"]
        assert (int(float(got["amount"])), got["term_months"]) == (o["amount"], o["term_months"])
        assert float(got["rate"]) == pytest.approx(o["rate"] * 100)
        assert int(float(got["monthly_payment"])) == pytest.approx(o["monthly_payment"], abs=1)
        assert dec["limit_binding"] == o["limit_binding"]


@pytest.mark.parametrize("company_id", ["C09", "C10", "C11", "C12", "C13", "C14"])
def test_rejection_is_explained_to_client(client, company_id):
    app = drive(client, fakes.by_id(company_id))
    assert app["status"]["code"] == "rejected"
    assert app["rejection"]["reason"]
    assert app["rejection"]["advice"]
    # служебные коды и комментарии (PD, стоп-факторы) клиенту не отдаём
    assert all(h["comment"] is None and h["reason_code"] is None for h in app["history"] if h["actor"] != "client")


def scoring_data(company_id, **changes):
    d = copy.deepcopy(fakes.by_id(company_id))
    data = {s: d[fakes.SECTIONS.get(s, s)] for s in external.SOURCES}
    data.update(changes)
    return d["meta"]["scenario"], data


def request_of(sc, is_legal=True):
    return Request(sc["product"], sc["amount"], sc["term_months"], is_legal, None, reviewed_before=False)


def test_legal_without_financials_goes_to_specialist():
    sc, data = scoring_data("C01", gir_bo=None)  # ГИР БО не нашёл отчётность — модель юрлица не посчитать
    r = decide(request_of(sc), data, revenue_check(data["bank"], sc["declared_revenue_12m"], None), date(2026, 10, 24))
    assert (r.outcome, r.manual_triggers) == ("MANUAL_REVIEW", ["M6_MODEL_UNAVAILABLE"])


def test_medium_business_is_out_of_model_scope():
    sc, data = scoring_data("C01")
    data["fns"]["msp_register"]["category"] = "MEDIUM"
    r = decide(request_of(sc), data, revenue_check(data["bank"], sc["declared_revenue_12m"], None), date(2026, 10, 24))
    assert (r.outcome, r.manual_triggers, r.pd) == ("MANUAL_REVIEW", ["M8_OUT_OF_MODEL_SCOPE"], None)


def test_reviewed_before_never_auto_decides():
    sc, data = scoring_data("C10")  # класс D: без специалиста был бы автоотказ
    req = request_of(sc)
    req.reviewed_before = True
    r = decide(req, data, revenue_check(data["bank"], sc["declared_revenue_12m"], None), date(2026, 10, 24))
    assert (r.outcome, r.manual_triggers, r.grade) == ("MANUAL_REVIEW", ["M7_REVIEWED_BEFORE"], "D")
