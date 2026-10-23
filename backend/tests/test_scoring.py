from datetime import date
from decimal import Decimal as D

from app.scoring import Inputs, ProductTerms, annuity, decide, probability_of_default, revenue_mismatch
from app.statuses import Status
from tests.fakes import COMPANIES

WC = ProductTerms("working_capital", D(300000), D(30000000), D("14"), D("25"), 9)
TODAY = date(2026, 10, 24)


def inputs(inn, amount, term=24, revenue=None, confirmed=False, product=WC):
    c = COMPANIES[inn]
    return Inputs(product, D(amount), term, c["registry"], c["bki"], c["fns"], c["bank"],
                  D(revenue) if revenue else None, confirmed, TODAY)


def test_pd_goes_down_when_score_goes_up():
    assert probability_of_default(140) < probability_of_default(70) < probability_of_default(0)
    assert D("0.009") < probability_of_default(140) < D("0.011")


def test_reliable_client_approved_with_low_rate():
    r = decide(inputs("7701123451", 5_000_000))
    assert r.outcome == Status.APPROVED
    assert r.score == 140
    assert r.amount == D(5_000_000)
    assert r.rate < D(15)


def test_high_debt_load_gives_smaller_amount():
    r = decide(inputs("7802543212", 3_000_000))
    assert r.outcome == Status.COUNTER_OFFER
    assert D(300_000) <= r.amount < D(3_000_000)
    # с предложенной суммой платежи укладываются в половину оборота
    assert (D(350_000) + r.monthly_payment) / D(900_000) <= D("0.5")


def test_young_business_without_history_goes_to_specialist():
    r = decide(inputs("540612345667", 1_000_000, term=12))
    assert r.outcome == Status.MANUAL_REVIEW
    assert r.manual_reasons == ["pd"]


def test_large_amount_goes_to_specialist():
    r = decide(inputs("7701123451", 20_000_000))
    assert r.outcome == Status.MANUAL_REVIEW
    assert "large_amount" in r.manual_reasons


def test_stop_factors():
    r = decide(inputs("7711234560", 2_000_000))
    assert r.outcome == Status.REJECTED
    assert [s["code"] for s in r.stop_factors] == ["liquidating", "tax_debt"]
    assert r.score is None  # до баллов дело не дошло


def test_product_rules_change_the_outcome():
    # тот же клиент, но продукт требует 5 лет работы — отказ ещё до баллов
    strict = ProductTerms("investment", D(1_000_000), D(150_000_000), D("14"), D("20"), 60)
    r = decide(inputs("7802543212", 3_000_000, product=strict))
    assert r.outcome == Status.REJECTED
    assert r.stop_factors[0]["code"] == "too_young"
    assert "от 60 мес." in r.reason


def test_revenue_mismatch_until_document():
    assert revenue_mismatch(inputs("6602345677", 5_000_000, revenue=30_000_000))
    assert not revenue_mismatch(inputs("6602345677", 5_000_000, revenue=30_000_000, confirmed=True))
    assert not revenue_mismatch(inputs("6602345677", 5_000_000, revenue=9_000_000))


def test_explanation_has_every_factor():
    r = decide(inputs("7802543212", 3_000_000))
    assert [f["code"] for f in r.factors] == [
        "business_age", "credit_history", "debt_load", "turnover_stability", "amount_to_revenue"
    ]
    assert sum(f["points"] for f in r.factors) == r.score


def test_annuity():
    # 1.2 млн на 12 мес. под 12% — классический пример, платёж ~106 618 ₽
    assert annuity(D(1_200_000), D(12), 12) == D("106618.55")
